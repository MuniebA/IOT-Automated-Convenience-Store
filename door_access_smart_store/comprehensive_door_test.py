#!/usr/bin/env python3
"""
Comprehensive Door Access System Test Suite
Tests all MQTT topics, database entries, and cloud integration
"""

import json
import time
import ssl
import threading
from datetime import datetime
from paho.mqtt import client as mqtt_client
from database import DatabaseManager
import boto3
from botocore.exceptions import ClientError

class ComprehensiveDoorTest:
    def __init__(self):
        # MQTT Configuration
        self.iot_endpoint = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
        self.client_id = "door-comprehensive-test"
        self.ca_cert = "certificates/AmazonRootCA1.pem"
        self.cert_file = "certificates/iot-convenience-store-door-001-production.cert.pem"
        self.key_file = "certificates/iot-convenience-store-door-001-production.private.key"
        
        # MQTT Topics to test
        self.topics = {
            # Publish topics (Door sends)
            'status': 'store/door/001/status',
            'entry': 'store/door/001/entry', 
            'exit': 'store/door/001/exit',
            'errors': 'store/door/001/errors',
            'rfid_scan': 'store/door/001/rfid/scan',
            
            # Subscribe topics (Door receives)
            'commands': 'store/door/001/commands',
            'customer_valid': 'store/customers/valid'
        }
        
        # Test tracking
        self.test_results = {}
        self.messages_received = {}
        self.connected = False
        
        # Database and cloud clients
        self.db = DatabaseManager()
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # DynamoDB table names (update these to match your Terraform deployment)
        self.tables = {
            'customers': 'iot-convenience-store-customers-production',
            'sessions': 'iot-convenience-store-sessions-production', 
            'transactions': 'iot-convenience-store-transactions-production',
            'fraud_events': 'iot-convenience-store-fraud-events-production',
            'access_logs': 'iot-convenience-store-access-logs-production'
        }
        
    def setup_mqtt_client(self):
        """Setup MQTT client with SSL"""
        try:
            self.mqtt_client = mqtt_client.Client(self.client_id)
            
            # SSL Configuration
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(self.ca_cert)
            context.load_cert_chain(self.cert_file, self.key_file)
            self.mqtt_client.tls_set_context(context)
            
            # Callbacks
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_message = self.on_message
            self.mqtt_client.on_publish = self.on_publish
            
            return True
        except Exception as e:
            print(f"❌ MQTT setup failed: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            print("✅ Connected to AWS IoT Core for testing")
            self.connected = True
            
            # Subscribe to all receive topics
            for topic_name, topic in self.topics.items():
                if topic_name in ['commands', 'customer_valid']:
                    client.subscribe(topic, qos=1)
                    print(f"📡 Subscribed to: {topic}")
        else:
            print(f"❌ MQTT connection failed: {rc}")
            self.connected = False
    
    def on_message(self, client, userdata, msg):
        """MQTT message callback"""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
            print(f"📨 Received on {topic}: {json.dumps(payload, indent=2)}")
            
            # Track received messages
            if topic not in self.messages_received:
                self.messages_received[topic] = []
            self.messages_received[topic].append(payload)
            
        except Exception as e:
            print(f"❌ Error parsing message on {topic}: {e}")
    
    def on_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        print(f"✅ Message {mid} published successfully")
    
    def connect_mqtt(self):
        """Connect to AWS IoT Core"""
        if not self.setup_mqtt_client():
            return False
            
        try:
            self.mqtt_client.connect(self.iot_endpoint, 8883, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
            
            return self.connected
        except Exception as e:
            print(f"❌ MQTT connection error: {e}")
            return False
    
    def test_publish_topics(self):
        """Test all topics that door publishes to"""
        print("\n🔸 Testing MQTT Publish Topics")
        print("=" * 50)
        
        test_cases = [
            {
                'topic': self.topics['status'],
                'name': 'Door Status',
                'payload': {
                    'door_id': 'door-001',
                    'status': 'TEST_STATUS',
                    'message': 'Comprehensive test status',
                    'timestamp': datetime.utcnow().isoformat(),
                    'door_state': 'LOCKED',
                    'ir_threshold': 300
                }
            },
            {
                'topic': self.topics['entry'],
                'name': 'Entry Event',
                'payload': {
                    'door_id': 'door-001',
                    'event_type': 'ENTRY_SUCCESS',
                    'rfid_uid': 'TEST123456789',
                    'customer_name': 'Test User',
                    'access_granted': True,
                    'reason': 'Test access',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'topic': self.topics['exit'],
                'name': 'Exit Event', 
                'payload': {
                    'door_id': 'door-001',
                    'event_type': 'EXIT_SUCCESS',
                    'customer_name': 'Test User',
                    'session_completed': True,
                    'timestamp': datetime.utcnow().isoformat(),
                    'ir_sensor_triggered': True
                }
            },
            {
                'topic': self.topics['errors'],
                'name': 'Error Event',
                'payload': {
                    'door_id': 'door-001',
                    'error_type': 'TEST_ERROR',
                    'details': 'Comprehensive test error',
                    'timestamp': datetime.utcnow().isoformat(),
                    'severity': 'LOW'
                }
            },
            {
                'topic': self.topics['rfid_scan'],
                'name': 'RFID Scan',
                'payload': {
                    'rfid_uid': 'TEST123456789',
                    'door_id': 'door-001',
                    'timestamp': datetime.utcnow().isoformat(),
                    'test': True
                }
            }
        ]
        
        for test_case in test_cases:
            print(f"\n📤 Testing: {test_case['name']}")
            print(f"   Topic: {test_case['topic']}")
            
            try:
                result = self.mqtt_client.publish(
                    test_case['topic'],
                    json.dumps(test_case['payload']),
                    qos=1
                )
                
                if result.rc == 0:
                    print(f"   ✅ Published successfully")
                    self.test_results[f"publish_{test_case['name']}"] = "PASS"
                else:
                    print(f"   ❌ Publish failed: {result.rc}")
                    self.test_results[f"publish_{test_case['name']}"] = "FAIL"
                    
                time.sleep(2)  # Wait between publishes
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.test_results[f"publish_{test_case['name']}"] = "ERROR"
    
    def test_subscribe_topics(self):
        """Test sending commands to door"""
        print("\n🔹 Testing MQTT Subscribe Topics (Sending Commands)")
        print("=" * 50)
        
        command_tests = [
            {
                'topic': self.topics['commands'],
                'name': 'Unlock Command',
                'payload': {
                    'command': 'UNLOCK',
                    'reason': 'Test unlock command',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'topic': self.topics['commands'],
                'name': 'Lock Command',
                'payload': {
                    'command': 'LOCK',
                    'reason': 'Test lock command', 
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'topic': self.topics['commands'],
                'name': 'Status Request',
                'payload': {
                    'command': 'STATUS_REQUEST',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'topic': self.topics['commands'],
                'name': 'Emergency Unlock',
                'payload': {
                    'command': 'EMERGENCY_UNLOCK',
                    'reason': 'Test emergency unlock',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'topic': self.topics['customer_valid'],
                'name': 'Customer Validation Response',
                'payload': {
                    'door_id': 'door-001',
                    'validation_result': {
                        'rfid_uid': 'TEST123456789',
                        'valid': True,
                        'customer_name': 'Test User',
                        'customer_type': 'REGULAR',
                        'reason': 'Valid test customer'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        ]
        
        for test_case in command_tests:
            print(f"\n📤 Testing: {test_case['name']}")
            print(f"   Topic: {test_case['topic']}")
            
            try:
                result = self.mqtt_client.publish(
                    test_case['topic'],
                    json.dumps(test_case['payload']),
                    qos=1
                )
                
                if result.rc == 0:
                    print(f"   ✅ Command sent successfully")
                    self.test_results[f"command_{test_case['name']}"] = "PASS"
                else:
                    print(f"   ❌ Command failed: {result.rc}")
                    self.test_results[f"command_{test_case['name']}"] = "FAIL"
                    
                time.sleep(3)  # Wait for response
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.test_results[f"command_{test_case['name']}"] = "ERROR"
    
    def test_local_database(self):
        """Test local MySQL/MariaDB database operations"""
        print("\n🗄️ Testing Local Database Operations")
        print("=" * 50)
        
        try:
            # Test 1: System status
            print("\n📊 Testing system status...")
            status = self.db.get_system_status()
            if status:
                print(f"   ✅ System status: {status}")
                self.test_results['local_db_status'] = "PASS"
            else:
                print(f"   ❌ System status failed")
                self.test_results['local_db_status'] = "FAIL"
            
            # Test 2: Add test user
            print("\n👤 Testing user management...")
            test_uid = f"TEST{int(time.time())}"
            if self.db.add_user(test_uid, "Test User Comprehensive"):
                print(f"   ✅ Added test user: {test_uid}")
                self.test_results['local_db_add_user'] = "PASS"
                
                # Test getting users
                users = self.db.get_all_users()
                print(f"   ✅ Retrieved {len(users)} users")
                self.test_results['local_db_get_users'] = "PASS"
                
            else:
                print(f"   ❌ Failed to add user")
                self.test_results['local_db_add_user'] = "FAIL"
            
            # Test 3: Access logging
            print("\n📝 Testing access logging...")
            if self.db.log_access(test_uid, "Test User", "GRANTED"):
                print(f"   ✅ Logged access event")
                self.test_results['local_db_log_access'] = "PASS"
                
                # Get recent logs
                logs = self.db.get_recent_logs(5)
                print(f"   ✅ Retrieved {len(logs)} recent logs")
                self.test_results['local_db_get_logs'] = "PASS"
                
            else:
                print(f"   ❌ Failed to log access")
                self.test_results['local_db_log_access'] = "FAIL"
            
            # Test 4: Commands
            print("\n⚡ Testing command queue...")
            if self.db.add_command("TEST_COMMAND"):
                print(f"   ✅ Added test command")
                self.test_results['local_db_add_command'] = "PASS"
                
                commands = self.db.get_pending_commands()
                if commands:
                    print(f"   ✅ Retrieved {len(commands)} pending commands")
                    # Mark first command as completed
                    self.db.mark_command_completed(commands[0][0])
                    print(f"   ✅ Marked command as completed")
                    self.test_results['local_db_commands'] = "PASS"
                else:
                    print(f"   ⚠️ No pending commands found")
                    self.test_results['local_db_commands'] = "PARTIAL"
            else:
                print(f"   ❌ Failed to add command")
                self.test_results['local_db_add_command'] = "FAIL"
                
        except Exception as e:
            print(f"❌ Database test error: {e}")
            self.test_results['local_db_error'] = str(e)
    
    def test_cloud_database(self):
        """Test AWS DynamoDB operations"""
        print("\n☁️ Testing Cloud Database (DynamoDB) Operations")
        print("=" * 50)
        
        for table_name, table_id in self.tables.items():
            print(f"\n📊 Testing table: {table_name} ({table_id})")
            
            try:
                table = self.dynamodb.Table(table_id)
                
                # Test table exists and is accessible
                response = table.meta.client.describe_table(TableName=table_id)
                print(f"   ✅ Table accessible - Status: {response['Table']['TableStatus']}")
                
                # Test scan (get item count)
                scan_response = table.scan(
                    Select='COUNT',
                    Limit=1
                )
                item_count = scan_response.get('Count', 0)
                print(f"   ✅ Table scan successful - Items: {item_count}")
                
                self.test_results[f'cloud_db_{table_name}'] = "PASS"
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    print(f"   ❌ Table not found: {table_id}")
                elif error_code == 'AccessDeniedException':
                    print(f"   ❌ Access denied to table: {table_id}")
                else:
                    print(f"   ❌ AWS Error: {error_code}")
                self.test_results[f'cloud_db_{table_name}'] = f"FAIL - {error_code}"
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.test_results[f'cloud_db_{table_name}'] = f"ERROR - {str(e)}"
    
    def test_end_to_end_flow(self):
        """Test complete end-to-end flow simulation"""
        print("\n🔄 Testing End-to-End Flow Simulation")
        print("=" * 50)
        
        try:
            # Simulate complete door access scenario
            test_rfid = f"E2E{int(time.time())}"
            test_customer = "End-to-End Test User"
            
            print(f"\n🎭 Simulating door access for: {test_customer}")
            print(f"   RFID: {test_rfid}")
            
            # Step 1: RFID Scan
            print("\n1️⃣ Simulating RFID scan...")
            rfid_payload = {
                'rfid_uid': test_rfid,
                'door_id': 'door-001',
                'timestamp': datetime.utcnow().isoformat(),
                'test_flow': True
            }
            
            self.mqtt_client.publish(
                self.topics['rfid_scan'],
                json.dumps(rfid_payload),
                qos=1
            )
            print("   ✅ RFID scan published")
            time.sleep(2)
            
            # Step 2: Customer validation response
            print("\n2️⃣ Simulating customer validation...")
            validation_payload = {
                'door_id': 'door-001',
                'validation_result': {
                    'rfid_uid': test_rfid,
                    'valid': True,
                    'customer_name': test_customer,
                    'customer_type': 'REGULAR',
                    'reason': 'Valid end-to-end test'
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.mqtt_client.publish(
                self.topics['customer_valid'],
                json.dumps(validation_payload),
                qos=1
            )
            print("   ✅ Customer validation published")
            time.sleep(2)
            
            # Step 3: Entry success
            print("\n3️⃣ Simulating successful entry...")
            entry_payload = {
                'door_id': 'door-001',
                'event_type': 'ENTRY_SUCCESS',
                'rfid_uid': test_rfid,
                'customer_name': test_customer,
                'access_granted': True,
                'reason': 'End-to-end test access',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.mqtt_client.publish(
                self.topics['entry'],
                json.dumps(entry_payload),
                qos=1
            )
            print("   ✅ Entry event published")
            time.sleep(2)
            
            # Step 4: Door status update
            print("\n4️⃣ Simulating door status update...")
            status_payload = {
                'door_id': 'door-001',
                'status': 'UNLOCKED',
                'message': f'Access granted to {test_customer}',
                'timestamp': datetime.utcnow().isoformat(),
                'door_state': 'UNLOCKED'
            }
            
            self.mqtt_client.publish(
                self.topics['status'],
                json.dumps(status_payload),
                qos=1
            )
            print("   ✅ Status update published")
            time.sleep(2)
            
            # Step 5: Exit event
            print("\n5️⃣ Simulating customer exit...")
            exit_payload = {
                'door_id': 'door-001',
                'event_type': 'EXIT_SUCCESS',
                'customer_name': test_customer,
                'session_completed': True,
                'timestamp': datetime.utcnow().isoformat(),
                'ir_sensor_triggered': True
            }
            
            self.mqtt_client.publish(
                self.topics['exit'],
                json.dumps(exit_payload),
                qos=1
            )
            print("   ✅ Exit event published")
            
            print(f"\n🎉 End-to-end flow simulation completed!")
            self.test_results['end_to_end_flow'] = "PASS"
            
        except Exception as e:
            print(f"❌ End-to-end flow error: {e}")
            self.test_results['end_to_end_flow'] = f"ERROR - {str(e)}"
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE DOOR ACCESS TEST REPORT")
        print("=" * 70)
        
        # Count results
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results.values() if r == "PASS"])
        failed = len([r for r in self.test_results.values() if "FAIL" in str(r)])
        errors = len([r for r in self.test_results.values() if "ERROR" in str(r)])
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⚠️ Errors: {errors}")
        print(f"   📊 Success Rate: {(passed/total_tests)*100:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            if result == "PASS":
                status = "✅"
            elif "FAIL" in str(result):
                status = "❌"
            elif "ERROR" in str(result):
                status = "⚠️"
            else:
                status = "📝"
            
            print(f"   {status} {test_name}: {result}")
        
        print(f"\n📨 MESSAGES RECEIVED:")
        for topic, messages in self.messages_received.items():
            print(f"   📡 {topic}: {len(messages)} messages")
        
        print(f"\n🔗 AWS Console Monitoring:")
        print(f"   📍 Go to: AWS IoT Console > Test > MQTT test client")
        print(f"   📡 Subscribe to: store/door/001/#")
        print(f"   📊 Check message traffic during test")
        
        print("=" * 70)
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Comprehensive Door Access System Test")
        print("=" * 70)
        print("🎯 This will test:")
        print("   • All MQTT publish topics")
        print("   • All MQTT subscribe topics") 
        print("   • Local database operations")
        print("   • Cloud database access")
        print("   • End-to-end flow simulation")
        print("=" * 70)
        
        # Connect to MQTT
        if not self.connect_mqtt():
            print("❌ Failed to connect to MQTT - aborting tests")
            return
        
        # Run all test suites
        time.sleep(2)
        self.test_publish_topics()
        
        time.sleep(3)
        self.test_subscribe_topics()
        
        time.sleep(2)
        self.test_local_database()
        
        time.sleep(2)
        self.test_cloud_database()
        
        time.sleep(2)
        self.test_end_to_end_flow()
        
        # Wait for any final messages
        time.sleep(5)
        
        # Generate report
        self.generate_test_report()
        
        # Cleanup
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("\n👋 Test completed - MQTT disconnected")

def main():
    """Main test execution"""
    print("🚪 Door Access System - Comprehensive Test Suite")
    print("=" * 55)
    
    # Check if system is ready
    import os
    cert_files = [
        'certificates/AmazonRootCA1.pem',
        'certificates/iot-convenience-store-door-001-production.cert.pem',
        'certificates/iot-convenience-store-door-001-production.private.key'
    ]
    
    print("🔐 Checking prerequisites...")
    for cert_file in cert_files:
        if os.path.exists(cert_file):
            print(f"   ✅ {cert_file}")
        else:
            print(f"   ❌ {cert_file} - MISSING!")
            return
    
    print("   ✅ All certificate files found")
    print("   ✅ Ready to start comprehensive testing")
    
    # Create and run test suite
    test_suite = ComprehensiveDoorTest()
    
    try:
        test_suite.run_all_tests()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")

if __name__ == "__main__":
    main()
