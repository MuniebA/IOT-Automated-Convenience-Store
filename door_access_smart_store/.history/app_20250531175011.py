from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from database import DatabaseManager
from config import Config
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
db = DatabaseManager()

@app.route('/')
def dashboard():
    """Main dashboard showing system overview"""
    try:
        # Get system status
        status = db.get_system_status()
        recent_logs = db.get_recent_logs(10)
        all_users = db.get_all_users()
        total_users = len(all_users)
        
        # Calculate some stats
        today_logs = [log for log in recent_logs if log[3].date() == datetime.now().date()]
        granted_today = len([log for log in today_logs if log[2] == 'GRANTED'])
        denied_today = len([log for log in today_logs if log[2] == 'DENIED'])
        
        return render_template('index.html', 
                             status=status, 
                             recent_logs=recent_logs,
                             total_users=total_users,
                             granted_today=granted_today,
                             denied_today=denied_today)
    except Exception as e:
        flash(f"Dashboard error: {e}", 'error')
        return render_template('index.html', status=None, recent_logs=[], total_users=0)

@app.route('/users')
def users():
    """User management page"""
    try:
        all_users = db.get_all_users()
        return render_template('users.html', users=all_users)
    except Exception as e:
        flash(f"Error loading users: {e}", 'error')
        return render_template('users.html', users=[])

@app.route('/logs')
def logs():
    """Access logs page"""
    try:
        all_logs = db.get_recent_logs(100)
        return render_template('logs.html', logs=all_logs)
    except Exception as e:
        flash(f"Error loading logs: {e}", 'error')
        return render_template('logs.html', logs=[])

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add new user"""
    uid = request.form.get('uid', '').strip().upper()
    name = request.form.get('name', '').strip()
    
    if uid and name:
        if db.add_user(uid, name):
            # Send command to Arduino to prepare for registration
            db.add_command(f"ADD_USER:{uid}:{name}")
            flash(f"User {name} added successfully! Arduino is ready for card registration.", 'success')
        else:
            flash("Error adding user to database.", 'error')
    else:
        flash("Please provide both UID and name.", 'error')
    
    return redirect(url_for('users'))

@app.route('/delete_user/<uid>', methods=['POST'])
def delete_user(uid):
    """Delete user"""
    if db.delete_user(uid):
        flash("User deleted successfully!", 'success')
    else:
        flash("Error deleting user.", 'error')
    return redirect(url_for('users'))

@app.route('/open_door', methods=['POST'])
def open_door():
    """Manual door open command"""
    if db.add_command("OPEN_DOOR"):
        return jsonify({"status": "success", "message": "Door open command sent to Arduino"})
    else:
        return jsonify({"status": "error", "message": "Failed to send command"})

@app.route('/set_mode', methods=['POST'])
def set_mode():
    """Set Arduino mode"""
    mode = request.form.get('mode')
    if mode == 'register':
        if db.add_command("REGISTER_MODE"):
            flash("Arduino set to registration mode", 'success')
        else:
            flash("Failed to set registration mode", 'error')
    elif mode == 'monitor':
        if db.add_command("MONITOR_MODE"):
            flash("Arduino set to monitor mode", 'success')
        else:
            flash("Failed to set monitor mode", 'error')
    return redirect(url_for('dashboard'))

@app.route('/calibrate_ir', methods=['POST'])
def calibrate_ir():
    """Calibrate IR sensor"""
    if db.add_command("CALIBRATE_IR"):
        return jsonify({"status": "success", "message": "IR calibration command sent to Arduino"})
    else:
        return jsonify({"status": "error", "message": "Failed to send calibration command"})

@app.route('/api/status')
def api_status():
    """API endpoint for real-time status updates"""
    try:
        status = db.get_system_status()
        recent_logs = db.get_recent_logs(5)
        
        return jsonify({
            "door_state": status[0] if status else "UNKNOWN",
            "last_activity": str(status[1]) if status else "",
            "ir_threshold": status[2] if status else 300,
            "recent_logs": [[str(item) for item in log] for log in recent_logs]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test_db')
def test_db():
    """Test database connection"""
    try:
        status = db.get_system_status()
        if status:
            return jsonify({"status": "success", "message": "Database connected", "door_state": status[0]})
        else:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("🏪 Smart Convenience Store - Web Interface")
    print("=" * 50)
    print(f"🌐 Server starting on http://localhost:{Config.PORT}")
    print("📊 phpMyAdmin: http://localhost/phpmyadmin")
    print("🔌 Make sure Arduino is connected to COM4")
    print("📡 Run serial_handler.py in another terminal")
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)