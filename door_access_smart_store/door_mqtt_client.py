#!/usr/bin/env python3
"""
Updated Door Access MQTT Client with Smart Cart Integration
Now supports entry processing, cart assignment, and exit validation
"""

import json
import time
import ssl
import logging
import queue
import threading
from datetime import datetime
from paho.mqtt.client import Client as MQTTClient
from database import DatabaseManager
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartDoorMQTTClient:
    def __init__(self):
        # AWS IoT Core Configuration
        self.iot_endpoint = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
        self.port = 8883
        self.client_id = "iot-convenience-store-door-001-production"
        
        # Certificate files
        self.ca_cert = "certificates/AmazonRootCA1.pem"
        self.cert_file = "certificates/iot-convenience-store-door-001-production.cert.pem"
        self.key_file = "certificates/iot-convenience-store-door-001-production.private.key"
        
        # MQTT Topics
        self.topics = {
            'status': 'store/door/001/status',
            'entry': 'store/door/001/entry',
            'exit': 'store/door/001/exit',
            'errors': 'store/door/001/errors',
            'commands': 'store/door/001/commands',
            'rfid_scan': 'store/door/001/rfid/scan',
            'exit_request': 'store/door/001/exit/request',
            'customer_valid': 'store/customers/valid',
            'exit_response': 'store/door/001/exit/response'
        }
        
        # Local database connection
        self.db = DatabaseManager()
        
        # MQTT Client
        self.mqtt_client = None
        self.connected = False
        self.running = False
        
        # Door state
        self.current_customer = None
        self.awaiting_exit_response = False
        self.request_queue = queue.Queue()
        self.response_cache = {}
        
    def setup_mqtt_client(self):
        """Configure MQTT client with SSL certificates"""
        try:
            self.mqtt_client = MQTTClient(self.client_id)
            
            # SSL Configuration
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(self.ca_cert)
            context.load_cert_chain(self.cert_file, self.key_file)
            
            self.mqtt_client.tls_set_context(context)
            
            # Callbacks
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            self.mqtt_client.on_message = self.on_message
            self.mqtt_client.on_publish = self.on_publish
            
            logger.info("MQTT client configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up MQTT client: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT client connects"""
        if rc == 0:
            logger.info("🌟 Connected to AWS IoT Core successfully!")
            self.connected = True
            
            # Subscribe to response topics
            client.subscribe(self.topics['customer_valid'], qos=1)
            client.subscribe(self.topics['exit_response'], qos=1)
            client.subscribe(self.topics['commands'], qos=1)
            
            # Publish initial status
            self.publish_door_status("CONNECTED", "Smart door system online with cart integration")
            
        else:
            logger.error(f"❌ Failed to connect to AWS IoT Core: {rc}")
            self.connected = False
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when MQTT client disconnects"""
        logger.warning("⚠️ Disconnected from AWS IoT Core")
        self.connected = False
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.info(f"📨 Received message on {topic}")
            
            if topic == self.topics['customer_valid']:
                self.handle_customer_validation_response(payload)
            elif topic == self.topics['exit_response']:
                self.handle_exit_response(payload)
            elif topic == self.topics['commands']:
                self.handle_door_command(payload)
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    def on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        logger.debug(f"✅ Message {mid} published successfully")
    
    def handle_customer_validation_response(self, response_data):
        """Handle customer validation response from cloud"""
        validation_result = response_data.get('validation_result', {})
        rfid_uid = validation_result.get('rfid_uid')
        is_valid = validation_result.get('valid', False)
        customer_name = validation_result.get('customer_name', 'Unknown')
        assigned_cart = validation_result.get('assigned_cart', 'N/A')
        message = validation_result.get('message', '')
        
        logger.info(f"👤 Entry validation: {customer_name} - {'VALID' if is_valid else 'INVALID'}")
        
        # Store response for Flask app to retrieve
        self.response_cache[rfid_uid] = {
            'type': 'entry_response',
            'valid': is_valid,
            'customer_name': customer_name,
            'assigned_cart': assigned_cart,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if is_valid:
            # Grant entry access
            self.grant_entry_access(rfid_uid, customer_name, assigned_cart, message)
        else:
            # Deny entry access
            self.deny_entry_access(rfid_uid, customer_name, message)
    
    def handle_exit_response(self, response_data):
        """Handle exit validation response from cloud"""
        allow_exit = response_data.get('allow_exit', False)
        message = response_data.get('message', '')
        customer_name = response_data.get('customer_name', 'Unknown')
        rfid_uid = response_data.get('rfid_uid')
        
        logger.info(f"🚪 Exit validation: {customer_name} - {'ALLOWED' if allow_exit else 'DENIED'}")
        
        # Store response for Flask app to retrieve
        self.response_cache[rfid_uid] = {
            'type': 'exit_response',
            'allowed': allow_exit,
            'customer_name': customer_name,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if allow_exit:
            # Grant exit access
            self.grant_exit_access(rfid_uid, customer_name, message)
        else:
            # Deny exit access
            self.deny_exit_access(rfid_uid, customer_name, message)
    
    def get_response_for_rfid(self, rfid_uid):
        """Get cached response for RFID UID"""
        return self.response_cache.get(rfid_uid)
    
    def clear_response_cache(self, rfid_uid):
        """Clear cached response for RFID UID"""
        if rfid_uid in self.response_cache:
            del self.response_cache[rfid_uid]
    
    def handle_door_command(self, command_data):
        """Process door commands from cloud/admin"""
        command_type = command_data.get('command')
        logger.info(f"🎮 Processing door command: {command_type}")
        
        if command_type == 'UNLOCK':
            self.db.add_command("OPEN_DOOR")
            logger.info("🔓 Manual unlock command queued")
            
        elif command_type == 'LOCK':
            self.db.add_command("MONITOR_MODE")
            logger.info("🔒 Lock command queued")
            
        elif command_type == 'STATUS_REQUEST':
            self.publish_door_status("RESPONDING", "Status requested from cloud")
            
        elif command_type == 'EMERGENCY_UNLOCK':
            self.db.add_command("OPEN_DOOR")
            logger.warning("🚨 Emergency unlock command queued")
    
    def process_rfid_scan(self, rfid_uid, scan_context="entry"):
        """Process RFID scan - determine if entry or exit"""
        if scan_context == "entry":
            self.process_entry_request(rfid_uid)
        elif scan_context == "exit":
            self.process_exit_request(rfid_uid)
        else:
            # Auto-detect based on door state or user selection
            self.process_entry_request(rfid_uid)  # Default to entry
    
    def process_entry_request(self, rfid_uid):
        """Process customer entry request with enhanced debugging"""
        logger.info(f"🔍 Processing entry request for RFID: {rfid_uid}")
        
        # Publish RFID scan for cloud validation
        scan_data = {
            'rfid_uid': rfid_uid,
            'door_id': 'door-001',
            'timestamp': datetime.utcnow().isoformat(),
            'scan_type': 'entry'
        }
        
        # ADD DETAILED LOGGING
        logger.info(f"📤 MQTT PUBLISH DEBUG:")
        logger.info(f"   Topic: {self.topics['rfid_scan']}")
        logger.info(f"   Message: {json.dumps(scan_data, indent=2)}")
        logger.info(f"   Connected: {self.connected}")
        logger.info(f"   MQTT Client: {self.mqtt_client}")
        
        if self.connected:
            try:
                logger.info(f"🚀 Attempting to publish to topic: {self.topics['rfid_scan']}")
                
                result = self.mqtt_client.publish(
                    self.topics['rfid_scan'],
                    json.dumps(scan_data),
                    qos=1
                )
                
                # CHECK PUBLISH RESULT
                logger.info(f"📤 Publish result:")
                logger.info(f"   Return code: {result.rc}")
                logger.info(f"   Message ID: {result.mid}")
                
                # Wait for publish to complete
                try:
                    result.wait_for_publish(timeout=5.0)
                    logger.info(f"✅ Message confirmed published to IoT Core")
                except Exception as wait_error:
                    logger.error(f"⚠️ Publish wait timeout or error: {wait_error}")
                
                if result.rc == 0:
                    logger.info(f"📤 Successfully published entry request for validation: {rfid_uid}")
                    return True
                else:
                    logger.error(f"❌ Failed to publish: return code {result.rc}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error publishing entry request: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                return False
        else:
            logger.warning("⚠️ Not connected to cloud, processing locally")
            self.process_local_entry(rfid_uid)
            return False
    
    def process_exit_request(self, rfid_uid):
        """Process customer exit request"""
        logger.info(f"🚪 Processing exit request for RFID: {rfid_uid}")
        
        self.awaiting_exit_response = True
        
        # Publish exit request for cloud validation
        exit_data = {
            'rfid_uid': rfid_uid,
            'door_id': 'door-001',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.connected:
            self.mqtt_client.publish(
                self.topics['exit_request'],
                json.dumps(exit_data),
                qos=1
            )
            logger.info(f"📤 Published exit request for validation: {rfid_uid}")
            return True
        else:
            logger.warning("⚠️ Not connected to cloud, allowing exit")
            self.grant_exit_access(rfid_uid, "Unknown", "Offline mode - exit allowed")
            return False
    
    def grant_entry_access(self, rfid_uid, customer_name, assigned_cart, message):
        """Grant entry access and show cart assignment"""
        try:
            # Queue door unlock command
            self.db.add_command("OPEN_DOOR")
            
            # Store current customer info
            self.current_customer = {
                'rfid_uid': rfid_uid,
                'name': customer_name,
                'assigned_cart': assigned_cart
            }
            
            # Log successful access
            self.db.log_access(rfid_uid, customer_name, "ENTRY_GRANTED")
            
            # Publish entry event
            self.publish_entry_event(rfid_uid, customer_name, True, f"Assigned to {assigned_cart}")
            
            # Update door status
            self.publish_door_status("ENTRY_GRANTED", f"{customer_name} granted access - Use {assigned_cart}")
            
            logger.info(f"✅ Entry granted: {customer_name} → {assigned_cart}")
            
        except Exception as e:
            logger.error(f"❌ Error granting entry access: {e}")
    
    def deny_entry_access(self, rfid_uid, customer_name, reason):
        """Deny entry access"""
        try:
            # Log denied access
            self.db.log_access(rfid_uid, customer_name, "ENTRY_DENIED")
            
            # Publish entry denial
            self.publish_entry_event(rfid_uid, customer_name, False, reason)
            
            # Keep door locked status
            self.publish_door_status("ENTRY_DENIED", f"Access denied: {reason}")
            
            logger.warning(f"❌ Entry denied: {customer_name} - {reason}")
            
        except Exception as e:
            logger.error(f"❌ Error denying entry access: {e}")
    
    def grant_exit_access(self, rfid_uid, customer_name, message):
        """Grant exit access"""
        try:
            # Queue door unlock command
            self.db.add_command("OPEN_DOOR")
            
            # Log successful exit
            self.db.log_access(rfid_uid, customer_name, "EXIT_GRANTED")
            
            # Publish exit event
            self.publish_exit_event(rfid_uid, customer_name, True, message)
            
            # Update door status
            self.publish_door_status("EXIT_GRANTED", message)
            
            # Clear current customer
            self.current_customer = None
            
            logger.info(f"✅ Exit granted: {customer_name}")
            
        except Exception as e:
            logger.error(f"❌ Error granting exit access: {e}")
    
    def deny_exit_access(self, rfid_uid, customer_name, reason):
        """Deny exit access"""
        try:
            # Log denied exit
            self.db.log_access(rfid_uid, customer_name, "EXIT_DENIED")
            
            # Publish exit denial
            self.publish_exit_event(rfid_uid, customer_name, False, reason)
            
            # Keep door locked status
            self.publish_door_status("EXIT_DENIED", reason)
            
            logger.warning(f"❌ Exit denied: {customer_name} - {reason}")
            
        except Exception as e:
            logger.error(f"❌ Error denying exit access: {e}")
    
    def process_local_entry(self, rfid_uid):
        """Process entry locally when cloud is unavailable"""
        # Fallback to local processing using existing database
        logger.info("🔄 Processing entry locally (offline mode)")
        
        # Check local database for user
        user = self.db.get_user_by_uid(rfid_uid)
        if user:
            self.grant_entry_access(rfid_uid, user[1], "Local Cart", "Offline mode - access granted")
        else:
            self.deny_entry_access(rfid_uid, "Unknown", "User not found in local database")
    
    def publish_door_status(self, status, message=""):
        """Publish door status to cloud"""
        if not self.connected:
            return False
            
        status_data = {
            'door_id': 'door-001',
            'status': status,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'current_customer': self.current_customer,
            'system_mode': 'smart_integration'
        }
        
        try:
            result = self.mqtt_client.publish(
                self.topics['status'], 
                json.dumps(status_data), 
                qos=1
            )
            return result.rc == 0
        except Exception as e:
            logger.error(f"❌ Error publishing status: {e}")
            return False
    
    def publish_entry_event(self, rfid_uid, customer_name, granted=True, reason=""):
        """Publish door entry event"""
        if not self.connected:
            return False
            
        entry_data = {
            'door_id': 'door-001',
            'event_type': 'ENTRY_SUCCESS' if granted else 'ENTRY_DENIED',
            'rfid_uid': rfid_uid,
            'customer_name': customer_name,
            'access_granted': granted,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            result = self.mqtt_client.publish(
                self.topics['entry'], 
                json.dumps(entry_data), 
                qos=1
            )
            return result.rc == 0
        except Exception as e:
            logger.error(f"❌ Error publishing entry event: {e}")
            return False
    
    def publish_exit_event(self, rfid_uid, customer_name, granted=True, reason=""):
        """Publish door exit event"""
        if not self.connected:
            return False
            
        exit_data = {
            'door_id': 'door-001',
            'event_type': 'EXIT_SUCCESS' if granted else 'EXIT_DENIED',
            'rfid_uid': rfid_uid,
            'customer_name': customer_name,
            'access_granted': granted,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            result = self.mqtt_client.publish(
                self.topics['exit'], 
                json.dumps(exit_data), 
                qos=1
            )
            return result.rc == 0
        except Exception as e:
            logger.error(f"❌ Error publishing exit event: {e}")
            return False
    
    def connect(self):
        """Connect to AWS IoT Core"""
        if not self.setup_mqtt_client():
            return False
            
        try:
            logger.info(f"🔗 Connecting to {self.iot_endpoint}:{self.port}")
            self.mqtt_client.connect(self.iot_endpoint, self.port, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
            
            if self.connected:
                logger.info("🎉 Successfully connected to AWS IoT Core!")
                return True
            else:
                logger.error("❌ Failed to connect within timeout")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting to AWS IoT Core: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from AWS IoT Core"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        self.connected = False
        logger.info("👋 Disconnected from AWS IoT Core")
    
    def run(self):
        """Main run loop"""
        self.running = True
        
        if not self.connect():
            logger.error("❌ Failed to connect to AWS IoT Core")
            return
        
        logger.info("🚀 Smart Door MQTT client running...")
        logger.info("🎯 Features: Entry processing + Cart assignment + Exit validation")
        logger.info("📊 Monitor: AWS IoT Console > Test > MQTT test client")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                # Check connection status
                if not self.connected:
                    logger.warning("⚠️ Connection lost, attempting to reconnect...")
                    self.connect()
                
                # Publish periodic status updates
                self.publish_door_status("MONITORING", "Smart door system operational")
                
                time.sleep(30)  # Status update every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down smart door MQTT client...")
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
        finally:
            self.disconnect()
    
    def stop(self):
        """Stop the MQTT client"""
        self.running = False


# Flask integration helpers
mqtt_client_instance = None

def get_mqtt_client():
    """Get global MQTT client instance"""
    global mqtt_client_instance
    if mqtt_client_instance is None:
        mqtt_client_instance = SmartDoorMQTTClient()
    return mqtt_client_instance

def start_mqtt_client_background():
    """Start MQTT client in background thread"""
    def run_mqtt():
        client = get_mqtt_client()
        if client.connect():
            logger.info("🎉 MQTT client connected in background")
            # Keep connection alive
            while client.connected:
                time.sleep(1)
        else:
            logger.error("❌ Failed to connect MQTT client in background")
    
    mqtt_thread = threading.Thread(target=run_mqtt, daemon=True)
    mqtt_thread.start()
    logger.info("🚀 Started MQTT client in background thread")


def main():
    """Main function"""
    print("🚪 Smart Door Access System with Cart Integration")
    print("=" * 60)
    print("🎯 Features:")
    print("   • Automatic cart assignment on entry")
    print("   • Checkout validation on exit")
    print("   • Real-time cloud synchronization") 
    print("   • Session management integration")
    print("=" * 60)
    
    # Create and run MQTT client
    door_client = SmartDoorMQTTClient()
    
    try:
        door_client.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopping smart door system...")
        door_client.stop()

if __name__ == "__main__":
    main()