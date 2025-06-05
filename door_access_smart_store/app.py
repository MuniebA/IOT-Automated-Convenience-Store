from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from database import DatabaseManager
from config import Config
import json
import requests
import threading 
import time
from datetime import datetime, timedelta
from door_mqtt_client import start_mqtt_client_background

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
db = DatabaseManager()

mqtt_client = None
mqtt_client_instance = None
mqtt_client_thread = None

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

@app.route('/test_mqtt', methods=['GET', 'POST'])
def test_mqtt():
    """Test MQTT connectivity and message publishing"""
    if request.method == 'GET':
        return '''
        <h2>🧪 MQTT Test Interface</h2>
        <form method="post">
            <h3>Test Entry Request</h3>
            <label>RFID UID:</label>
            <input type="text" name="rfid_uid" value="ABC123456789" placeholder="Enter RFID UID">
            <br><br>
            <label>Test Type:</label>
            <select name="test_type">
                <option value="entry">Entry Request</option>
                <option value="exit">Exit Request</option>
                <option value="status">Status Update</option>
            </select>
            <br><br>
            <button type="submit">🚀 Send MQTT Test Message</button>
        </form>
        <hr>
        <h3>📊 Monitor These Topics in AWS IoT Console:</h3>
        <ul>
            <li><code>store/door/001/status</code> - Status updates</li>
            <li><code>store/door/001/rfid/scan</code> - RFID scans</li>
            <li><code>store/door/001/entry</code> - Entry events</li>
            <li><code>store/door/001/exit/request</code> - Exit requests</li>
            <li><code>store/customers/valid</code> - Lambda responses</li>
        </ul>
        '''
    
    # Process test request
    from door_mqtt_client import get_mqtt_client
    
    rfid_uid = request.form.get('rfid_uid', 'ABC123456789')
    test_type = request.form.get('test_type', 'entry')
    
    try:
        # Get MQTT client instance
        mqtt_client = get_mqtt_client()
        
        if not mqtt_client.connected:
            return f"❌ MQTT client not connected. Start door_mqtt_client.py first."
        
        result_message = ""
        
        if test_type == 'entry':
            # Test entry request
            success = mqtt_client.process_entry_request(rfid_uid)
            result_message = f"📤 Entry request sent for {rfid_uid}" if success else "❌ Failed to send entry request"
            
        elif test_type == 'exit':
            # Test exit request  
            success = mqtt_client.process_exit_request(rfid_uid)
            result_message = f"📤 Exit request sent for {rfid_uid}" if success else "❌ Failed to send exit request"
            
        elif test_type == 'status':
            # Test status update
            success = mqtt_client.publish_door_status("TEST", f"Manual test triggered for {rfid_uid}")
            result_message = f"📤 Status update sent" if success else "❌ Failed to send status update"
        
        return f'''
        <h2>✅ MQTT Test Result</h2>
        <p><strong>{result_message}</strong></p>
        <p>🔍 Check AWS IoT Console MQTT Test Client for the message!</p>
        <br>
        <a href="/test_mqtt">🔄 Run Another Test</a>
        '''
        
    except Exception as e:
        return f'''
        <h2>❌ MQTT Test Error</h2>
        <p><strong>Error: {str(e)}</strong></p>
        <p>Make sure door_mqtt_client.py is running in background.</p>
        <br>
        <a href="/test_mqtt">🔄 Try Again</a>
        '''

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

@app.route('/process_rfid_scan', methods=['POST'])
def process_rfid_scan():
    """
    SIMPLIFIED: Process RFID scan using name from Arduino
    """
    try:
        data = request.get_json()
        rfid_uid = data.get('rfid_uid') if data else request.form.get('rfid_uid')
        user_name = data.get('user_name', 'Unknown') if data else request.form.get('user_name', 'Unknown')
        
        print(f"🔍 Processing RFID: {rfid_uid} for user: {user_name}")
        
        if not rfid_uid:
            return jsonify({'error': 'No RFID UID provided'}), 400
        
        # Check if it's an unknown card
        if user_name == "UNKNOWN":
            print(f"❌ Unknown RFID card: {rfid_uid}")
            db.log_access(rfid_uid, "Unknown", "DENIED")
            return jsonify({
                'status': 'denied',
                'message': 'Unknown RFID card',
                'action': 'none'
            })
        
        # Create user_info tuple for compatibility
        user_info = (rfid_uid, user_name)
        
        # Determine entry vs exit
        session_status = determine_entry_or_exit(rfid_uid, user_info)
        
        # Process based on determination
        if session_status['action'] == 'entry':
            result = process_entry_request(rfid_uid, user_info)
        elif session_status['action'] == 'exit':
            result = process_exit_request(rfid_uid, user_info)
        else:
            result = {
                'status': 'error',
                'message': 'Could not determine entry or exit intent',
                'action': 'none'
            }
        
        print(f"📋 Result: {result['status']} - {result['message']}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error processing RFID scan: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Processing error: {str(e)}',
            'action': 'none'
        }), 500

def determine_entry_or_exit(rfid_uid, user_info):
    """
    STEP 1 LOGIC: Determine if this is entry or exit based on time
    - No recent activity = Entry
    - Recent activity = Exit attempt
    """
    try:
        # Check recent access logs to determine context
        recent_logs = db.get_recent_logs(10)
        user_recent_logs = [log for log in recent_logs if log[0] == rfid_uid]
        
        if not user_recent_logs:
            # No recent activity = Entry attempt
            return {
                'action': 'entry',
                'reason': 'No recent activity - entry attempt'
            }
        
        # Check last access within reasonable time window (e.g., 4 hours)
        last_log = user_recent_logs[0]
        last_access_time = last_log[3]  # timestamp
        time_diff = datetime.now() - last_access_time
        
        # If last access was entry and within 4 hours = Exit attempt
        if time_diff.total_seconds() < 14400:  # 4 hours
            if last_log[2] in ['GRANTED', 'ENTRY_GRANTED']:
                return {
                    'action': 'exit',
                    'reason': 'Recent entry detected - exit attempt'
                }
        
        # Default to entry for new session
        return {
            'action': 'entry',
            'reason': 'New session - entry attempt'
        }
        
    except Exception as e:
        print(f"⚠️ Error determining entry/exit: {e}")
        # Default to entry on error
        return {
            'action': 'entry',
            'reason': 'Default to entry due to error'
        }

def process_entry_request(rfid_uid, user_info):
    """Process entry request - SUPER SHORT DATABASE VALUES"""
    try:
        user_name = user_info[1] if len(user_info) > 1 else "Unknown"
        
        print(f"🚪 Processing ENTRY request for: {user_name}")
        
        # Try fresh MQTT client first
        try:
            print("📡 Creating fresh MQTT connection...")
            from door_mqtt_client import SmartDoorMQTTClient
            
            # Use unique client ID to avoid conflicts
            client = SmartDoorMQTTClient()
            client.client_id = f"door-flask-{int(time.time())}"  # Unique ID
            
            if client.connect():
                print(f"✅ Fresh MQTT connected, publishing...")
                success = client.process_entry_request(rfid_uid)
                
                if success:
                    print(f"✅ MQTT publish successful for {user_name}")
                    client.disconnect()
                    
                    # Log with very short value
                    db.log_access(rfid_uid, user_name, "CLOUD")  # Super short
                    
                    return {
                        'status': 'processing',
                        'message': f'Processing entry for {user_name} via cloud',
                        'action': 'entry',
                        'user_name': user_name,
                        'rfid_uid': rfid_uid,
                        'cloud_processing': True
                    }
                else:
                    client.disconnect()
            else:
                print(f"❌ Fresh MQTT failed to connect")
                
        except Exception as mqtt_error:
            print(f"❌ MQTT error: {mqtt_error}")
        
        # Fallback to local processing
        print(f"🔄 Processing locally for {user_name}")
        db.log_access(rfid_uid, user_name, "LOCAL")  # Super short
        return {
            'status': 'granted',
            'message': f'Local entry granted for {user_name}',
            'action': 'entry',
            'user_name': user_name,
            'rfid_uid': rfid_uid,
            'cloud_processing': False,
            'assigned_cart': 'cart-001'
        }
        
    except Exception as e:
        print(f"❌ Error processing entry: {e}")
        db.log_access(rfid_uid, user_name, "ERROR")  # Super short
        return {
            'status': 'error',
            'message': f'Entry processing error: {str(e)}',
            'action': 'entry'
        }

def process_exit_request(rfid_uid, user_info):
    """Process exit request - NOW CONNECTS TO MQTT"""
    try:
        user_name = user_info[1] if len(user_info) > 1 else "Unknown"
        
        print(f"🚪 Processing EXIT request for: {user_name}")
        
        # Log locally first
        db.log_access(rfid_uid, user_name, "EXIT_PROCESSING")
        
        # STEP 3: ADD MQTT CLIENT CALL
        try:
            from door_mqtt_client import get_mqtt_client
            mqtt_client = get_mqtt_client()
            
            if mqtt_client.connected:
                print(f"📡 Sending exit request to cloud via MQTT")
                success = mqtt_client.process_exit_request(rfid_uid)
                
                if success:
                    return {
                        'status': 'processing',
                        'message': f'Processing exit for {user_name} via cloud',
                        'action': 'exit',
                        'user_name': user_name,
                        'rfid_uid': rfid_uid,
                        'cloud_processing': True
                    }
                else:
                    print(f"❌ MQTT publish failed, falling back to local")
            else:
                print(f"⚠️ MQTT client not connected, processing locally")
                
        except Exception as mqtt_error:
            print(f"❌ MQTT client error: {mqtt_error}")
        
        # Fallback to local processing (allow exit)
        db.log_access(rfid_uid, user_name, "EXIT_GRANTED")
        return {
            'status': 'granted',
            'message': f'Local exit granted for {user_name}',
            'action': 'exit',
            'user_name': user_name,
            'rfid_uid': rfid_uid,
            'cloud_processing': False
        }
        
    except Exception as e:
        print(f"❌ Error processing exit: {e}")
        return {
            'status': 'error',
            'message': f'Exit processing error: {str(e)}',
            'action': 'exit'
        }

@app.route('/test_card_scan', methods=['GET', 'POST'])
def test_card_scan():
    """Test route to simulate CARD_SCANNED message"""
    if request.method == 'GET':
        return '''
        <h2>🧪 Test Card Scan Simulation</h2>
        <form method="post">
            <label>RFID UID:</label>
            <input type="text" name="rfid_uid" value="A4F55A07" placeholder="Enter RFID UID">
            <br><br>
            <button type="submit">🚀 Simulate Card Scan</button>
        </form>
        '''
    
    # Process test card scan
    rfid_uid = request.form.get('rfid_uid', 'A4F55A07')
    
    print(f"🧪 TEST: Simulating card scan for {rfid_uid}")
    
    # Call the same function that serial handler would call
    try:
        response = requests.post(
            "http://localhost:5000/process_rfid_scan",
            json={'rfid_uid': rfid_uid},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return f'''
            <h2>✅ Test Result</h2>
            <pre>{json.dumps(result, indent=2)}</pre>
            <br>
            <a href="/test_card_scan">🔄 Test Again</a>
            '''
        else:
            return f'''
            <h2>❌ Test Failed</h2>
            <p>Status: {response.status_code}</p>
            <p>Response: {response.text}</p>
            <a href="/test_card_scan">🔄 Try Again</a>
            '''
            
    except Exception as e:
        return f'''
        <h2>❌ Test Error</h2>
        <p>Error: {str(e)}</p>
        <a href="/test_card_scan">🔄 Try Again</a>
        '''

# Test endpoint for manual testing
@app.route('/test_rfid', methods=['GET', 'POST'])
def test_rfid():
    """Test endpoint for RFID processing"""
    if request.method == 'GET':
        return '''
        <form method="post">
            <label>RFID UID:</label>
            <input type="text" name="rfid_uid" placeholder="Enter RFID UID">
            <button type="submit">Test RFID Scan</button>
        </form>
        '''
    
    # Process test RFID
    rfid_uid = request.form.get('rfid_uid')
    if rfid_uid:
        # Call our new endpoint
        return process_rfid_scan()
    else:
        return "No RFID UID provided"

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

def initialize_mqtt_client():
    """Initialize MQTT client in background - FIXED VERSION"""
    global mqtt_client_instance, mqtt_client_thread
    
    try:
        print("🚀 Starting MQTT client in background...")
        
        # Import and create client
        from door_mqtt_client import SmartDoorMQTTClient
        mqtt_client_instance = SmartDoorMQTTClient()
        
        # Start client in background thread
        def run_mqtt_client():
            try:
                if mqtt_client_instance.connect():
                    print("✅ MQTT client connected in background")
                    # Keep the client running
                    while mqtt_client_instance.connected:
                        time.sleep(1)
                else:
                    print("❌ Failed to connect MQTT client")
            except Exception as e:
                print(f"❌ MQTT client thread error: {e}")
        
        mqtt_client_thread = threading.Thread(target=run_mqtt_client, daemon=True)
        mqtt_client_thread.start()
        
        # Wait for connection
        time.sleep(3)
        
        if mqtt_client_instance and mqtt_client_instance.connected:
            print("✅ MQTT client initialization completed")
            return True
        else:
            print("❌ MQTT client failed to connect")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start MQTT client: {e}")
        return False

@app.route('/test_mqtt_connection')
def test_mqtt_connection():
    """Test MQTT connection directly"""
    try:
        print("🧪 Testing MQTT connection...")
        
        # Test fresh client approach
        from door_mqtt_client import SmartDoorMQTTClient
        
        client = SmartDoorMQTTClient()
        
        html = "<h2>🧪 MQTT Connection Test</h2>"
        
        # Try to connect
        if client.connect():
            html += "<p>✅ MQTT client connected successfully</p>"
            
            # Try to publish a test message
            test_success = client.process_entry_request("TEST123456")
            
            if test_success:
                html += "<p>✅ Test message published successfully</p>"
                html += "<p>📊 Check AWS IoT MQTT test client for the message</p>"
            else:
                html += "<p>❌ Test message failed to publish</p>"
            
            # Disconnect
            client.disconnect()
            html += "<p>📡 Disconnected from MQTT</p>"
            
        else:
            html += "<p>❌ MQTT client failed to connect</p>"
            html += "<p>🔍 Check certificates and network connectivity</p>"
        
        html += '<br><a href="/">← Back to Dashboard</a>'
        
        return html
        
    except Exception as e:
        return f"<h2>❌ MQTT Test Error</h2><p>{str(e)}</p><a href='/'>← Back</a>"

def get_flask_mqtt_client():
    """Get the Flask-managed MQTT client instance with debugging"""
    global mqtt_client_instance
    
    print(f"🔍 MQTT Debug: Checking client instance...")
    print(f"   Instance exists: {mqtt_client_instance is not None}")
    
    if mqtt_client_instance:
        print(f"   Connected: {mqtt_client_instance.connected}")
        print(f"   MQTT object: {mqtt_client_instance.mqtt_client}")
        
        # If not connected, try to reconnect
        if not mqtt_client_instance.connected:
            print(f"🔄 MQTT client disconnected, attempting reconnection...")
            try:
                success = mqtt_client_instance.connect()
                print(f"   Reconnection result: {success}")
                if success:
                    # Wait a moment for connection to stabilize
                    import time
                    time.sleep(2)
            except Exception as e:
                print(f"   Reconnection error: {e}")
    
    return mqtt_client_instance

# Modify the main block
if __name__ == '__main__':
    print("🏪 Smart Convenience Store - Main Web Interface")
    print("=" * 55)
    print(f"🌐 Server starting on http://localhost:{Config.PORT}")
    print("📊 phpMyAdmin: http://localhost/phpmyadmin")
    print("🔌 Make sure Arduino is connected to COM4")
    print("📡 Make sure serial_handler.py is running")
    print("=" * 55)
    
    # IMPORTANT: Don't run standalone door_mqtt_client.py anymore
    print("⚠️  NOTE: Do NOT run door_mqtt_client.py separately!")
    print("🚀 Initializing integrated MQTT client...")
    
    # Start MQTT client in background
    #mqtt_success = initialize_mqtt_client()
    
    #if mqtt_success:
       # print("✅ MQTT integration ready")
    #else:
        #print("❌ MQTT integration failed - running in local mode only")
    
   # print("=" * 55)
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
