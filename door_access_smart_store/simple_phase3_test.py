#!/usr/bin/env python3
"""
Simple Phase 3 Test - Step by step verification
"""

def test_step_1_dynamodb():
    """Test Step 1: DynamoDB Manager"""
    print("📊 Step 1: Testing DynamoDB Manager")
    print("-" * 40)
    
    try:
        from dynamodb_manager import DynamoDBManager
        
        # Initialize
        db = DynamoDBManager()
        print("✅ DynamoDB Manager initialized")
        
        # Test customer lookup
        customer = db.get_customer_by_rfid('A4F55A07')
        print(f"✅ Customer lookup: {customer['found']}")
        
        if customer['found']:
            print(f"   Name: {customer['customer_name']}")
            print(f"   Type: {customer['customer_type']}")
            
            # Test session check
            session = db.check_customer_active_session(customer['customer_id'])
            print(f"✅ Session check: {'Found' if session else 'No session'}")
            
        return True
        
    except Exception as e:
        print(f"❌ DynamoDB test failed: {e}")
        return False

def test_step_2_mqtt():
    """Test Step 2: MQTT Connection"""
    print("\n📡 Step 2: Testing MQTT Connection")
    print("-" * 40)
    
    try:
        from door_mqtt_client import SmartDoorMQTTClient
        
        # Create client
        client = SmartDoorMQTTClient()
        client.client_id = "simple-test-client"
        
        print("🔗 Attempting MQTT connection...")
        
        if client.connect():
            print("✅ MQTT connected successfully")
            
            # Test publish
            print("📤 Testing message publish...")
            success = client.publish_door_status("TEST", "Simple test message")
            
            if success:
                print("✅ Message published successfully")
            else:
                print("⚠️  Message publish unclear")
            
            client.disconnect()
            return True
        else:
            print("❌ MQTT connection failed")
            return False
            
    except Exception as e:
        print(f"❌ MQTT test failed: {e}")
        return False

def test_step_3_integration():
    """Test Step 3: Integration Test"""
    print("\n🔗 Step 3: Testing Integration")
    print("-" * 40)
    
    try:
        from dynamodb_manager import DynamoDBManager
        
        db = DynamoDBManager()
        
        # Simulate the cloud-direct flow
        rfid_uid = 'A4F55A07'
        
        print(f"1. Looking up customer: {rfid_uid}")
        customer = db.get_customer_by_rfid(rfid_uid)
        
        if customer['found']:
            print(f"2. Customer found: {customer['customer_name']}")
            
            print(f"3. Checking active session...")
            session = db.check_customer_active_session(customer['customer_id'])
            
            if session:
                print(f"4. Exit flow: Customer has active session")
                action = "exit"
            else:
                print(f"4. Entry flow: No active session")
                action = "entry"
            
            print(f"5. Logging access event...")
            db.log_access_event(
                customer['customer_id'],
                rfid_uid,
                f"{action.upper()}_SUCCESS",
                customer['customer_name'],
                f"Cloud-direct {action} test"
            )
            
            print(f"✅ Integration test successful: {action} flow")
            return True
        else:
            print("❌ Customer not found in DynamoDB")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    print("🏪 Phase 3 Testing - Cloud-Direct Implementation")
    print("=" * 55)
    
    # Run tests step by step
    test1 = test_step_1_dynamodb()
    test2 = test_step_2_mqtt()
    test3 = test_step_3_integration()
    
    print("\n" + "=" * 55)
    print("📊 TEST RESULTS")
    print(f"DynamoDB Manager: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"MQTT Connection:  {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Integration Test: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 Phase 3 Implementation Successful")
        print("\n📋 Next Steps:")
        print("1. Run: python cloud_direct_serial_handler.py")
        print("2. Scan RFID card: A4F55A07")
        print("3. Watch cloud-direct processing in action")
        print("4. Proceed to Phase 4: User Management")
    else:
        print("\n⚠️  Some tests failed")
        if not test1:
            print("   🔧 Fix DynamoDB connection")
        if not test2:
            print("   🔧 Check MQTT certificates")
        if not test3:
            print("   🔧 Verify customer data exists")

if __name__ == "__main__":
    main()
