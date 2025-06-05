#!/usr/bin/env python3
import ssl
import socket
import os
from paho.mqtt import client as mqtt_client

# Configuration
IOT_ENDPOINT = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "door-debug-test"
CA_CERT = "certificates/AmazonRootCA1.pem"
CERT_FILE = "certificates/iot-convenience-store-door-001-production.cert.pem"
KEY_FILE = "certificates/iot-convenience-store-door-001-production.private.key"

def debug_ssl_handshake():
    """Test SSL handshake manually"""
    print("🔍 Testing SSL handshake...")
    
    try:
        # Create SSL context
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CA_CERT)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        
        # Test connection
        sock = socket.create_connection((IOT_ENDPOINT, 8883), timeout=10)
        ssock = context.wrap_socket(sock, server_hostname=IOT_ENDPOINT)
        
        print(f"✅ SSL handshake successful!")
        print(f"   Protocol: {ssock.version()}")
        print(f"   Cipher: {ssock.cipher()}")
        
        ssock.close()
        return True
        
    except ssl.SSLError as e:
        print(f"❌ SSL Error: {e}")
        return False
    except socket.timeout:
        print(f"❌ Connection timeout to {IOT_ENDPOINT}:8883")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def debug_mqtt_connection():
    """Test MQTT with detailed logging"""
    print("\n🔍 Testing MQTT connection with debug...")
    
    def on_connect(client, userdata, flags, rc):
        print(f"📡 Connection result: {rc}")
        if rc == 0:
            print("✅ MQTT connected successfully!")
            client.connected_flag = True
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable", 
                4: "Bad username or password",
                5: "Not authorized"
            }
            print(f"❌ MQTT connection failed: {error_messages.get(rc, f'Unknown error {rc}')}")
            client.connected_flag = False
    
    def on_disconnect(client, userdata, rc):
        print(f"📡 Disconnected with result: {rc}")
        client.connected_flag = False
    
    def on_log(client, userdata, level, buf):
        print(f"🔎 MQTT Log: {buf}")
    
    # Create client with logging
    client = mqtt_client.Client(CLIENT_ID)
    client.connected_flag = False
    client.enable_logger()
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_log = on_log
    
    try:
        # Setup SSL
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CA_CERT)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        client.tls_set_context(context)
        
        # Connect with timeout
        print(f"🔗 Attempting MQTT connection...")
        client.connect(IOT_ENDPOINT, 8883, 60)
        client.loop_start()
        
        # Wait for connection
        import time
        timeout = 15
        while not hasattr(client, 'connected_flag') and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
        if hasattr(client, 'connected_flag') and client.connected_flag:
            print("🎉 MQTT connection successful!")
            return True
        else:
            print("❌ MQTT connection failed or timed out")
            return False
            
    except Exception as e:
        print(f"❌ MQTT error: {e}")
        return False
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    print("🔧 Debug MQTT Connection")
    print("=" * 30)
    
    # Test 1: SSL handshake
    ssl_ok = debug_ssl_handshake()
    
    if ssl_ok:
        # Test 2: MQTT connection
        mqtt_ok = debug_mqtt_connection()
        
        if mqtt_ok:
            print("\n🎉 All tests passed! MQTT should work.")
        else:
            print("\n❌ MQTT connection failed despite SSL working.")
            print("   This suggests certificate/policy issues in AWS.")
    else:
        print("\n❌ SSL handshake failed.")
        print("   Check certificate files and network connectivity.")
