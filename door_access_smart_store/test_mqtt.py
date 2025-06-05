#!/usr/bin/env python3
"""
Simple MQTT Test Script - Run this in a separate terminal
"""

import json
import time
from datetime import datetime
from door_mqtt_client import SmartDoorMQTTClient

def test_mqtt_client():
    """Test MQTT client functionality"""
    print("🧪 MQTT Client Test")
    print("=" * 40)
    
    # Create MQTT client
    client = SmartDoorMQTTClient()
    
    # Connect
    print("🔗 Connecting to AWS IoT Core...")
    if not client.connect():
        print("❌ Failed to connect to AWS IoT Core")
        return False
    
    print("✅ Connected successfully!")
    time.sleep(2)
    
    # Test 1: Status message
    print("\n📊 Test 1: Publishing status update...")
    success = client.publish_door_status("TEST_MODE", "Manual test in progress")
    print(f"Status update: {'✅ Success' if success else '❌ Failed'}")
    
    time.sleep(2)
    
    # Test 2: Entry request
    print("\n🚪 Test 2: Processing entry request...")
    test_rfid = "ABC123456789"
    success = client.process_entry_request(test_rfid)
    print(f"Entry request for {test_rfid}: {'✅ Sent' if success else '❌ Failed'}")
    
    time.sleep(3)
    
    # Test 3: Exit request
    print("\n🚶 Test 3: Processing exit request...")
    success = client.process_exit_request(test_rfid)
    print(f"Exit request for {test_rfid}: {'✅ Sent' if success else '❌ Failed'}")
    
    time.sleep(2)
    
    print("\n🎉 Tests completed!")
    print("📊 Check AWS IoT Console MQTT Test Client for messages on:")
    print("   • store/door/001/status")
    print("   • store/door/001/rfid/scan") 
    print("   • store/door/001/exit/request")
    print("   • store/customers/valid (Lambda response)")
    
    # Keep connection alive for a bit to see responses
    print("\n⏳ Waiting 10 seconds for potential responses...")
    time.sleep(10)
    
    # Disconnect
    client.disconnect()
    print("👋 Disconnected from AWS IoT Core")

if __name__ == "__main__":
    test_mqtt_client()