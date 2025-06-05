import serial
import time
import threading
import requests
from database import DatabaseManager
from config import Config
import re

class ArduinoHandler:
    def __init__(self):
        self.port = Config.ARDUINO_PORT
        self.baudrate = Config.ARDUINO_BAUDRATE
        self.serial_conn = None
        self.db = DatabaseManager()
        self.running = False
        self.flask_url = "http://localhost:5000"
        
    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Allow Arduino to reset
            print(f"✅ Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Arduino on {self.port}: {e}")
            print("Make sure:")
            print("1. Arduino is connected to COM4")
            print("2. Arduino IDE Serial Monitor is closed")
            print("3. No other programs are using COM4")
            return False
    
    def disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Disconnected from Arduino")
    
    def send_command(self, command):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(f"{command}\n".encode())
                print(f"📤 Sent to Arduino: {command}")
                return True
            except Exception as e:
                print(f"Error sending command: {e}")
                return False
        return False
    
    def parse_arduino_message(self, message):
        message = message.strip()
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
            self.handle_card_scanned_message(message)
        elif message.startswith("ERROR:"):
            self.handle_error_message(message)
        elif message.startswith("RECEIVED:"):
            print(f"✅ Arduino confirmed: {message.split(':', 1)[1]}")
    
    def handle_status_message(self, message):
        """Handle STATUS: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 2:
            status_type = parts[1]
            
            if status_type == "SYSTEM_READY":
                self.db.update_system_status(door_state="READY")
                print("🟢 Arduino system ready")
                
            elif status_type == "DOOR_OPENING":
                self.db.update_system_status(door_state="OPENING")
                
            elif status_type == "DOOR_CLOSED":
                self.db.update_system_status(door_state="CLOSED")
                
            elif status_type == "MONITOR_MODE_ACTIVE":
                print("👁️  Arduino in monitor mode")
                
            elif status_type == "REGISTER_MODE_ACTIVE":
                print("📝 Arduino in registration mode")
                
            elif status_type == "MONITORING_MOVEMENT":
                print("🔍 Arduino monitoring for movement")
    
    def handle_access_message(self, message):
        """Handle ACCESS: messages from Arduino"""
        # Format: ACCESS:GRANTED:UID:Name or ACCESS:DENIED:UID:Reason
        parts = message.split(":")
        if len(parts) >= 4:
            access_result = parts[1]  # GRANTED or DENIED
            uid = parts[2]
            name_or_reason = parts[3]
            
            if access_result == "GRANTED":
                self.db.log_access(uid, name_or_reason, "GRANTED")
                self.db.update_system_status(door_state="OPEN")
                print(f"✅ Access granted to {name_or_reason}")
                
            elif access_result == "DENIED":
                self.db.log_access(uid, name_or_reason, "DENIED")
                print(f"❌ Access denied: {name_or_reason}")
                
            elif access_result == "MANUAL_OVERRIDE":
                self.db.log_access("MANUAL", name_or_reason, "MANUAL_OPEN")
                print(f"🔓 Manual door opening by {name_or_reason}")
    
    def handle_registration_message(self, message):
        """Handle REGISTERED: messages from Arduino"""
        # Format: REGISTERED:UID:Name
        parts = message.split(":")
        if len(parts) >= 3:
            uid = parts[1]
            name = parts[2]
            print(f"📝 Registration confirmed: {name} ({uid})")
            self.db.log_access(uid, name, "REGISTERED")
    
    def handle_movement_message(self, message):
        """Handle MOVEMENT: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 2:
            movement_result = parts[1]
            
            if movement_result == "DETECTED":
                print("🚶 Movement confirmed - access complete")
                self.db.update_system_status(door_state="CLOSED")
                
            elif movement_result == "NONE_DETECTED":
                print("⚠️  No movement detected - potential security issue")
                self.db.log_access("SYSTEM", "Security", "NO_MOVEMENT_ALERT")
    
    def handle_calibration_message(self, message):
        """Handle IR_CALIBRATION: messages from Arduino"""
        parts = message.split(":")
        if len(parts) >= 4 and parts[1] == "COMPLETE":
            avg_value = parts[2]
            new_threshold = parts[3]
            self.db.update_system_status(ir_threshold=int(new_threshold))
            print(f"🎯 IR sensor calibrated: threshold = {new_threshold}")
    
    def handle_card_scanned_message(self, message):
        """Handle CARD_SCANNED: messages - now with name included"""
        parts = message.split(":")
        if len(parts) >= 2:
            uid = parts[1]
            name = parts[2] if len(parts) > 2 else "Unknown"
            
            print(f"💳 Card scanned: {uid} ({name})")
            
            # Send both UID and name to Flask
            self.process_rfid_with_flask(uid, name)
    
    def display_message(self, message):
        """Display message to user (LCD or console)"""
        print(f"📺 DISPLAY: {message}")
        # TODO: Add LCD display command when ready
        # self.send_command(f"DISPLAY:{message}")
    
    def handle_error_message(self, message):
        """Handle ERROR: messages from Arduino"""
        parts = message.split(":", 1)
        if len(parts) >= 2:
            error_details = parts[1]
            print(f"❌ Arduino error: {error_details}")
    
    def process_rfid_with_flask(self, rfid_uid, user_name="Unknown"):
        """Process RFID scan with name included"""
        try:
            print(f"🔗 Sending RFID {rfid_uid} ({user_name}) to Flask...")
            
            # Send both UID and name
            response = requests.post(
                f"{self.flask_url}/process_rfid_scan",
                json={
                    'rfid_uid': rfid_uid,
                    'user_name': user_name
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.handle_flask_response(rfid_uid, result)
            else:
                print(f"❌ Flask endpoint error: {response.status_code}")
                self.fallback_to_local_processing(rfid_uid)
                
        except Exception as e:
            print(f"❌ Error calling Flask: {e}")
            self.fallback_to_local_processing(rfid_uid)
    
    def handle_flask_response(self, rfid_uid, result):
        """Handle response from Flask endpoint"""
        status = result.get('status', 'unknown')
        message = result.get('message', 'No message')
        action = result.get('action', 'none')
        user_name = result.get('user_name', 'Unknown')
        cloud_processing = result.get('cloud_processing', False)
        
        print(f"📋 Flask response: {status} - {message}")
        
        if status == 'granted':
            # Access granted - door should open
            print(f"✅ Access granted for {user_name} ({action})")
            self.send_command("MANUAL_OPEN")  # Open door
            
            # Display message on LCD/console
            if action == 'entry':
                assigned_cart = result.get('assigned_cart', 'cart-001')
                self.display_message(f"Welcome {user_name}! Use {assigned_cart}")
            else:  # exit
                self.display_message(f"Goodbye {user_name}! Thank you!")
                
        elif status == 'denied':
            # Access denied
            print(f"❌ Access denied for {user_name}: {message}")
            self.display_message(f"Access Denied: {message}")
            
        elif status == 'processing':
            # Cloud processing in progress
            if cloud_processing:
                print(f"⏳ Cloud processing for {user_name}...")
                self.display_message(f"Processing {user_name}...")
                # Wait for cloud response (handled by MQTT client)
            else:
                print(f"🔄 Local processing completed for {user_name}")
                
        else:
            print(f"⚠️ Unknown status: {status}")
            self.display_message("Processing error - try again")
    
    def fallback_to_local_processing(self, rfid_uid):
        """Fallback to original local processing if Flask fails"""
        print(f"🔄 Falling back to local processing for: {rfid_uid}")
        
        # Use existing local database lookup
        try:
            # Check if user exists locally
            conn = self.db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT uid, name FROM users WHERE uid = %s", (rfid_uid,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if user:
                    user_name = user[1]
                    self.db.log_access(rfid_uid, user_name, "GRANTED")
                    self.send_command("MANUAL_OPEN")
                    self.display_message(f"Welcome {user_name}!")
                    print(f"✅ Local access granted: {user_name}")
                else:
                    self.db.log_access(rfid_uid, "Unknown", "DENIED")
                    self.display_message("Access Denied: Unknown card")
                    print(f"❌ Local access denied: Unknown card")
            else:
                print("❌ Database connection failed in fallback")
                self.display_message("System error - try again")
                
        except Exception as e:
            print(f"❌ Error in fallback processing: {e}")
            self.display_message("System error - try again")
    
    def check_pending_commands(self):
        """Check for pending commands from web interface"""
        commands = self.db.get_pending_commands()
        for cmd_id, command in commands:
            print(f"📋 Processing web command: {command}")
            
            if command == "OPEN_DOOR":
                self.send_command("MANUAL_OPEN")
                
            elif command == "REGISTER_MODE":
                self.send_command("REGISTER_MODE")
                
            elif command == "MONITOR_MODE":
                self.send_command("MONITOR_MODE")
                
            elif command == "CALIBRATE_IR":
                self.send_command("CALIBRATE_IR")
                
            elif command.startswith("ADD_USER:"):
                # Forward the ADD_USER command directly to Arduino
                self.send_command(command)
                
            elif command == "GET_STATUS":
                self.send_command("GET_STATUS")
            
            # Mark command as completed
            self.db.mark_command_completed(cmd_id)
    
    def run(self):
        if not self.connect():
            return
        
        self.running = True
        print("🚀 Arduino IoT handler started")
        print("🎮 Arduino is now controlled by the web interface")
        print("🌐 Use the Flask app to send commands")
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
                
                # Check for pending commands from web interface
                self.check_pending_commands()
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)
        
        self.disconnect()
    
    def stop(self):
        self.running = False

def main():
    print("🏪 Smart Convenience Store - IoT Arduino Handler")
    print("=" * 55)
    print("🎮 Arduino is controlled by web interface")
    print("🌐 Start Flask app in another terminal")
    
    handler = ArduinoHandler()
    
    try:
        handler.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Arduino handler...")
        handler.stop()

if __name__ == "__main__":
    main()
