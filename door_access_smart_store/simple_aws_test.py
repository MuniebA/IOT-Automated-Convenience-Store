#!/usr/bin/env python3
"""
Simple AWS IoT connection test without dependencies
"""
import ssl
import socket
import time
import json
from paho.mqtt import client as mqtt

# Your configuration
ENDPOINT = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "simple-test-client"

# Certificate files (check which ones exist)
import os
if os.path.exists("certificates/root-CA.crt"):
    CA_CERT = "certificates/root-CA.crt"
elif os.path.exists("certificates/AmazonRootCA1.pem"):
    CA_CERT = "certificates/AmazonRootCA1.pem"
else:
    print("❌ No CA certificate found!")
    exit(1)

CERT_FILE = "certificates/iot-convenience-store-door-001-production.cert.pem"
KEY_FILE = "certificates/iot-convenience-store-door-001-production.private.key"

print(f"🔐 Using CA cert: {CA_CERT}")

def test_basic_connection():
    """Test basic socket connection to port 8883"""
    print("🔍 Testing basic socket connection...")
    try:
        sock = socket.create_connection((ENDPOINT, 8883), timeout=10)
        print("✅ Socket connection successful")
        sock.close()
        return True
    except Exception as e:
        print(f"❌ Socket connection failed: {e}")
        return False

def test_ssl_connection():
    """Test SSL connection"""
    print("🔒 Testing SSL connection...")
    try:
        # Create SSL context
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # First try without client certificates
        sock = socket.create_connection((ENDPOINT, 8883), timeout=10)
        ssock = context.wrap_socket(sock, server_hostname=ENDPOINT)
        
        print("✅ Basic SSL connection successful")
        print(f"   SSL version: {ssock.version()}")
        
        ssock.close()
        return True
        
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
        return False

def test_ssl_with_certs():
    """Test SSL with client certificates"""
    print("🔑 Testing SSL with client certificates...")
    try:
        # Create SSL context with client certs
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CA_CERT)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        
        sock = socket.create_connection((ENDPOINT, 8883), timeout=10)
        ssock = context.wrap_socket(sock, server_hostname=ENDPOINT)
        
        print("✅ SSL with client certs successful!")
        print(f"   SSL version: {ssock.version()}")
        print(f"   Cipher: {ssock.cipher()}")
        
        ssock.close()
        return True
        
    except ssl.SSLError as e:
        print(f"❌ SSL certificate error: {e}")
        return False
    except Exception as e:
        print(f"❌ SSL connection error: {e}")
        return False

def test_mqtt_minimal():
    """Test minimal MQTT connection"""
    print("📡 Testing MQTT connection...")
    
    connected = False
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            print("✅ MQTT connected!")
            connected = True
        else:
            print(f"❌ MQTT connection failed: {rc}")
    
    try:
        # Create MQTT client
        client = mqtt.Client(CLIENT_ID)
        client.on_connect = on_connect
        
        # Setup SSL
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CA_CERT)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        client.tls_set_context(context)
        
        # Connect
        client.connect(ENDPOINT, 8883, 60)
        client.loop_start()
        
        # Wait for connection
        for i in range(10):
            if connected:
                break
            time.sleep(1)
            print(f"   Waiting... {10-i}s")
        
        if connected:
            print("🎉 MQTT connection successful!")
            # Try to publish a test message
            client.publish("test/topic", "Hello from Raspberry Pi!")
            time.sleep(2)
            return True
        else:
            print("❌ MQTT connection timeout")
            return False
            
    except Exception as e:
        print(f"❌ MQTT error: {e}")
        return False
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    print("🧪 AWS IoT Connection Diagnostic")
    print("=" * 40)
    
    # Test 1: Basic connectivity
    if not test_basic_connection():
        print("❌ Basic connection failed - check network/firewall")
        exit(1)
    
    # Test 2: SSL without certs
    if not test_ssl_connection():
        print("❌ SSL connection failed - check network/TLS")
        exit(1)
    
    # Test 3: SSL with client certs
    if not test_ssl_with_certs():
        print("❌ SSL with client certificates failed")
        print("   This suggests certificate/key file issues")
        exit(1)
    
    # Test 4: MQTT
    if test_mqtt_minimal():
        print("\n🎉 ALL TESTS PASSED!")
        print("Your certificates and connection are working!")
    else:
        print("\n❌ MQTT failed despite SSL working")
        print("This suggests AWS policy/permission issues")
