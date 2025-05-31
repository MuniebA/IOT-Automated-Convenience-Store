from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from database import DatabaseManager
from config import Config
import json
from datetime import datetime, timedelta

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
        
        # Calculate statistics
        now = datetime.now()
        today_logs = [log for log in recent_logs if log[3].date() == now.date()]
        this_week_logs = [log for log in recent_logs if log[3] >= now - timedelta(days=7)]
        
        granted_today = len([log for log in today_logs if log[2] == 'GRANTED'])
        denied_today = len([log for log in today_logs if log[2] == 'DENIED'])
        total_access_week = len([log for log in this_week_logs if log[2] == 'GRANTED'])
        
        # Get recent activity for dashboard
        recent_activity = []
        for log in recent_logs[:5]:
            activity = {
                'time': log[3].strftime('%H:%M'),
                'user': log[1] if log[1] else 'Unknown',
                'action': log[2],
                'status': 'success' if log[2] == 'GRANTED' else 'danger'
            }
            recent_activity.append(activity)
        
        dashboard_data = {
            'system_status': status,
            'total_users': total_users,
            'granted_today': granted_today,
            'denied_today': denied_today,
            'total_access_week': total_access_week,
            'recent_activity': recent_activity,
            'door_state': status[0] if status else 'UNKNOWN',
            'last_activity': status[1] if status else None,
            'ir_threshold': status[2] if status else 300
        }
        
        return render_template('index.html', **dashboard_data)
        
    except Exception as e:
        flash(f"Dashboard error: {e}", 'error')
        return render_template('index.html', 
                             system_status=None, 
                             total_users=0, 
                             granted_today=0, 
                             denied_today=0,
                             total_access_week=0,
                             recent_activity=[],
                             door_state='ERROR',
                             last_activity=None,
                             ir_threshold=300)

@app.route('/users')
def users():
    """User management page"""
    try:
        all_users = db.get_all_users()
        user_list = []
        
        for user in all_users:
            # Get recent access for each user
            recent_logs = db.get_recent_logs(50)
            user_logs = [log for log in recent_logs if log[0] == user[0]]
            last_access = user_logs[0][3] if user_logs else None
            access_count = len([log for log in user_logs if log[2] == 'GRANTED'])
            
            user_data = {
                'uid': user[0],
                'name': user[1],
                'created_at': user[2],
                'last_access': last_access,
                'access_count': access_count
            }
            user_list.append(user_data)
        
        return render_template('users.html', users=user_list)
        
    except Exception as e:
        flash(f"Error loading users: {e}", 'error')
        return render_template('users.html', users=[])

@app.route('/logs')
def logs():
    """Access logs page with filtering"""
    try:
        # Get filter parameters
        filter_type = request.args.get('filter', 'all')
        limit = int(request.args.get('limit', 100))
        
        all_logs = db.get_recent_logs(limit)
        
        # Apply filters
        if filter_type == 'granted':
            filtered_logs = [log for log in all_logs if log[2] == 'GRANTED']
        elif filter_type == 'denied':
            filtered_logs = [log for log in all_logs if log[2] == 'DENIED']
        elif filter_type == 'today':
            today = datetime.now().date()
            filtered_logs = [log for log in all_logs if log[3].date() == today]
        else:
            filtered_logs = all_logs
        
        # Prepare logs for display
        log_data = []
        for log in filtered_logs:
            log_entry = {
                'uid': log[0] if log[0] else 'N/A',
                'name': log[1] if log[1] else 'Unknown',
                'result': log[2],
                'timestamp': log[3],
                'status_class': 'success' if log[2] == 'GRANTED' else 'danger' if log[2] == 'DENIED' else 'warning'
            }
            log_data.append(log_entry)
        
        return render_template('logs.html', 
                             logs=log_data, 
                             current_filter=filter_type,
                             total_logs=len(all_logs),
                             filtered_count=len(filtered_logs))
        
    except Exception as e:
        flash(f"Error loading logs: {e}", 'error')
        return render_template('logs.html', logs=[], current_filter='all', total_logs=0, filtered_count=0)

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add new user"""
    uid = request.form.get('uid', '').strip().upper()
    name = request.form.get('name', '').strip()
    
    if not uid or not name:
        flash("Please provide both UID and name.", 'error')
        return redirect(url_for('users'))
    
    # Validate UID format (should be hex)
    if not all(c in '0123456789ABCDEF' for c in uid):
        flash("UID should contain only hexadecimal characters (0-9, A-F).", 'error')
        return redirect(url_for('users'))
    
    try:
        # Add user to database
        if db.add_user(uid, name):
            # Send command to Arduino to prepare for registration
            if db.add_command(f"ADD_USER:{uid}:{name}"):
                flash(f"User {name} added successfully! Arduino is ready for card registration. Please scan the RFID card now.", 'success')
            else:
                flash(f"User {name} added to database, but failed to send command to Arduino.", 'warning')
        else:
            flash("Error adding user to database. UID might already exist.", 'error')
    except Exception as e:
        flash(f"Error adding user: {e}", 'error')
    
    return redirect(url_for('users'))

@app.route('/delete_user/<uid>', methods=['POST'])
def delete_user(uid):
    """Delete user"""
    try:
        if db.delete_user(uid):
            flash("User deleted successfully!", 'success')
        else:
            flash("Error deleting user.", 'error')
    except Exception as e:
        flash(f"Error deleting user: {e}", 'error')
    
    return redirect(url_for('users'))

@app.route('/manual_open', methods=['POST'])
def manual_open():
    """Manual door open command"""
    try:
        if db.add_command("OPEN_DOOR"):
            return jsonify({"status": "success", "message": "Door open command sent to Arduino"})
        else:
            return jsonify({"status": "error", "message": "Failed to send command to Arduino"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/set_mode', methods=['POST'])
def set_mode():
    """Set Arduino mode"""
    mode = request.form.get('mode')
    
    try:
        if mode == 'register':
            if db.add_command("REGISTER_MODE"):
                flash("Arduino set to registration mode. Scan a new card to register it.", 'success')
            else:
                flash("Failed to set registration mode.", 'error')
        elif mode == 'monitor':
            if db.add_command("MONITOR_MODE"):
                flash("Arduino set to monitor mode. Ready for normal operation.", 'success')
            else:
                flash("Failed to set monitor mode.", 'error')
        else:
            flash("Invalid mode selected.", 'error')
    except Exception as e:
        flash(f"Error setting mode: {e}", 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/calibrate_ir', methods=['POST'])
def calibrate_ir():
    """Calibrate IR sensor"""
    try:
        if db.add_command("CALIBRATE_IR"):
            return jsonify({"status": "success", "message": "IR calibration command sent to Arduino"})
        else:
            return jsonify({"status": "error", "message": "Failed to send calibration command"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_status', methods=['POST'])
def get_status():
    """Request status update from Arduino"""
    try:
        if db.add_command("GET_STATUS"):
            return jsonify({"status": "success", "message": "Status request sent to Arduino"})
        else:
            return jsonify({"status": "error", "message": "Failed to send status request"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# API Routes for real-time updates
@app.route('/api/status')
def api_status():
    """API endpoint for real-time status updates"""
    try:
        status = db.get_system_status()
        recent_logs = db.get_recent_logs(5)
        
        # Format logs for JSON
        formatted_logs = []
        for log in recent_logs:
            formatted_logs.append({
                'uid': log[0] if log[0] else 'N/A',
                'name': log[1] if log[1] else 'Unknown',
                'result': log[2],
                'timestamp': log[3].strftime('%H:%M:%S') if log[3] else 'Unknown'
            })
        
        return jsonify({
            "door_state": status[0] if status else "UNKNOWN",
            "last_activity": str(status[1]) if status and status[1] else "",
            "ir_threshold": status[2] if status else 300,
            "recent_logs": formatted_logs,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        recent_logs = db.get_recent_logs(100)
        all_users = db.get_all_users()
        
        now = datetime.now()
        today_logs = [log for log in recent_logs if log[3].date() == now.date()]
        
        stats = {
            "total_users": len(all_users),
            "access_granted_today": len([log for log in today_logs if log[2] == 'GRANTED']),
            "access_denied_today": len([log for log in today_logs if log[2] == 'DENIED']),
            "total_logs": len(recent_logs)
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("🏪 Smart Convenience Store - Main Web Interface")
    print("=" * 55)
    print(f"🌐 Server starting on http://localhost:{Config.PORT}")
    print("📊 phpMyAdmin: http://localhost/phpmyadmin")
    print("🔌 Make sure Arduino is connected to COM4")
    print("📡 Make sure serial_handler.py is running")
    print("=" * 55)
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)