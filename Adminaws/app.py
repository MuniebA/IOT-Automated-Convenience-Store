from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from config import Config
from utils.mock_data import (
    get_mock_customers,
    get_mock_analytics,
    get_mock_stores,
    get_mock_recent_transactions
)
import random
import string

app = Flask(__name__)
app.config.from_object(Config)

# Mock RFID cards storage
mock_rfid_cards = []


@app.route('/')
def dashboard():
    try:
        analytics = get_mock_analytics()
        recent_transactions = get_mock_recent_transactions()
        return render_template('dashboard.html',
                               analytics=analytics,
                               recent_transactions=recent_transactions)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/users')
def users():
    try:
        customers = get_mock_customers()
        return render_template('users.html', customers=customers)
    except Exception as e:
        return f"Error loading users: {str(e)}", 500


@app.route('/analytics')
def analytics():
    try:
        analytics_data = get_mock_analytics()
        return render_template('analytics.html', analytics=analytics_data)
    except Exception as e:
        return f"Error loading analytics: {str(e)}", 500


@app.route('/stores')
def stores():
    try:
        stores_data = get_mock_stores()
        return render_template('stores.html', stores=stores_data)
    except Exception as e:
        return f"Error loading stores: {str(e)}", 500


@app.route('/register-card')
def register_card():
    try:
        return render_template('register_card.html')
    except Exception as e:
        return f"Error loading register card: {str(e)}", 500


@app.route('/api/register-card', methods=['POST'])
def api_register_card():
    try:
        data = request.get_json()

        # Generate mock RFID UID
        rfid_uid = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=10))

        # Create new customer record
        new_customer = {
            'customer_id': f"cust_{len(mock_rfid_cards) + 1:03d}",
            'customer_name': data['name'],
            'customer_type': data['type'],
            'rfid_card_uid': rfid_uid,
            'email': data['email'],
            'phone': data.get('phone', ''),
            'total_spent': 0.0,
            'total_visits': 0,
            'membership_status': 'ACTIVE',
            'created_at': '2024-05-31T15:30:00Z'
        }

        mock_rfid_cards.append(new_customer)

        return jsonify({
            'success': True,
            'message': 'Card registered successfully!',
            'customer': new_customer
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/simulate-rfid-scan')
def simulate_rfid_scan():
    try:
        rfid_uid = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=10))

        return jsonify({
            'rfid_uid': rfid_uid,
            'scan_time': '2024-05-31T15:30:00Z'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("🚀 Starting IoT Store Admin UI...")
    print("📍 Access at: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
