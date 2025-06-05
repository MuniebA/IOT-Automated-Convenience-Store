#!/usr/bin/env python3
import ssl
import os
import time
import json
from paho.mqtt import client as mqtt_client

print("🚪 Clean MQTT Connection Test")
print("=" * 40)

# Configuration
IOT_ENDPOINT = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "door-test-clean"

# Certificate files
CA_CERT = "certificates/AmazonRootCA1.pem"
CERT_FILE = "certificates/iot-convenience-store-door-001-production.cert.pem"
KEY_FILE = "certificates/iot-convenience-store-door-001-production.private.key"

def check_certificates():
    """Check certificate files"""
    print("🔐 Checking certificates...")
    for name, path in [("CA", CA_CERT), ("Certificate", CERT_FILE), ("Private Key", KEY_FILE)]:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✅ {name}: Found ({size} bytes)")
        else:
            print(f"❌ {name}: Missing - {path}")
            return False
    return True

def on_connect(client, userdata, flags, rc):
    """Callback when client connects"""
    if rc == 0:
        print("🎉 Connected to AWS IoT Core!")
        client.connected_flag = True
        
        # Subscribe to test topics
        client.subscribe("store/door/001/status", 1)
        client.subscribe("store/door/001/commands", 1)
        print("📡 Subscribed to topics")
        
    else:
        print(f"❌ Connection failed with code {rc}")
        client.connected_flag = False

def on_message(client, userdata, msg):
    """Callback when message received"""
    print(f"📨 Received: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print(f"    Data: {payload}")
    except:
        print(f"    Raw: {msg.payload.decode()}")

def on_publish(client, userdata, mid):
    """Callback when message published"""
    print(f"✅ Message {mid} published")

def test_connection():
    """Test MQTT connection"""
    
    if not check_certificates():
        return False
    
    # Create MQTT client (compatible way)
    client = mqtt_client.Client(CLIENT_ID)
    client.connected_flag = False
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    
    try:
        # Setup SSL/TLS
        print("🔒 Setting up SSL...")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CA_CERT)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        client.tls_set_context(context)
        print("✅ SSL configured")
        
        # Connect
        print(f"🔗 Connecting to {IOT_ENDPOINT}:8883...")
        client.connect(IOT_ENDPOINT, 8883, 60)
        client.loop_start()
        
        # Wait for connection
        timeout = 10
        while not client.connected_flag and timeout > 0:
            print(f"⏳ Waiting... ({timeout}s)")
            time.sleep(1)
            timeout -= 1
        
        if client.connected_flag:
            print("\n🎊 SUCCESS! Connection established!")
            
            # Test publish
            test_msg = {
                "door_id": "door-001",
                "status": "TEST",
                "message": "Connection test successful",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            print("📤 Publishing test message...")
            result = client.publish("store/door/001/status", json.dumps(test_msg), 1)
            
            # Wait a bit for any responses
            print("⏳ Waiting for responses...")
            time.sleep(5)
            
            print("\n🚀 Test completed successfully!")
            print("🔍 Check AWS IoT Console > Test > MQTT test client")
            print("📡 Subscribe to: store/door/001/#")
            
            return True
        else:
            print("❌ Connection timeout")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    finally:
        if client:
            client.loop_stop()
            client.disconnect()
            print("👋 Disconnected")

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n" + "=" * 50)
        print("🎉 MQTT CONNECTION WORKING!")
        print("Next: Run your door_mqtt_client.py")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ Connection failed - check certificate setup")
        print("=" * 50)
