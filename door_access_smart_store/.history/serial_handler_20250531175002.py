import serial
import time
import threading
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
                print(f"📤 Sent command: {command}")
                return True
            except Exception as e:
                print(f"Error sending command: {e}")
                return False
        return False
    
    def parse_arduino_message(self, message):
        message = message.strip()
        print(f"📨 Arduino: {message}")
        
        # Parse access attempts
        if "Access granted:" in message:
            name = message.split("Access granted: ")[1]
            self.db.log_access("", name, "GRANTED")
            self.db.update_system_status(door_state="OPEN")
            print(f"✅ Access granted to {name}")
            
        elif "Access denied:" in message:
            self.db.log_access("", "Unknown", "DENIED")
            print("❌ Access denied")
            
        # Parse registration confirmations
        elif "Registered!" in message:
            print("📝 Registration confirmed by Arduino")
            
        # Parse movement detection
        elif "Movement detected!" in message:
            print("🚶 Movement confirmed - door closing")
            self.db.update_system_status(door_state="CLOSED")
            
        elif "No movement detected." in message:
            print("⚠️  No movement - possible tailgating attempt")
            self.db.log_access("", "System", "NO_MOVEMENT_DETECTED")
    
    def check_pending_commands(self):
        commands = self.db.get_pending_commands()
        for cmd_id, command in commands:
            print(f"📋 Processing command: {command}")
            
            if command == "OPEN_DOOR":
                self.send_command("2")  # Monitor mode to allow access
            elif command == "REGISTER_MODE":
                self.send_command("1")  # Registration mode
            elif command == "MONITOR_MODE":
                self.send_command("2")  # Monitor mode
            elif command == "CALIBRATE_IR":
                self.send_command("3")  # Calibrate IR sensor
            elif command.startswith("ADD_USER:"):
                # Format: ADD_USER:UID:Name
                parts = command.split(":")
                if len(parts) == 3:
                    uid, name = parts[1], parts[2]
                    self.send_command("1")  # Enter registration mode
                    time.sleep(1)
                    # Note: Manual registration still required on Arduino
                    print(f"🔄 Registration mode activated for {name}")
            
            self.db.mark_command_completed(cmd_id)
    
    def run(self):
        if not self.connect():
            return
        
        self.running = True
        print("🚀 Arduino handler started. Monitoring serial communication...")
        print("Press Ctrl+C to stop")
        
        while self.running:
            try:
                # Check for Arduino messages
                if self.serial_conn.in_waiting > 0:
                    message = self.serial_conn.readline().decode('utf-8', errors='ignore')
                    if message.strip():
                        self.parse_arduino_message(message)
                
                # Check for pending commands every 2 seconds
                self.check_pending_commands()
                
                time.sleep(0.5)  # Reasonable delay
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)
        
        self.disconnect()
    
    def stop(self):
        self.running = False

def main():
    print("🏪 Smart Convenience Store - Arduino Handler")
    print("=" * 50)
    
    handler = ArduinoHandler()
    
    try:
        handler.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Arduino handler...")
        handler.stop()

if __name__ == "__main__":
    main()