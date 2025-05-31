from database import DatabaseManager
import time

def test_arduino_commands():
    db = DatabaseManager()
    
    print("🧪 Testing Arduino Commands via Database...")
    print("Make sure serial_handler.py is running!")
    
    # Test 1: Set to monitor mode
    print("\n1. Testing MONITOR_MODE command...")
    db.add_command("MONITOR_MODE")
    time.sleep(2)
    
    # Test 2: Manual door open
    print("2. Testing MANUAL_OPEN command...")
    db.add_command("OPEN_DOOR")
    time.sleep(3)
    
    # Test 3: Registration mode
    print("3. Testing REGISTER_MODE command...")
    db.add_command("REGISTER_MODE")
    time.sleep(2)
    
    # Test 4: Add a new user
    print("4. Testing ADD_USER command...")
    db.add_command("ADD_USER:TEST123:John Doe")
    time.sleep(2)
    
    # Test 5: Back to monitor mode
    print("5. Back to MONITOR_MODE...")
    db.add_command("MONITOR_MODE")
    time.sleep(2)
    
    print("\n✅ All commands sent!")
    print("Check the serial_handler.py terminal for Arduino responses")

if __name__ == "__main__":
    test_arduino_commands()