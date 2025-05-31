from flask import Flask, jsonify
from database import DatabaseManager
from config import Config

app = Flask(__name__)
db = DatabaseManager()

@app.route('/')
def test_home():
    return """
    <h1>Smart Store - Test Interface</h1>
    <p><a href="/test_db">Test Database</a></p>
    <p><a href="/test_add_user">Test Add User</a></p>
    <p><a href="/test_logs">Test Logs</a></p>
    <p><a href="/api/status">API Status</a></p>
    """

@app.route('/test_db')
def test_db():
    try:
        status = db.get_system_status()
        users = db.get_all_users()
        logs = db.get_recent_logs(5)
        
        return jsonify({
            "database": "connected",
            "status": status,
            "total_users": len(users),
            "recent_logs_count": len(logs)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test_add_user')
def test_add_user():
    # Add a test user
    result = db.add_user("TEST123", "Test User")
    return jsonify({"add_user_success": result})

@app.route('/test_logs')
def test_logs():
    # Add a test log
    db.log_access("TEST123", "Test User", "GRANTED")
    logs = db.get_recent_logs(10)
    return jsonify({"logs": logs})

@app.route('/api/status')
def api_status():
    try:
        status = db.get_system_status()
        return jsonify({
            "door_state": status[0] if status else "UNKNOWN",
            "last_activity": str(status[1]) if status else "",
            "timestamp": str(status[1]) if status else ""
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🧪 Testing Flask App...")
    print("🌐 Open: http://localhost:5000")
    app.run(debug=True)