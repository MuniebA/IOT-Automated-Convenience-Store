import mysql.connector
from mysql.connector import Error
import threading
from datetime import datetime
from config import Config

class DatabaseManager:
    def __init__(self):
        self.config = {
            'host': Config.DB_HOST,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'autocommit': True
        }
        self.lock = threading.Lock()
    
    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            print(f"Database connection error: {e}")
            return None
    
    def add_user(self, uid, name):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                query = "INSERT INTO users (uid, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = %s"
                cursor.execute(query, (uid, name, name))
                cursor.close()
                return True
            except Error as e:
                print(f"Error adding user: {e}")
                return False
            finally:
                if conn.is_connected():
                    conn.close()
    
    def get_all_users(self):
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT uid, name, created_at FROM users ORDER BY created_at DESC")
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            print(f"Error getting users: {e}")
            return []
        finally:
            if conn.is_connected():
                conn.close()
    
    def delete_user(self, uid):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE uid = %s", (uid,))
                cursor.close()
                return True
            except Error as e:
                print(f"Error deleting user: {e}")
                return False
            finally:
                if conn.is_connected():
                    conn.close()
    
    def log_access(self, uid, name, result):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                query = "INSERT INTO access_logs (uid, name, access_result) VALUES (%s, %s, %s)"
                cursor.execute(query, (uid, name, result))
                cursor.close()
                return True
            except Error as e:
                print(f"Error logging access: {e}")
                return False
            finally:
                if conn.is_connected():
                    conn.close()
    
    def get_recent_logs(self, limit=50):
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT uid, name, access_result, timestamp FROM access_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            print(f"Error getting logs: {e}")
            return []
        finally:
            if conn.is_connected():
                conn.close()
    
    def add_command(self, command):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO commands (command) VALUES (%s)", (command,))
                cursor.close()
                return True
            except Error as e:
                print(f"Error adding command: {e}")
                return False
            finally:
                if conn.is_connected():
                    conn.close()
    
    def get_pending_commands(self):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return []
            
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, command FROM commands WHERE status = 'PENDING' ORDER BY created_at")
                result = cursor.fetchall()
                cursor.close()
                return result
            except Error as e:
                print(f"Error getting commands: {e}")
                return []
            finally:
                if conn.is_connected():
                    conn.close()
    
    def mark_command_completed(self, command_id):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE commands SET status = 'COMPLETED' WHERE id = %s", (command_id,))
                cursor.close()
                return True
            except Error as e:
                print(f"Error marking command complete: {e}")
                return False
            finally:
                if conn.is_connected():
                    conn.close()
    
    def update_system_status(self, door_state=None, ir_threshold=None):
        with self.lock:
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                if door_state:
                    cursor.execute("UPDATE system_status SET door_state = %s, last_activity = NOW() WHERE id = 1", (door_state,))
                if ir_threshold:
                    cursor.execute("UPDATE system_status SET ir_threshold = %s WHERE id = 1", (ir_threshold,))
                cursor.close()
                return True
            except Error as e:
                print(f"Error updating status: {e}")
                return False
            finally:
                if conn.is_connected():
                    conn.close()
    
    def get_system_status(self):
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT door_state, last_activity, ir_threshold FROM system_status WHERE id = 1")
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"Error getting status: {e}")
            return None
        finally:
            if conn.is_connected():
                conn.close()

# Test database connection
def test_connection():
    db = DatabaseManager()
    status = db.get_system_status()
    if status:
        print("✅ Database connection successful!")
        print(f"Current door state: {status[0]}")
    else:
        print("❌ Database connection failed!")

if __name__ == "__main__":
    test_connection()