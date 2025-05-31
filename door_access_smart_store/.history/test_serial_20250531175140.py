from database import DatabaseManager
import time

def test_database_operations():
    print("🧪 Testing Serial Handler Database Operations...")
    db = DatabaseManager()
    
    # Test adding commands
    print("1. Testing command queue...")
    result1 = db.add_command("OPEN_DOOR")
    result2 = db.add_command("REGISTER_MODE")
    print(f"Commands added: {result1}, {result2}")
    
    # Test getting pending commands
    print("2. Testing command retrieval...")
    commands = db.get_pending_commands()
    print(f"Pending commands: {commands}")
    
    # Test marking commands complete
    if commands:
        print("3. Testing command completion...")
        for cmd_id, cmd in commands:
            db.mark_command_completed(cmd_id)
            print(f"Marked command {cmd_id} as completed")
    
    # Test logging access
    print("4. Testing access logging...")
    db.log_access("ABC123", "John Doe", "GRANTED")
    db.log_access("DEF456", "Unknown", "DENIED")
    
    # Test status updates
    print("5. Testing status updates...")
    db.update_system_status(door_state="OPEN")
    time.sleep(1)
    db.update_system_status(door_state="CLOSED")
    
    print("✅ All database operations tested!")

if __name__ == "__main__":
    test_database_operations()