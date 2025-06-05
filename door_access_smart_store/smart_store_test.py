#!/usr/bin/env python3
"""
Smart Store Comprehensive Test Suite
Tests the complete customer journey with cart integration
"""

import json
import time
import ssl
import boto3
from datetime import datetime
from paho.mqtt import client as mqtt_client
from database import DatabaseManager

class SmartStoreTestSuite:
    def __init__(self):
        # MQTT Configuration
        self.iot_endpoint = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
        self.client_id = "smart-store-test-suite"
        self.ca_cert = "certificates/AmazonRootCA1.pem"
        self.cert_file = "certificates/iot-convenience-store-door-001-production.cert.pem"
        self.key_file = "certificates/iot-convenience-store-door-001-production.private.key"
        
        # Test tracking
        self.connected = False
        self.test_results = {}
        self.messages_received = {}
        
        # Database clients
        self.db = DatabaseManager()
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Test customer data
        self.test_customer = {
            'rfid_uid': f'TEST{int(time.time())}',
            'customer_name': 'Test Customer Journey',
            'customer_id': f'test_customer_{int(time.time())}'
        }
        
    def setup_mqtt_client(self):
        """Setup MQTT client"""
        try:
            self.mqtt_client = mqtt_client.Client(self.client_id)
            
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(self.ca_cert)
            context.load_cert_chain(self.cert_file, self.key_file)
            self.mqtt_client.tls_set_context(context)
            
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_message = self.on_message
            
            return True
        except Exception as e:
            print(f"❌ MQTT setup failed: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to AWS IoT Core for testing")
            self.connected = True
            
            # Subscribe to all relevant topics
            topics = [
                'store/customers/valid',
                'store/door/001/exit/response',
                'store/door/001/status',
                'store/door/001/entry',
                'store/door/001/exit'
            ]
            
            for topic in topics:
                client.subscribe(topic, qos=1)
                print(f"📡 Subscribed to: {topic}")
        else:
            print(f"❌ MQTT connection failed: {rc}")
            self.connected = False
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
            print(f"📨 Received on {topic}: {json.dumps(payload, indent=2)}")
            
            if topic not in self.messages_received:
                self.messages_received[topic] = []
            self.messages_received[topic].append(payload)
            
        except Exception as e:
            print(f"❌ Error parsing message on {topic}: {e}")
    
    def connect_mqtt(self):
        """Connect to AWS IoT Core"""
        if not self.setup_mqtt_client():
            return False
            
        try:
            self.mqtt_client.connect(self.iot_endpoint, 8883, 60)
            self.mqtt_client.loop_start()
            
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
            
            return self.connected
        except Exception as e:
            print(f"❌ MQTT connection error: {e}")
            return False
    
    def test_1_setup_test_customer(self):
        """Test 1: Create test customer in database"""
        print("\n" + "="*60)
        print("🧪 TEST 1: Setup Test Customer")
        print("="*60)
        
        try:
            # Add test customer to local database for fallback
            result = self.db.add_user(self.test_customer['rfid_uid'], self.test_customer['customer_name'])
            
            if result:
                print(f"✅ Test customer added to local database")
                print(f"   RFID: {self.test_customer['rfid_uid']}")
                print(f"   Name: {self.test_customer['customer_name']}")
                self.test_results['setup_customer'] = "PASS"
            else:
                print(f"❌ Failed to add test customer to local database")
                self.test_results['setup_customer'] = "FAIL"
                
            # Try to add to cloud DynamoDB (if available)
            try:
                customers_table = self.dynamodb.Table('iot-convenience-store-customers-production')
                
                customer_record = {
                    'customer_id': self.test_customer['customer_id'],
                    'customer_name': self.test_customer['customer_name'],
                    'rfid_card_uid': self.test_customer['rfid_uid'],
                    'customer_type': 'REGULAR',
                    'membership_status': 'ACTIVE',
                    'total_spent': 0.0,
                    'total_visits': 0,
                    'discount_percentage': 0,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                customers_table.put_item(Item=customer_record)
                print(f"✅ Test customer added to cloud DynamoDB")
                self.test_results['setup_cloud_customer'] = "PASS"
                
            except Exception as e:
                print(f"⚠️ Could not add to cloud DynamoDB: {e}")
                self.test_results['setup_cloud_customer'] = "SKIP"
                
        except Exception as e:
            print(f"❌ Error in customer setup: {e}")
            self.test_results['setup_customer'] = "ERROR"
    
    def test_2_customer_entry(self):
        """Test 2: Customer entry with cart assignment"""
        print("\n" + "="*60)
        print("🚪 TEST 2: Customer Entry & Cart Assignment")
        print("="*60)
        
        try:
            # Clear previous messages
            self.messages_received.clear()
            
            # Simulate RFID scan at door for entry
            entry_scan = {
                'rfid_uid': self.test_customer['rfid_uid'],
                'door_id': 'door-001',
                'timestamp': datetime.utcnow().isoformat(),
                'scan_type': 'entry'
            }
            
            print(f"📤 Publishing entry request...")
            print(f"   RFID: {self.test_customer['rfid_uid']}")
            
            result = self.mqtt_client.publish(
                'store/door/001/rfid/scan',
                json.dumps(entry_scan),
                qos=1
            )
            
            if result.rc == 0:
                print(f"✅ Entry request published successfully")
                
                # Wait for cloud validation response
                print(f"⏳ Waiting for cloud validation response...")
                timeout = 15
                validation_received = False
                
                while timeout > 0 and not validation_received:
                    time.sleep(1)
                    timeout -= 1
                    
                    # Check if we received a validation response
                    if 'store/customers/valid' in self.messages_received:
                        validation_response = self.messages_received['store/customers/valid'][-1]
                        validation_result = validation_response.get('validation_result', {})
                        
                        if validation_result.get('valid'):
                            assigned_cart = validation_result.get('assigned_cart', 'unknown')
                            customer_name = validation_result.get('customer_name', 'Unknown')
                            
                            print(f"✅ Entry validation successful!")
                            print(f"   Customer: {customer_name}")
                            print(f"   Assigned Cart: {assigned_cart}")
                            print(f"   Message: {validation_result.get('message', '')}")
                            
                            self.test_results['customer_entry'] = "PASS"
                            self.test_customer['assigned_cart'] = assigned_cart
                            validation_received = True
                        else:
                            reason = validation_result.get('reason', 'Unknown')
                            print(f"❌ Entry validation failed: {reason}")
                            self.test_results['customer_entry'] = "FAIL"
                            validation_received = True
                
                if not validation_received:
                    print(f"⚠️ No validation response received within timeout")
                    self.test_results['customer_entry'] = "TIMEOUT"
                    
            else:
                print(f"❌ Failed to publish entry request: {result.rc}")
                self.test_results['customer_entry'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error in entry test: {e}")
            self.test_results['customer_entry'] = "ERROR"
    
    def test_3_check_active_session(self):
        """Test 3: Verify active session was created"""
        print("\n" + "="*60)
        print("📊 TEST 3: Check Active Session Creation")
        print("="*60)
        
        try:
            # Check if active session was created in DynamoDB
            active_sessions_table = self.dynamodb.Table('iot-convenience-store-active-sessions-production')
            
            response = active_sessions_table.get_item(
                Key={'customer_id': self.test_customer['customer_id']}
            )
            
            if 'Item' in response:
                session = response['Item']
                print(f"✅ Active session found!")
                print(f"   Session ID: {session.get('session_id')}")
                print(f"   Customer: {session.get('customer_name')}")
                print(f"   Assigned Cart: {session.get('assigned_cart')}")
                print(f"   Entry Time: {session.get('entry_time')}")
                print(f"   Checkout Completed: {session.get('checkout_completed', False)}")
                
                self.test_results['active_session_check'] = "PASS"
                self.test_customer['session_id'] = session.get('session_id')
            else:
                print(f"❌ No active session found for customer")
                self.test_results['active_session_check'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error checking active session: {e}")
            self.test_results['active_session_check'] = "ERROR"
    
    def test_4_cart_checkout_simulation(self):
        """Test 4: Simulate cart checkout completion"""
        print("\n" + "="*60)
        print("🛒 TEST 4: Cart Checkout Simulation")
        print("="*60)
        
        try:
            # Simulate cart checkout completion
            assigned_cart = self.test_customer.get('assigned_cart', 'cart-001')
            
            checkout_data = {
                'customer_id': self.test_customer['customer_id'],
                'session_id': self.test_customer.get('session_id', f'sess_{int(time.time())}'),
                'assigned_cart': assigned_cart,
                'total_amount': 45.67,
                'items': [
                    {'product_id': 'prod_001', 'name': 'Test Apple', 'quantity': 2, 'price': 15.99},
                    {'product_id': 'prod_002', 'name': 'Test Bread', 'quantity': 1, 'price': 13.69}
                ],
                'payment_method': 'card',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            print(f"📤 Publishing checkout completion...")
            print(f"   Cart: {assigned_cart}")
            print(f"   Total: ${checkout_data['total_amount']}")
            print(f"   Items: {len(checkout_data['items'])}")
            
            result = self.mqtt_client.publish(
                f'store/cart/{assigned_cart.split("-")[1]}/checkout',
                json.dumps(checkout_data),
                qos=1
            )
            
            if result.rc == 0:
                print(f"✅ Checkout completion published successfully")
                self.test_results['cart_checkout'] = "PASS"
                
                # Wait a moment for processing
                time.sleep(5)
                
            else:
                print(f"❌ Failed to publish checkout: {result.rc}")
                self.test_results['cart_checkout'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error in checkout simulation: {e}")
            self.test_results['cart_checkout'] = "ERROR"
    
    def test_5_verify_checkout_processed(self):
        """Test 5: Verify checkout was processed in active session"""
        print("\n" + "="*60)
        print("✅ TEST 5: Verify Checkout Processing")
        print("="*60)
        
        try:
            # Check if checkout was marked as completed
            active_sessions_table = self.dynamodb.Table('iot-convenience-store-active-sessions-production')
            
            response = active_sessions_table.get_item(
                Key={'customer_id': self.test_customer['customer_id']}
            )
            
            if 'Item' in response:
                session = response['Item']
                checkout_completed = session.get('checkout_completed', False)
                total_amount = session.get('total_amount', 0)
                
                if checkout_completed:
                    print(f"✅ Checkout marked as completed!")
                    print(f"   Total Amount: ${total_amount}")
                    print(f"   Checkout Time: {session.get('checkout_time', 'N/A')}")
                    self.test_results['checkout_verification'] = "PASS"
                else:
                    print(f"❌ Checkout not marked as completed")
                    self.test_results['checkout_verification'] = "FAIL"
            else:
                print(f"❌ Active session not found")
                self.test_results['checkout_verification'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error verifying checkout: {e}")
            self.test_results['checkout_verification'] = "ERROR"
    
    def test_6_customer_exit_successful(self):
        """Test 6: Customer exit with successful checkout"""
        print("\n" + "="*60)
        print("🚪 TEST 6: Customer Exit (Checkout Complete)")
        print("="*60)
        
        try:
            # Clear previous messages
            if 'store/door/001/exit/response' in self.messages_received:
                del self.messages_received['store/door/001/exit/response']
            
            # Simulate RFID scan at door for exit
            exit_request = {
                'rfid_uid': self.test_customer['rfid_uid'],
                'door_id': 'door-001',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            print(f"📤 Publishing exit request...")
            print(f"   RFID: {self.test_customer['rfid_uid']}")
            
            result = self.mqtt_client.publish(
                'store/door/001/exit/request',
                json.dumps(exit_request),
                qos=1
            )
            
            if result.rc == 0:
                print(f"✅ Exit request published successfully")
                
                # Wait for exit validation response
                print(f"⏳ Waiting for exit validation response...")
                timeout = 15
                exit_response_received = False
                
                while timeout > 0 and not exit_response_received:
                    time.sleep(1)
                    timeout -= 1
                    
                    # Check if we received an exit response
                    if 'store/door/001/exit/response' in self.messages_received:
                        exit_response = self.messages_received['store/door/001/exit/response'][-1]
                        allow_exit = exit_response.get('allow_exit', False)
                        message = exit_response.get('message', '')
                        customer_name = exit_response.get('customer_name', 'Unknown')
                        
                        if allow_exit:
                            print(f"✅ Exit granted!")
                            print(f"   Customer: {customer_name}")
                            print(f"   Message: {message}")
                            self.test_results['customer_exit_success'] = "PASS"
                        else:
                            print(f"❌ Exit denied: {message}")
                            self.test_results['customer_exit_success'] = "FAIL"
                        
                        exit_response_received = True
                
                if not exit_response_received:
                    print(f"⚠️ No exit response received within timeout")
                    self.test_results['customer_exit_success'] = "TIMEOUT"
                    
            else:
                print(f"❌ Failed to publish exit request: {result.rc}")
                self.test_results['customer_exit_success'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error in exit test: {e}")
            self.test_results['customer_exit_success'] = "ERROR"
    
    def test_7_verify_session_cleanup(self):
        """Test 7: Verify active session was cleaned up after exit"""
        print("\n" + "="*60)
        print("🧹 TEST 7: Verify Session Cleanup")
        print("="*60)
        
        try:
            # Check if active session was removed
            active_sessions_table = self.dynamodb.Table('iot-convenience-store-active-sessions-production')
            
            response = active_sessions_table.get_item(
                Key={'customer_id': self.test_customer['customer_id']}
            )
            
            if 'Item' not in response:
                print(f"✅ Active session cleaned up successfully!")
                print(f"   Customer session removed from active sessions table")
                self.test_results['session_cleanup'] = "PASS"
            else:
                print(f"❌ Active session still exists (should be removed after exit)")
                session = response['Item']
                print(f"   Session ID: {session.get('session_id')}")
                print(f"   Checkout Completed: {session.get('checkout_completed', False)}")
                self.test_results['session_cleanup'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error checking session cleanup: {e}")
            self.test_results['session_cleanup'] = "ERROR"
    
    def test_8_verify_historical_records(self):
        """Test 8: Verify historical records were created"""
        print("\n" + "="*60)
        print("📚 TEST 8: Verify Historical Records")
        print("="*60)
        
        try:
            # Check if transaction was created
            transactions_table = self.dynamodb.Table('iot-convenience-store-transactions-production')
            
            response = transactions_table.query(
                IndexName='user-time-index',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': self.test_customer['customer_id']},
                ScanIndexForward=False,  # Get most recent first
                Limit=1
            )
            
            transactions = response.get('Items', [])
            if transactions:
                transaction = transactions[0]
                print(f"✅ Transaction record created!")
                print(f"   Transaction ID: {transaction.get('transaction_id')}")
                print(f"   Amount: ${transaction.get('total_amount', 0)}")
                print(f"   Timestamp: {transaction.get('timestamp')}")
                self.test_results['historical_transaction'] = "PASS"
            else:
                print(f"❌ No transaction record found")
                self.test_results['historical_transaction'] = "FAIL"
                
            # Check if session was created
            sessions_table = self.dynamodb.Table('iot-convenience-store-sessions-production')
            
            response = sessions_table.query(
                IndexName='customer-time-index',
                KeyConditionExpression='customer_id = :customer_id',
                ExpressionAttributeValues={':customer_id': self.test_customer['customer_id']},
                ScanIndexForward=False,  # Get most recent first
                Limit=1
            )
            
            sessions = response.get('Items', [])
            if sessions:
                session = sessions[0]
                print(f"✅ Session record created!")
                print(f"   Session ID: {session.get('session_id')}")
                print(f"   Status: {session.get('session_status')}")
                print(f"   Total Amount: ${session.get('total_amount', 0)}")
                self.test_results['historical_session'] = "PASS"
            else:
                print(f"❌ No session record found")
                self.test_results['historical_session'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error checking historical records: {e}")
            self.test_results['historical_transaction'] = "ERROR"
            self.test_results['historical_session'] = "ERROR"
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n" + "="*60)
        print("🧹 CLEANUP: Removing Test Data")
        print("="*60)
        
        try:
            # Remove from local database
            self.db.delete_user(self.test_customer['rfid_uid'])
            print(f"✅ Removed test customer from local database")
            
            # Remove from cloud (if exists)
            try:
                customers_table = self.dynamodb.Table('iot-convenience-store-customers-production')
                customers_table.delete_item(
                    Key={'customer_id': self.test_customer['customer_id']}
                )
                print(f"✅ Removed test customer from cloud database")
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📊 SMART STORE INTEGRATION TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results.values() if r == "PASS"])
        failed = len([r for r in self.test_results.values() if r == "FAIL"])
        errors = len([r for r in self.test_results.values() if r == "ERROR"])
        timeouts = len([r for r in self.test_results.values() if r == "TIMEOUT"])
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⚠️ Errors: {errors}")
        print(f"   ⏰ Timeouts: {timeouts}")
        if total_tests > 0:
            print(f"   📊 Success Rate: {(passed/total_tests)*100:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            if result == "PASS":
                status = "✅"
            elif result == "FAIL":
                status = "❌"
            elif result == "ERROR":
                status = "⚠️"
            elif result == "TIMEOUT":
                status = "⏰"
            else:
                status = "📝"
            
            print(f"   {status} {test_name}: {result}")
        
        print(f"\n🎯 INTEGRATION STATUS:")
        if passed >= 6:  # Core functionality
            print("   🎉 SMART STORE INTEGRATION SUCCESSFUL!")
            print("   🚀 Your system is ready for production use")
        elif passed >= 4:
            print("   ⚠️ PARTIAL INTEGRATION - Some features working")
            print("   🔧 Check failed tests and retry")
        else:
            print("   ❌ INTEGRATION ISSUES - Review setup")
            print("   🔍 Check Lambda functions and IoT rules")
        
        print("="*80)
    
    def run_full_test_suite(self):
        """Run the complete test suite"""
        print("🧪 Smart Store Integration Test Suite")
        print("🎯 Testing complete customer journey with cart integration")
        print("=" * 80)
        
        if not self.connect_mqtt():
            print("❌ Failed to connect to MQTT - aborting tests")
            return
        
        # Run all tests in sequence
        self.test_1_setup_test_customer()
        time.sleep(2)
        
        self.test_2_customer_entry()
        time.sleep(3)
        
        self.test_3_check_active_session()
        time.sleep(2)
        
        self.test_4_cart_checkout_simulation()
        time.sleep(5)
        
        self.test_5_verify_checkout_processed()
        time.sleep(2)
        
        self.test_6_customer_exit_successful()
        time.sleep(3)
        
        self.test_7_verify_session_cleanup()
        time.sleep(2)
        
        self.test_8_verify_historical_records()
        time.sleep(2)
        
        # Generate final report
        self.generate_test_report()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Disconnect
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

def main():
    """Main test execution"""
    test_suite = SmartStoreTestSuite()
    
    try:
        test_suite.run_full_test_suite()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")

if __name__ == "__main__":
    main()