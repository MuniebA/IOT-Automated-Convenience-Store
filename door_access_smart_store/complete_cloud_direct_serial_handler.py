import serial
import time
import threading
import requests
import json
from datetime import datetime
from config import Config
import logging

# Import our new DynamoDB manager
from dynamodb_manager import DynamoDBManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudDirectArduinoHandler:
    def __init__(self):
        self.port = Config.ARDUINO_PORT
        self.baudrate = Config.ARDUINO_BAUDRATE
        self.serial_conn = None
        
        # Use DynamoDB instead of MySQL
        self.db = DynamoDBManager()
        
        self.running = False
        self.flask_url = "http://localhost:5000"
        
        # Response handler will be initialized later
        self.response_handler = None
        
        logger.info("🌟 Cloud-Direct Arduino Handler initialized")
        
    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Allow Arduino to reset
            logger.info(f"✅ Connected to Arduino on {self.port}")
            print(f"✅ Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Arduino on {self.port}: {e}")
            print(f"❌ Failed to connect to Arduino on {self.port}: {e}")
            print("Make sure:")
            print("1. Arduino is connected to COM4")
            print("2. Arduino IDE Serial Monitor is closed")
            print("3. No other programs are using COM4")
            return False
    
    def disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from Arduino")
            print("Disconnected from Arduino")
    
    def send_command(self, command):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(f"{command}\n".encode())
                logger.info(f"📤 Sent to Arduino: {command}")
                print(f"📤 Sent to Arduino: {command}")
                return True
            except Exception as e:
                logger.error(f"Error sending command: {e}")
                print(f"Error sending command: {e}")
                return False
        return False
    
    def parse_arduino_message(self, message):
        message = message.strip()
        logger.info(f"📨 Arduino: {message}")
        print(f"📨 Arduino: {message}")
        
        # Parse different types of messages from Arduino
        if message.startswith("STATUS:"):
            self.handle_status_message(message)
        elif message.startswith("ACCESS:"):
            self.handle_access_message(message)
        elif message.startswith("REGISTERED:"):
            self.handle_registration_message(message)
        elif message.startswith("MOVEMENT:"):
            self.handle_movement_message(message)
        elif message.startswith("IR_CALIBRATION:"):
            self.handle_calibration_message(message)
        elif message.startswith("CARD_SCANNED:"):
            # MAIN CHANGE: Process using cloud-direct method
            self.handle_cloud_direct_card_scan(message)
        elif message.startswith("ERROR:"):
            self.handle_error_message(message)
        elif message.startswith("RECEIVED:"):
            logger.info(f"✅ Arduino confirmed: {message.split(':', 1)[1]}")
            print(f"✅ Arduino confirmed: {message.split(':', 1)[1]}")
    
    def handle_cloud_direct_card_scan(self, message):
        """NEW: Handle card scan using cloud-direct DynamoDB lookup"""
        parts = message.split(":")
        if len(parts) >= 2:
            rfid_uid = parts[1]
            
            logger.info(f"💳 Cloud-direct processing: {rfid_uid}")
            print(f"💳 Cloud-direct processing: {rfid_uid}")
            
            # STEP 1: Look up customer in DynamoDB
            customer_info = self.db.get_customer_by_rfid(rfid_uid)
            
            if not customer_info['found']:
                # Unknown customer - deny access
                logger.warning(f"❌ Unknown RFID: {rfid_uid}")
                print(f"❌ Unknown RFID: {rfid_uid}")
                
                self.db.log_access_event(
                    None, 
                    rfid_uid, 
                    'ENTRY_DENIED', 
                    'Unknown', 
                    'RFID not registered'
                )
                
                self.send_command("ACCESS_DENIED")
                self.send_command("DISPLAY:Access Denied")
                return
            
            # STEP 2: Determine entry vs exit using cloud data
            action_result = self.determine_cloud_entry_or_exit(rfid_uid, customer_info)
            
            if action_result['action'] == 'entry':
                self.process_cloud_entry(rfid_uid, customer_info)
            elif action_result['action'] == 'exit':
                self.process_cloud_exit(rfid_uid, customer_info)
            else:
                logger.error(f"⚠️ Unknown action: {action_result}")
                self.send_command("DISPLAY:System Error")
    
    def determine_cloud_entry_or_exit(self, rfid_uid, customer_info):
        """Determine entry or exit using DynamoDB active session data"""
        try:
            customer_id = customer_info['customer_id']
            
            # Check for active session in DynamoDB
            active_session = self.db.check_customer_active_session(customer_id)
            
            if active_session:
                # Customer has active session = Exit attempt
                logger.info(f"🚪 Exit detected for {customer_info['customer_name']} (active session exists)")
                return {
                    'action': 'exit',
                    'reason': 'Active session detected',
                    'session': active_session
                }
            else:
                # No active session = Entry attempt
                logger.info(f"🚪 Entry detected for {customer_info['customer_name']} (no active session)")
                return {
                    'action': 'entry',
                    'reason': 'No active session'
                }
                
        except Exception as e:
            logger.error(f"❌ Error determining entry/exit: {e}")
            # Default to entry on error
            return {
                'action': 'entry',
                'reason': 'Error detection - default to entry'
            }
    
    def process_cloud_entry(self, rfid_uid, customer_info):
        """Process entry request using MQTT cloud integration"""
        try:
            customer_name = customer_info['customer_name']
            logger.info(f"🚪 Processing ENTRY for: {customer_name}")
            print(f"🚪 Processing ENTRY for: {customer_name}")
        
            # Log entry attempt
            self.db.log_access_event(
                customer_info['customer_id'],
                rfid_uid,
                'ENTRY_PROCESSING',
                customer_name,
                'Cloud-direct entry processing'
            )
        
            # CHANGED: Use the matched UID format from database lookup
            matched_uid = customer_info.get('matched_format', rfid_uid)
            logger.info(f"🔄 Using matched UID format for Lambda: '{rfid_uid}' → '{matched_uid}'")
            print(f"🔄 Using matched UID format for Lambda: '{rfid_uid}' → '{matched_uid}'")
        
            # Send MQTT message with the format that exists in database
            success = self.send_mqtt_entry_request(matched_uid)
        
            if success:
                # Display processing message
                self.send_command(f"DISPLAY:Processing {customer_name}")
                logger.info(f"✅ Entry request sent to cloud for {customer_name}")
                print(f"✅ Entry request sent to cloud for {customer_name}")
                print(f"⏳ Waiting for Lambda response via MQTT...")
            else:
                # Fallback to local processing
                self.fallback_local_entry(rfid_uid, customer_info)
        
        except Exception as e:
            logger.error(f"❌ Error processing entry: {e}")
            print(f"❌ Error processing entry: {e}")
            self.send_command("DISPLAY:Entry Error")

    
    def process_cloud_exit(self, rfid_uid, customer_info):
        """Process exit request using MQTT cloud integration"""
        try:
            customer_name = customer_info['customer_name']
            logger.info(f"🚪 Processing EXIT for: {customer_name}")
            print(f"🚪 Processing EXIT for: {customer_name}")
        
            # Log exit attempt
            self.db.log_access_event(
                customer_info['customer_id'],
                rfid_uid,
                'EXIT_PROCESSING',
                customer_name,
                'Cloud-direct exit processing'
            )
        
            # CHANGED: Use the matched UID format from database lookup
            matched_uid = customer_info.get('matched_format', rfid_uid)
            logger.info(f"🔄 Using matched UID format for Lambda: '{rfid_uid}' → '{matched_uid}'")
            print(f"🔄 Using matched UID format for Lambda: '{rfid_uid}' → '{matched_uid}'")
        
            # Send MQTT message with the format that exists in database
            success = self.send_mqtt_exit_request(matched_uid)
        
            if success:
                # Display processing message
                self.send_command(f"DISPLAY:Checking {customer_name}")
                logger.info(f"✅ Exit request sent to cloud for {customer_name}")
                print(f"✅ Exit request sent to cloud for {customer_name}")
                print(f"⏳ Waiting for Lambda response via MQTT...")
            else:
                # Fallback to local processing
                self.fallback_local_exit(rfid_uid, customer_info)
        
        except Exception as e:
            logger.error(f"❌ Error processing exit: {e}")
            print(f"❌ Error processing exit: {e}")
            self.send_command("DISPLAY:Exit Error")
    
    def send_mqtt_entry_request(self, rfid_uid):
        """Send MQTT entry request without maintaining connection"""
        try:
            from door_mqtt_client import SmartDoorMQTTClient
            
            # Create temporary client
            mqtt_client = SmartDoorMQTTClient()
            mqtt_client.client_id = f"entry-{int(time.time())}"
            
            if mqtt_client.connect():
                success = mqtt_client.process_entry_request(rfid_uid)
                mqtt_client.disconnect()
                return success
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT entry error: {e}")
            return False
    
    def send_mqtt_exit_request(self, rfid_uid):
        """Send MQTT exit request without maintaining connection"""
        try:
            from door_mqtt_client import SmartDoorMQTTClient
            
            # Create temporary client
            mqtt_client = SmartDoorMQTTClient()
            mqtt_client.client_id = f"exit-{int(time.time())}"
            
            if mqtt_client.connect():
                success = mqtt_client.process_exit_request(rfid_uid)
                mqtt_client.disconnect()
                return success
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT exit error: {e}")
            return False
    
    def fallback_local_entry(self, rfid_uid, customer_info):
        """Fallback to local entry processing"""
        customer_name = customer_info['customer_name']
        logger.info(f"🔄 Fallback to local entry processing for {customer_name}")
        print(f"🔄 Fallback to local entry processing for {customer_name}")
        
        self.db.log_access_event(
            customer_info['customer_id'],
            rfid_uid,
            'ENTRY_SUCCESS',
            customer_name,
            'Local fallback entry granted'
        )
        
        self.send_command("MANUAL_OPEN")
        self.send_command(f"DISPLAY:Welcome {customer_name}")
    
    def fallback_local_exit(self, rfid_uid, customer_info):
        """Fallback to local exit processing"""
        customer_name = customer_info['customer_name']
        logger.info(f"🔄 Fallback to local exit processing for {customer_name}")
        print(f"🔄 Fallback to local exit processing for {customer_name}")
        
        self.db.log_access_event(
            customer_info['customer_id'],
            rfid_uid,
            'EXIT_SUCCESS',
            customer_name,
            'Local fallback exit granted'
        )
        
        self.send_command("MANUAL_OPEN")
        self.send_command(f"DISPLAY:Goodbye {customer_name}")
    
    def handle_status_message(self, message):
        """Handle STATUS: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 2:
            status_type = parts[1]
            
            if status_type == "SYSTEM_READY":
                logger.info("🟢 Arduino system ready")
                print("🟢 Arduino system ready")
                
            elif status_type == "DOOR_OPENING":
                logger.info("🚪 Door opening")
                print("🚪 Door opening")
                
            elif status_type == "DOOR_CLOSED":
                logger.info("🚪 Door closed")
                print("🚪 Door closed")
                
            elif status_type == "MONITOR_MODE_ACTIVE":
                logger.info("👁️  Arduino in monitor mode")
                print("👁️  Arduino in monitor mode")
                
            elif status_type == "REGISTER_MODE_ACTIVE":
                logger.info("📝 Arduino in registration mode")
                print("📝 Arduino in registration mode")
                
            elif status_type == "MONITORING_MOVEMENT":
                logger.info("🔍 Arduino monitoring for movement")
                print("🔍 Arduino monitoring for movement")
                
            elif status_type == "CLOUD_DIRECT_MODE:ENABLED":
                logger.info("☁️  Cloud-direct mode enabled")
                print("☁️  Cloud-direct mode enabled")
    
    def handle_access_message(self, message):
        """Handle ACCESS: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 4:
            access_result = parts[1]
            uid = parts[2]
            name_or_reason = parts[3]
            
            if access_result == "CLOUD_GRANTED":
                logger.info(f"✅ Cloud access granted to {name_or_reason}")
                print(f"✅ Cloud access granted to {name_or_reason}")
                
            elif access_result == "DENIED":
                logger.info(f"❌ Access denied: {name_or_reason}")
                print(f"❌ Access denied: {name_or_reason}")
                
            elif access_result == "MANUAL_OVERRIDE":
                logger.info(f"🔓 Manual door opening by {name_or_reason}")
                print(f"🔓 Manual door opening by {name_or_reason}")
    
    def handle_registration_message(self, message):
        """Handle REGISTERED: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 3:
            uid = parts[1]
            name = parts[2]
            logger.info(f"📝 Registration confirmed: {name} ({uid})")
            print(f"📝 Registration confirmed: {name} ({uid})")
            
            try:
                result = self.db.create_customer(name, uid)
                if result['success']:
                    logger.info(f"✅ Customer added to DynamoDB: {name}")
                    print(f"✅ Customer added to DynamoDB: {name}")
                else:
                    logger.warning(f"⚠️  Failed to add to DynamoDB: {result['reason']}")
                    print(f"⚠️  Failed to add to DynamoDB: {result['reason']}")
            except Exception as e:
                logger.error(f"❌ Error adding to DynamoDB: {e}")
                print(f"❌ Error adding to DynamoDB: {e}")
    
    def handle_movement_message(self, message):
        """Handle MOVEMENT: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 2:
            movement_result = parts[1]
            
            if movement_result == "DETECTED":
                logger.info("🚶 Movement confirmed - access complete")
                print("🚶 Movement confirmed - access complete")
                
            elif movement_result == "NONE_DETECTED":
                logger.warning("⚠️  No movement detected - potential security issue")
                print("⚠️  No movement detected - potential security issue")
                
                self.db.log_access_event(
                    'system',
                    'security_sensor',
                    'SECURITY_ALERT',
                    'System',
                    'No movement detected after door opening'
                )
    
    def handle_calibration_message(self, message):
        """Handle IR_CALIBRATION: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 4 and parts[1] == "COMPLETE":
            avg_value = parts[2]
            new_threshold = parts[3]
            logger.info(f"🎯 IR sensor calibrated: threshold = {new_threshold}")
            print(f"🎯 IR sensor calibrated: threshold = {new_threshold}")
    
    def handle_error_message(self, message):
        """Handle ERROR: messages from Arduino"""
        parts = message.split(":", 1)
        if len(parts) >= 2:
            error_details = parts[1]
            logger.error(f"❌ Arduino error: {error_details}")
            print(f"❌ Arduino error: {error_details}")
            
            self.db.log_access_event(
                'system',
                'arduino',
                'SYSTEM_ERROR',
                'Arduino',
                error_details
            )
    
    def start_cloud_response_handler(self):
        """Start the cloud response handler for Lambda responses"""
        try:
            from cloud_response_handler import add_response_handler_to_serial_handler
            
            logger.info("🌟 Starting Cloud Response Handler...")
            print("🌟 Starting Cloud Response Handler...")
            
            self.response_handler = add_response_handler_to_serial_handler(self)
            
            if self.response_handler and self.response_handler.is_running():
                logger.info("✅ Cloud Response Handler started successfully")
                print("✅ Cloud Response Handler started successfully")
                print("📡 Now listening for Lambda responses!")
                return True
            else:
                logger.warning("⚠️  Cloud Response Handler failed to start")
                print("⚠️  Cloud Response Handler failed to start")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting response handler: {e}")
            print(f"❌ Error starting response handler: {e}")
            return False
    
    def run(self):
        if not self.connect():
            return
        
        # Start cloud response handler
        response_handler_started = self.start_cloud_response_handler()
        
        self.running = True
        logger.info("🚀 Cloud-Direct Arduino handler started")
        print("🚀 Cloud-Direct Arduino handler started")
        print("☁️  Using DynamoDB for all customer data")
        print("📡 MQTT integration for smart cart sessions")
        
        if response_handler_started:
            print("🎯 Lambda response handling ENABLED")
        else:
            print("⚠️  Lambda response handling DISABLED (fallback mode)")
        
        print("🎮 Arduino is now cloud-controlled")
        print("Press Ctrl+C to stop")
        
        # Send initial status request
        time.sleep(1)
        self.send_command("GET_STATUS")
        
        while self.running:
            try:
                # Check for Arduino messages
                if self.serial_conn.in_waiting > 0:
                    message = self.serial_conn.readline().decode('utf-8', errors='ignore')
                    if message.strip():
                        self.parse_arduino_message(message)
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                print(f"Error in main loop: {e}")
                time.sleep(1)
        
        # Cleanup
        if self.response_handler:
            self.response_handler.stop()
        
        self.disconnect()
    
    def stop(self):
        self.running = False

def main():
    print("🏪 Smart Convenience Store - Cloud-Direct IoT Handler")
    print("=" * 60)
    print("☁️  Direct DynamoDB Integration")
    print("📡 Smart Cart Session Management")
    print("🚪 Intelligent Entry/Exit Detection")
    print("🎮 Cloud-Controlled Arduino")
    print("🎯 Lambda Response Processing")
    print("=" * 60)
    
    handler = CloudDirectArduinoHandler()
    
    try:
        handler.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down cloud-direct handler...")
        handler.stop()

if __name__ == "__main__":
    main()
