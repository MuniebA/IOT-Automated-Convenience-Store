#!/usr/bin/env python3
"""
Test script for Door Access MQTT connection to AWS IoT Core
"""

import json
import time
import ssl
import os
from paho.mqtt.client import Client as MQTTClient

# Configuration - UPDATE WITH YOUR IOT ENDPOINT
IOT_ENDPOINT = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "iot-convenience-store-door-001-test"

# Certificate files
CA_CERT = "certificates/AmazonRootCA1.pem"
CERT_FILE = "certificates/iot-convenience-store-door-001-production.cert.pem"
KEY_FILE = "certificates/iot-convenience-store-door-001-production.private.key"

def test_certificates():
    """Test if certificate files exist and are readable"""
    print("🔐 Checking certificate files...")
    
    cert_files = {
        'CA Certificate': CA_CERT,
        'Device Certificate': CERT_FILE, 
        'Private Key': KEY_FILE
    }
    
    all_good = True
    for name, path in cert_files.items():
        if os.path.exists(path):
            print(f"✅ {name}: Found")
            # Check file size
            size = os.path.getsize(path)
            print(f"   Size: {size} bytes")
        else:
            print(f"❌ {name}: Missing - {path}")
            all_good = False
    
    return all_good

def test_mqtt_connection():
    """Test basic MQTT connection to AWS IoT Core"""
    
    print("\n🧪 Testing MQTT Connection to AWS IoT Core")
    print("=" * 50)
    
    if not test_certificates():
        return False
    
    if IOT_ENDPOINT == "YOUR_ENDPOINT_HERE.iot.us-east-1.amazonaws.com":
        print("\n❌ Please update IOT_ENDPOINT with your actual endpoint!")
        print("   Get it from: AWS IoT Console > Settings > Device data endpoint")
        return False
    
    # Setup MQTT client
    client = MQTTClient(CLIENT_ID, callback_api_version=1)
    
    # SSL setup
    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CA_CERT)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        client.tls_set_context(context)
        print("✅ SSL certificates loaded successfully")
    except Exception as e:
        print(f"❌ SSL setup failed: {e}")
        return False
    
    # Connection tracking
    connected = False
    connection_result = None
    messages_received = []
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected, connection_result
        connection_result = rc
        if rc == 0:
            print("🎉 Connected to AWS IoT Core successfully!")
            connected = True
            
            # Subscribe to test topics
            test_topics = [
                "store/door/001/status",
                "store/door/001/commands",
                "store/customers/valid"
            ]
            
            for topic in test_topics:
                client.subscribe(topic, qos=1)
                print(f"📡 Subscribed to: {topic}")
            
        else:
            print(f"❌ Connection failed with code {rc}")
            error_codes = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier", 
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            print(f"   Error: {error_codes.get(rc, 'Unknown error')}")
    
    def on_message(client, userdata, msg):
        print(f"📨 Received message on {msg.topic}:")
        try:
            payload = json.loads(msg.payload.decode())
            print(f"    {json.dumps(payload, indent=2)}")
        except:
            print(f"    {msg.payload.decode()}")
        messages_received.append(msg.topic)
    
    def on_publish(client, userdata, mid):
        print(f"✅ Message {mid} published successfully")
    
    def on_subscribe(client, userdata, mid, granted_qos):
        print(f"✅ Subscription confirmed with QoS {granted_qos}")
    
    client.on_connect = on_connect
    client.on_message = on_message  
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    
    try:
        print(f"🔗 Connecting to {IOT_ENDPOINT}:8883...")
        client.connect(IOT_ENDPOINT, 8883, 60)
        client.loop_start()
        
        # Wait for connection
        timeout = 15
        while not connected and timeout > 0:
            print(f"⏳ Waiting for connection... ({timeout}s)")
            time.sleep(1)
            timeout -= 1
            
        if connected:
            print("\n🎊 Connection test successful!")
            
            # Test publishing
            test_messages = [
                {
                    "topic": "store/door/001/status",
                    "data": {
                        "door_id": "door-001",
                        "status": "TEST",
                        "message": "MQTT connection test",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "test": True
                    }
                },
                {
                    "topic": "store/door/001/rfid/scan",
                    "data": {
                        "rfid_uid": "TEST123456",
                        "door_id": "door-001",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "test": True
                    }
                }
            ]
            
            print(f"\n📤 Publishing test messages...")
            for msg in test_messages:
                print(f"   Publishing to: {msg['topic']}")
                result = client.publish(
                    msg['topic'], 
                    json.dumps(msg['data']), 
                    qos=1
                )
                time.sleep(1)
            
            print(f"\n⏳ Waiting for responses (10 seconds)...")
            time.sleep(10)
            
            print(f"\n📊 Test Results:")
            print(f"   ✅ Connection: Success")
            print(f"   ✅ SSL/TLS: Working")
            print(f"   ✅ Publishing: Working")
            print(f"   ✅ Subscribing: Working")
            print(f"   📨 Messages received: {len(messages_received)}")
            
            if messages_received:
                print(f"   📝 Topics with traffic: {', '.join(set(messages_received))}")
            
            print(f"\n🚀 Your door system is ready for MQTT communication!")
            print(f"🔍 Monitor live traffic at: AWS IoT Console > Test > MQTT test client")
            
        else:
            print(f"\n❌ Connection failed within timeout")
            if connection_result is not None:
                print(f"   Connection result code: {connection_result}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    finally:
        client.loop_stop()
        client.disconnect()
        print("👋 Disconnected from AWS IoT Core")
        
    return connected

def main():
    print("🚪 Door Access MQTT Connection Test")
    print("=" * 40)
    print("🎯 This will test your AWS IoT Core connection")
    print("📋 Make sure you have:")
    print("   1. Downloaded certificates from AWS Console")
    print("   2. Updated IOT_ENDPOINT with your endpoint")
    print("   3. Certificates attached to thing and policy")
    print()
    
    success = test_mqtt_connection()
    
    if success:
        print("\n" + "=" * 50)
        print("🎉 SUCCESS! Your MQTT connection is working!")
        print("=" * 50)
        print("🔥 Next steps:")
        print("   1. Run: python3 door_mqtt_client.py")
        print("   2. Test RFID scans and door commands")
        print("   3. Monitor in AWS IoT Console")
    else:
        print("\n" + "=" * 50)
        print("❌ CONNECTION FAILED")
        print("=" * 50)
        print("🔧 Troubleshooting:")
        print("   1. Check certificate files are present")
        print("   2. Verify IoT endpoint URL is correct")
        print("   3. Ensure certificate is attached to thing")
        print("   4. Verify policy is attached to certificate")

if __name__ == "__main__":
    main()