#!/usr/bin/env python3
"""
Cloud Response Handler - The Missing Piece
Persistent MQTT subscriber to receive Lambda responses and send Arduino commands
"""

import json
import time
import threading
import queue
from datetime import datetime
from door_mqtt_client import SmartDoorMQTTClient
from dynamodb_manager import DynamoDBManager
import logging

logger = logging.getLogger(__name__)

class CloudResponseHandler:
    def __init__(self, arduino_handler=None):
        """Initialize response handler with Arduino connection"""
        self.arduino_handler = arduino_handler
        self.db = DynamoDBManager()
        
        # Create persistent MQTT client
        self.mqtt_client = SmartDoorMQTTClient()
        self.mqtt_client.client_id = "persistent-response-handler"
        
        # Response processing queue
        self.response_queue = queue.Queue()
        self.running = False
        
        # Override MQTT callbacks to handle responses
        self.setup_response_handlers()
        
    def setup_response_handlers(self):
        """Setup MQTT callbacks to handle Lambda responses"""
        original_on_message = self.mqtt_client.on_message
        
        def enhanced_on_message(client, userdata, msg):
            """Enhanced message handler to process Lambda responses"""
            try:
                topic = msg.topic
                payload = json.loads(msg.payload.decode())
                
                logger.info(f"📨 Received cloud response on {topic}")
                print(f"📨 Received cloud response on {topic}")
                
                if topic == 'store/customers/valid':
                    self.handle_entry_response(payload)
                elif topic == 'store/door/001/exit/response':
                    self.handle_exit_response(payload)
                else:
                    # Call original handler for other messages
                    original_on_message(client, userdata, msg)
                    
            except Exception as e:
                logger.error(f"❌ Error processing cloud response: {e}")
                print(f"❌ Error processing cloud response: {e}")
        
        # Replace the message handler
        self.mqtt_client.on_message = enhanced_on_message
    
    def handle_entry_response(self, response_data):
        """Handle entry validation response from Lambda"""
        try:
            validation_result = response_data.get('validation_result', {})
            rfid_uid = validation_result.get('rfid_uid')
            is_valid = validation_result.get('valid', False)
            customer_name = validation_result.get('customer_name', 'Unknown')
            assigned_cart = validation_result.get('assigned_cart', 'N/A')
            message = validation_result.get('message', '')
            
            logger.info(f"🎯 Entry Response: {customer_name} - {'VALID' if is_valid else 'INVALID'}")
            print(f"🎯 Entry Response: {customer_name} - {'VALID' if is_valid else 'INVALID'}")
            
            if is_valid:
                # Grant entry access
                logger.info(f"✅ Granting entry: {customer_name} → {assigned_cart}")
                print(f"✅ Granting entry: {customer_name} → {assigned_cart}")
                
                # Send Arduino commands
                if self.arduino_handler:
                    self.arduino_handler.send_command("MANUAL_OPEN")
                    self.arduino_handler.send_command(f"DISPLAY:Welcome! Use {assigned_cart}")
                
                # Log success
                self.db.log_access_event(
                    validation_result.get('customer_id', 'unknown'),
                    rfid_uid,
                    'ENTRY_SUCCESS',
                    customer_name,
                    f'Cloud entry granted - {assigned_cart}'
                )
                
            else:
                # Deny entry access
                reason = validation_result.get('reason', 'Access denied')
                logger.warning(f"❌ Denying entry: {customer_name} - {reason}")
                print(f"❌ Denying entry: {customer_name} - {reason}")
                
                # Send Arduino commands
                if self.arduino_handler:
                    self.arduino_handler.send_command("ACCESS_DENIED")
                    self.arduino_handler.send_command(f"DISPLAY:Access Denied")
                
                # Log denial
                self.db.log_access_event(
                    None,
                    rfid_uid,
                    'ENTRY_DENIED',
                    customer_name,
                    reason
                )
                
        except Exception as e:
            logger.error(f"❌ Error handling entry response: {e}")
            print(f"❌ Error handling entry response: {e}")
    
    def handle_exit_response(self, response_data):
        """Handle exit validation response from Lambda"""
        try:
            allow_exit = response_data.get('allow_exit', False)
            message = response_data.get('message', '')
            customer_name = response_data.get('customer_name', 'Unknown')
            rfid_uid = response_data.get('rfid_uid')
            
            logger.info(f"🎯 Exit Response: {customer_name} - {'ALLOWED' if allow_exit else 'DENIED'}")
            print(f"🎯 Exit Response: {customer_name} - {'ALLOWED' if allow_exit else 'DENIED'}")
            
            if allow_exit:
                # Grant exit access
                logger.info(f"✅ Granting exit: {customer_name}")
                print(f"✅ Granting exit: {customer_name}")
                print(f"💬 Message: {message}")
                
                # Send Arduino commands
                if self.arduino_handler:
                    self.arduino_handler.send_command("MANUAL_OPEN")
                    self.arduino_handler.send_command(f"DISPLAY:Goodbye {customer_name}!")
                
                # Log success
                self.db.log_access_event(
                    'unknown',  # Lambda should provide customer_id
                    rfid_uid,
                    'EXIT_SUCCESS',
                    customer_name,
                    f'Cloud exit granted - {message}'
                )
                
            else:
                # Deny exit access
                logger.warning(f"❌ Denying exit: {customer_name}")
                print(f"❌ Denying exit: {customer_name}")
                print(f"💬 Reason: {message}")
                
                # Send Arduino commands
                if self.arduino_handler:
                    self.arduino_handler.send_command(f"DISPLAY:{message}")
                
                # Log denial
                self.db.log_access_event(
                    'unknown',
                    rfid_uid,
                    'EXIT_DENIED',
                    customer_name,
                    message
                )
                
        except Exception as e:
            logger.error(f"❌ Error handling exit response: {e}")
            print(f"❌ Error handling exit response: {e}")
    
    def start(self):
        """Start the persistent response handler"""
        try:
            logger.info("🚀 Starting Cloud Response Handler...")
            print("🚀 Starting Cloud Response Handler...")
            
            # Connect to MQTT
            if self.mqtt_client.connect():
                logger.info("✅ Connected to AWS IoT Core for responses")
                print("✅ Connected to AWS IoT Core for responses")
                
                # Subscribe to response topics
                self.mqtt_client.mqtt_client.subscribe('store/customers/valid', qos=1)
                self.mqtt_client.mqtt_client.subscribe('store/door/001/exit/response', qos=1)
                
                logger.info("📡 Subscribed to Lambda response topics")
                print("📡 Subscribed to Lambda response topics")
                print("   • store/customers/valid (entry responses)")
                print("   • store/door/001/exit/response (exit responses)")
                
                self.running = True
                return True
            else:
                logger.error("❌ Failed to connect to AWS IoT Core")
                print("❌ Failed to connect to AWS IoT Core")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting response handler: {e}")
            print(f"❌ Error starting response handler: {e}")
            return False
    
    def stop(self):
        """Stop the response handler"""
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        logger.info("🛑 Cloud Response Handler stopped")
        print("🛑 Cloud Response Handler stopped")
    
    def is_running(self):
        """Check if response handler is running"""
        return self.running and self.mqtt_client.connected

# Integration function for the serial handler
def add_response_handler_to_serial_handler(serial_handler):
    """Add cloud response handling to the existing serial handler"""
    
    # Create response handler
    response_handler = CloudResponseHandler(serial_handler)
    
    # Start response handler in background thread
    def start_response_handler():
        if response_handler.start():
            logger.info("🌟 Cloud response handler started in background")
            print("🌟 Cloud response handler started in background")
            
            # Keep it running
            while response_handler.is_running():
                time.sleep(1)
        else:
            logger.error("❌ Failed to start cloud response handler")
            print("❌ Failed to start cloud response handler")
    
    # Start in daemon thread
    response_thread = threading.Thread(target=start_response_handler, daemon=True)
    response_thread.start()
    
    # Give it time to connect
    time.sleep(3)
    
    return response_handler

def test_response_handler():
    """Test the response handler independently"""
    print("🧪 Testing Cloud Response Handler")
    print("=" * 40)
    
    handler = CloudResponseHandler()
    
    try:
        if handler.start():
            print("✅ Response handler started successfully")
            print("🔄 Waiting for Lambda responses...")
            print("   (Try scanning RFID card in another terminal)")
            print("   Press Ctrl+C to stop")
            
            # Keep running until interrupted
            while handler.is_running():
                time.sleep(1)
                
        else:
            print("❌ Failed to start response handler")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping response handler test...")
        handler.stop()

if __name__ == "__main__":
    test_response_handler()
