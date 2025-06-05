from flask import Flask, render_template, request, jsonify, redirect, url_for, session as flask_session
import mysql.connector
import json
from datetime import datetime
import time
import logging
import secrets
import boto3
import uuid
from dotenv import load_dotenv
import os
import traceback
import decimal
from decimal import Decimal
from mqtt_client import SmartCartMQTT

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

load_dotenv()
AWS_REGION = os.getenv('AWS_REGION')
ACCOUNT_ID = os.getenv('ACCOUNT_ID')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("flask_app.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# AWS Configuration
AWS_REGION = 'us-east-1'
ACCOUNT_ID = '378084046672'

# DynamoDB Table Names (from Terraform outputs)
DYNAMODB_TABLES = {
    'sessions': 'iot-convenience-store-sessions-production',
    'customers': 'iot-convenience-store-customers-production', 
    'transactions': 'iot-convenience-store-transactions-production',
    'fraud_events': 'iot-convenience-store-fraud-events-production',
    'products': 'iot-convenience-store-products-production',
    'discounts': 'iot-convenience-store-discount-effectiveness-production'
}
# Initialize DynamoDB client
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    # Table references
    sessions_table = dynamodb.Table(DYNAMODB_TABLES['sessions'])
    customers_table = dynamodb.Table(DYNAMODB_TABLES['customers'])
    transactions_table = dynamodb.Table(DYNAMODB_TABLES['transactions'])
    fraud_events_table = dynamodb.Table(DYNAMODB_TABLES['fraud_events'])
    products_table = dynamodb.Table(DYNAMODB_TABLES['products'])
    discounts_table = dynamodb.Table(DYNAMODB_TABLES['discounts'])
    # Test connection
    sessions_table.meta.client.describe_table(TableName=DYNAMODB_TABLES['sessions'])
    logging.info("✅ AWS DynamoDB connection successful")
except Exception as e:
    logging.error(f"❌ AWS DynamoDB connection failed: {str(e)}")
    # Continue without cloud features if AWS fails
    dynamodb = None

# Database configuration (Local MySQL backup)
DB_CONFIG = {
    'user': 'shifaz',
    'password': 'Shifaz1122@',
    'host': 'localhost',
    'database': 'automated_shopping_cart'
}

class CloudSessionManager:
    def __init__(self):
        self.current_session = None
    
    def create_cloud_session(self, customer_name, customer_address=None):
        """Create a new session in AWS DynamoDB"""
        if not dynamodb:
            logging.warning("AWS DynamoDB not available, skipping cloud session creation")
            return None
        
        # Generate unique IDs
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        customer_id = f"cust_{uuid.uuid4().hex[:8]}"
        
        try:
            # Check if customer exists in DynamoDB
            try:
                response = customers_table.get_item(
                    Key={'customer_id': customer_id}
                )
                if 'Item' not in response:
                    # Create new customer in DynamoDB
                    customer_data = {
                        'customer_id': customer_id,
                        'name': customer_name,
                        'address': customer_address or '',
                        'created_at': datetime.now().isoformat(),
                        'last_visit': datetime.now().isoformat(),
                        'total_sessions': 1,
                        'total_spent': 0,
                        'total_fraud_incidents': 0
                    }
                    customers_table.put_item(Item=customer_data)
                else:
                    # Update existing customer
                    customers_table.update_item(
                        Key={'customer_id': customer_id},
                        UpdateExpression='SET last_visit = :visit, total_sessions = total_sessions + :inc',
                        ExpressionAttributeValues={
                            ':visit': datetime.now().isoformat(),
                            ':inc': 1
                        }
                    )
            except Exception as customer_err:
                logging.error(f"Error managing customer in DynamoDB: {customer_err}")
            
            # Create session in DynamoDB  
            session_data = {
                'session_id': session_id,
                'customer_id': customer_id,
                'customer_name': customer_name,
                'start_time': datetime.now().isoformat(),
                'session_status': 'active',
                'node_type': 'smart-cart',
                'node_id': 'cart-001',
                'total_amount': 0,
                'total_items': 0,
                'fraud_event_count': 0,
                'has_fraud_alerts': False
            }
            
            sessions_table.put_item(Item=session_data)
            
            self.current_session = {
                'session_id': session_id,
                'customer_id': customer_id,
                'customer_name': customer_name
            }
            
            logging.info(f"[SUCCESS] Cloud session created: {session_id} for customer: {customer_name}")
            return session_data
            
        except Exception as e:
            logging.error(f"[ERROR] Error creating cloud session: {str(e)}")
            return None
    
    def end_cloud_session(self, session_id, total_amount=0, item_count=0, items_data=None):
        """End session and trigger cloud processing"""
        if not dynamodb:
            logging.warning("AWS DynamoDB not available, skipping cloud session end")
            return False
            
        try:
            # Convert to Decimal for DynamoDB
            total_amount_decimal = Decimal(str(total_amount))
            
            # Update session in DynamoDB
            sessions_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET session_status = :status, end_time = :end_time, total_amount = :amount, total_items = :items',
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':end_time': datetime.now().isoformat(),
                    ':amount': total_amount_decimal,
                    ':items': item_count
                }
            )
            
            # Trigger Lambda function for session processing
            try:
                lambda_client = boto3.client('lambda', region_name=AWS_REGION)
                
                # FIXED: Send proper payload with customer_id and items data
                payload = {
                    'session_id': session_id,
                    'customer_id': self.current_session.get('customer_id') if self.current_session else None,
                    'trigger': 'session_end',
                    'timestamp': datetime.now().isoformat(),
                    'total_amount': float(total_amount_decimal),
                    'total_items': item_count,
                    # Add items data for active sessions update
                    'items': [],  # Will be filled below
                    'customer_name': self.current_session.get('customer_name') if self.current_session else None
                }
                
                # Get the actual items from the session for Lambda processing
                try:
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("""
                            SELECT s.id, s.tag_id, s.weight, p.product_name, p.price, p.is_grocery
                            FROM scanned_items s
                            JOIN product_data p ON s.product_id = p.id
                            WHERE s.is_validated = TRUE
                        """)
                        items = cursor.fetchall()
                        
                        # Format items for Lambda
                        payload['items'] = [
                            {
                                'id': item['id'],
                                'product_name': item['product_name'],
                                'price': float(item['price']),
                                'weight': float(item['weight']) if item['weight'] else None,
                                'is_grocery': item['is_grocery'],
                                'tag_id': item['tag_id']
                            }
                            for item in items
                        ]
                        
                        cursor.close()
                        conn.close()
                        
                        logging.info(f"Sending {len(payload['items'])} items to Lambda for session {session_id}")
                        
                except Exception as items_err:
                    logging.error(f"Error getting items for Lambda payload: {items_err}")
                    # Continue without items if there's an error
                
                # Invoke session processor Lambda
                lambda_client.invoke(
                    FunctionName='iot-convenience-store-session-processor-production',
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps(payload, cls=DecimalEncoder)
                )
                
                logging.info(f"[SUCCESS] Cloud session ended and Lambda triggered: {session_id}")
                logging.info(f"Lambda payload: customer_id={payload.get('customer_id')}, items_count={len(payload.get('items', []))}")
                
            except Exception as lambda_err:
                logging.error(f"[ERROR] Error triggering Lambda: {lambda_err}")
            
            return True
            
        except Exception as e:
            logging.error(f"[ERROR] Error ending cloud session: {str(e)}")
            return False
    
    def create_cloud_transaction(self, session_id, items_data, total_amount):
        """Create transaction record in cloud"""
        if not dynamodb:
            logging.warning("AWS DynamoDB not available, skipping cloud transaction creation")
            return None
            
        try:
            transaction_id = f"trans_{uuid.uuid4().hex[:8]}"
            
            # Convert to Decimal for DynamoDB
            total_amount_decimal = Decimal(str(total_amount))
            
            # Prepare items for cloud storage
            cloud_items = []
            for item in items_data:
                # Convert all numeric values to Decimal for DynamoDB
                price = Decimal(str(item['price']))
                weight = Decimal(str(item.get('weight', 0))) if item.get('weight') is not None else None
                
                cloud_items.append({
                    'product_id': str(item.get('id', 'unknown')),
                    'product_name': str(item['product_name']),
                    'price': price,
                    'weight': weight,
                    'is_grocery': bool(item.get('is_grocery', False)),
                    'tag_id': str(item.get('tag_id', 'unknown'))
                })
            
            transaction_data = {
                'transaction_id': transaction_id,
                'session_id': session_id,
                'customer_id': self.current_session.get('customer_id') if self.current_session else 'unknown',
                'timestamp': datetime.now().isoformat(),
                'amount': total_amount_decimal,
                'item_count': len(items_data),
                'items': cloud_items,
                'payment_method': 'card',
                'node_id': 'cart-001'
            }
            
            transactions_table.put_item(Item=transaction_data)
            
            logging.info(f"[SUCCESS] Cloud transaction created: {transaction_id} with {len(items_data)} items, total: ${total_amount_decimal}")
            return transaction_id
            
        except Exception as e:
            logging.error(f"[ERROR] Error creating cloud transaction: {str(e)}")
            logging.error(f"Transaction error traceback: {traceback.format_exc()}")
            return None
    
    def log_fraud_event(self, session_id, fraud_type, details):
        """Log fraud event to DynamoDB"""
        if not dynamodb:
            logging.warning("AWS DynamoDB not available, skipping cloud fraud logging")
            return False
            
        try:
            event_id = f"fraud_{uuid.uuid4().hex[:8]}"
            
            fraud_data = {
                'event_id': event_id,
                'session_id': session_id,
                'fraud_type': fraud_type,
                'details': details,
                'timestamp': datetime.now().isoformat(),
                'node_type': 'smart-cart',
                'severity': 'medium'
            }
            
            fraud_events_table.put_item(Item=fraud_data)
            
            # Update session fraud count
            sessions_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET fraud_event_count = fraud_event_count + :inc, has_fraud_alerts = :has_fraud',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':has_fraud': True
                }
            )
            
            logging.info(f"[FRAUD] Fraud event logged to cloud: {fraud_type} for session {session_id}")
            return True
            
        except Exception as e:
            logging.error(f"[ERROR] Error logging fraud event to cloud: {str(e)}")
            return False
            
     
def get_applicable_discounts(customer_id, item_names):
    """
    Simple discount check: Only cust_002 gets discount on Smartphone if they have 'shown' response
    Returns: dict mapping product_name -> discount_percentage
    """
    # Only check for cust_002
    if customer_id != "cust_002":
        logging.info(f"💰 No discounts: Customer {customer_id} is not cust_002")
        return {}
    
    # Only check for Smartphone
    if "Smartphone" not in item_names:
        logging.info(f"💰 No discounts: Smartphone not in cart items {item_names}")
        return {}
    
    if not dynamodb:
        logging.info("💰 No discounts: AWS not configured")
        return {}
    
    try:
        logging.info(f"💰 Checking discount for cust_002 with Smartphone...")
        
        # Query discounts for cust_002
        response = discounts_table.scan(
            FilterExpression='customer_id = :customer_id',
            ExpressionAttributeValues={':customer_id': 'cust_002'}
        )
        
        discounts = response.get('Items', [])
        logging.info(f"💰 Found {len(discounts)} discount records for cust_002")
        
        # Look for any discount with action_taken = 'shown'
        for discount in discounts:
            customer_response = discount.get('customer_response', {})
            action_taken = customer_response.get('action_taken', '')
            
            if action_taken == 'shown':
                discount_details = discount.get('discount_details', {})
                discount_percentage = discount_details.get('discount_percentage', 0)
                
                # Convert Decimal to float if needed
                if hasattr(discount_percentage, '__float__'):
                    discount_percentage = float(discount_percentage)
                
                logging.info(f"✅ Found 'shown' discount for cust_002: {discount_percentage}%")
                return {"Smartphone": discount_percentage}
        
        logging.info(f"💰 No 'shown' discounts found for cust_002")
        return {}
        
    except Exception as e:
        logging.error(f"💥 Error getting discounts: {e}")
        return {}
        
@app.route('/test_discount_direct')
def test_discount_direct():
    """Test discount lookup with hardcoded customer ID"""
    
    # Force the customer ID we know exists
    test_customer_id = "cust_002"
    test_items = ["Smartphone"]
    
    # Test discount lookup directly
    discounts = get_applicable_discounts(test_customer_id, test_items)
    
    return jsonify({
        'success': True,
        'test_customer_id': test_customer_id,
        'test_items': test_items,
        'found_discounts': discounts,
        'discount_table_available': dynamodb is not None
    })
        
@app.route('/debug_discount_table')
def debug_discount_table():
    """Debug what's in the discount table - SAFE VERSION"""
    if not dynamodb:
        return jsonify({'error': 'DynamoDB not available'})
    
    try:
        # Get all discount records (be careful in production!)
        response = discounts_table.scan()
        items = response.get('Items', [])
        
        # Check current cloud session state
        cloud_session_info = {
            'exists': cloud_session.current_session is not None,
            'current_session': cloud_session.current_session,
            'customer_id': cloud_session.current_session.get('customer_id') if cloud_session.current_session else None
        }
        
        debug_info = {
            'total_records': len(items),
            'cloud_session_info': cloud_session_info,
            'cust_002_discounts': [],
            'all_customer_ids': set()
        }
        
        # Process each item and specifically look for cust_002
        for i, item in enumerate(items):
            try:
                if isinstance(item, dict):
                    customer_id = item.get('customer_id')
                    debug_info['all_customer_ids'].add(customer_id)
                    
                    # Focus on cust_002 records
                    if customer_id == 'cust_002':
                        customer_response = item.get('customer_response', {})
                        discount_details = item.get('discount_details', {})
                        
                        action_taken = customer_response.get('action_taken', '')
                        product_id = discount_details.get('product_id', '')
                        discount_percentage = discount_details.get('discount_percentage', 0)
                        
                        debug_info['cust_002_discounts'].append({
                            'index': i,
                            'action_taken': action_taken,
                            'product_id': product_id,
                            'discount_percentage': float(discount_percentage) if hasattr(discount_percentage, '__float__') else discount_percentage,
                            'should_apply': action_taken not in ['ignored']
                        })
                        
            except Exception as item_error:
                continue
        
        debug_info['all_customer_ids'] = list(debug_info['all_customer_ids'])
        
        return jsonify(debug_info)
        
    except Exception as e:
        logging.error(f"Error debugging discount table: {e}")
        return jsonify({'error': str(e), 'error_type': type(e).__name__})

def recover_session_for_checkout():
    """
    Try to recover session information for checkout
    Returns: (local_customer_id, cloud_customer_id, session_recovered)
    """
    # First check if we have Flask session
    if flask_session.get('session_id'):
        cloud_customer_id = cloud_session.current_session.get('customer_id') if cloud_session.current_session else None
        return flask_session.get('customer_id'), cloud_customer_id, True
    
    # If Flask session is empty but cloud session exists, use that
    if cloud_session.current_session:
        cloud_customer_id = cloud_session.current_session.get('customer_id')
        cloud_session_id = cloud_session.current_session.get('session_id')
        customer_name = cloud_session.current_session.get('customer_name')
        
        logging.info(f"🔄 Using cloud session: customer_id={cloud_customer_id}, session_id={cloud_session_id}")
        
        # Find matching database session
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT id, customer_id, cloud_session_id 
                    FROM shopping_sessions 
                    WHERE cloud_session_id = %s AND status = 'active'
                    ORDER BY start_time DESC 
                    LIMIT 1
                """, (cloud_session_id,))
                session = cursor.fetchone()
                
                if session:
                    # Restore Flask session
                    flask_session['session_id'] = session['id']
                    flask_session['customer_id'] = session['customer_id'] 
                    flask_session['customer_name'] = customer_name
                    flask_session['cloud_session_id'] = cloud_session_id
                    
                    logging.info(f"✅ Session recovered: local_id={session['customer_id']}, cloud_id={cloud_customer_id}")
                    return session['customer_id'], cloud_customer_id, True
                    
            except Exception as e:
                logging.error(f"💥 Error recovering from cloud session: {e}")
            finally:
                cursor.close()
                conn.close()
    
    # Return what we have from cloud session
    if cloud_session.current_session:
        cloud_customer_id = cloud_session.current_session.get('customer_id')
        logging.info(f"⚠️ Using cloud customer ID without database recovery: {cloud_customer_id}")
        return None, cloud_customer_id, False
    
    return None, None, False

def get_db_connection():
    """Create and return a new database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        return None

def initialize_database():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    if not conn:
        logging.error("Failed to initialize database")
        return False
    
    cursor = conn.cursor()
    try:
        # Create customers table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_visit DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create shopping_sessions table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT,
                cloud_session_id VARCHAR(100),
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME NULL,
                total_amount DECIMAL(10, 2) DEFAULT 0.00,
                fraud_alerts INT DEFAULT 0,
                status ENUM('active', 'completed', 'abandoned') DEFAULT 'active',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        
        # Add session_id field to transactions table if it doesn't exist
        try:
            cursor.execute("""
                SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'transactions' 
                AND COLUMN_NAME = 'session_id'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE transactions 
                    ADD COLUMN session_id INT,
                    ADD FOREIGN KEY (session_id) REFERENCES shopping_sessions(id)
                """)
                logging.info("Added session_id to transactions table")
        except mysql.connector.Error as err:
            logging.error(f"Error checking/updating transactions table: {err}")
        
        # Add session_id field to fraud_logs table if it doesn't exist
        try:
            cursor.execute("""
                SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'fraud_logs' 
                AND COLUMN_NAME = 'session_id'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE fraud_logs
                    ADD COLUMN session_id INT,
                    ADD FOREIGN KEY (session_id) REFERENCES shopping_sessions(id)
                """)
                logging.info("Added session_id to fraud_logs table")
        except mysql.connector.Error as err:
            logging.error(f"Error checking/updating fraud_logs table: {err}")
        
        conn.commit()
        logging.info("Database initialized successfully")
        return True
    except mysql.connector.Error as err:
        logging.error(f"Database initialization error: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

# Initialize database on startup
initialize_database()

# Initialize the cloud session manager
cloud_session = CloudSessionManager()

@app.route('/debug_session_state')
def debug_session_state():
    """Debug current session state"""
    
    # Check all possible session sources
    session_info = {
        'flask_session': {
            'keys': list(flask_session.keys()),
            'session_id': flask_session.get('session_id'),
            'cloud_session_id': flask_session.get('cloud_session_id'),
            'customer_id': flask_session.get('customer_id'),
            'customer_name': flask_session.get('customer_name')
        },
        'cloud_session_manager': {
            'current_session': cloud_session.current_session,
            'has_session': cloud_session.current_session is not None
        }
    }
    
    # Check database for active sessions
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Get recent active sessions
            cursor.execute("""
                SELECT id, customer_id, cloud_session_id, start_time, status
                FROM shopping_sessions 
                WHERE status = 'active' 
                ORDER BY start_time DESC 
                LIMIT 5
            """)
            active_sessions = cursor.fetchall()
            
            # Get current cart items
            cursor.execute("""
                SELECT s.id, s.tag_id, p.product_name, p.price, s.is_validated
                FROM scanned_items s
                JOIN product_data p ON s.product_id = p.id
                ORDER BY s.timestamp DESC
                LIMIT 10
            """)
            cart_items = cursor.fetchall()
            
            session_info['database'] = {
                'active_sessions': active_sessions,
                'cart_items': cart_items
            }
            
        except Exception as e:
            session_info['database'] = {'error': str(e)}
        finally:
            cursor.close()
            conn.close()
    
    return jsonify(session_info)

@app.route('/test_discount_lookup')
def test_discount_lookup():
    """Test endpoint to check discount lookup functionality with session recovery"""
    
    # Try to recover session if needed
    local_customer_id, cloud_customer_id, session_recovered = recover_session_for_checkout()
    
    # Get current cart items (only validated ones for checkout)
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.product_name, p.price, s.id
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            WHERE s.is_validated = TRUE
            ORDER BY s.timestamp DESC
        """)
        validated_items = cursor.fetchall()
        item_names = [item['product_name'] for item in validated_items]
        
        # Test discount lookup with cloud customer ID
        discounts = get_applicable_discounts(cloud_customer_id, item_names)
        
        return jsonify({
            'success': True,
            'session_info': {
                'session_recovered': session_recovered,
                'local_customer_id': local_customer_id,
                'cloud_customer_id': cloud_customer_id,
                'flask_session_restored': flask_session.get('session_id') is not None
            },
            'cart_data': {
                'validated_items': validated_items,
                'item_names_for_discount': item_names
            },
            'discount_results': {
                'found_discounts': discounts,
                'discount_table_available': dynamodb is not None
            }
        })
        
    except Exception as e:
        logging.error(f"Error in discount test: {e}")
        return jsonify({'error': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/welcome')
def welcome():
    """Welcome page for the smart cart system."""
    return render_template('welcome.html')

@app.route('/')
def index():
    """Main shopping cart page."""
    # Check if there's an active session
    if 'session_id' not in flask_session:
        return redirect(url_for('welcome'))
    
    return render_template('index.html')

@app.route('/debug_active_sessions')
def debug_active_sessions():
    """Debug route to check active sessions table"""
    if not dynamodb:
        return jsonify({'error': 'AWS not configured'})
    
    try:
        # Get active sessions table
        active_sessions_table = dynamodb.Table('iot-convenience-store-active-sessions-production')
        
        response = active_sessions_table.scan()
        sessions = response.get('Items', [])
        
        return jsonify({
            'success': True,
            'table_name': 'iot-convenience-store-active-sessions-production',
            'sessions': sessions,
            'session_count': len(sessions)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/manual_checkout_update/<customer_id>')
def manual_checkout_update(customer_id):
    """Manually update checkout status for testing"""
    if not dynamodb:
        return jsonify({'error': 'AWS not configured'})
    
    try:
        active_sessions_table = dynamodb.Table('iot-convenience-store-active-sessions-production')
        
        # Get current session data
        response = active_sessions_table.get_item(Key={'customer_id': customer_id})
        
        if 'Item' not in response:
            return jsonify({'error': f'No session found for customer {customer_id}'})
        
        current_session = response['Item']
        
        # Update with checkout completion
        active_sessions_table.update_item(
            Key={'customer_id': customer_id},
            UpdateExpression='''
                SET checkout_completed = :completed,
                    checkout_time = :checkout_time,
                    last_activity = :timestamp,
                    total_amount = :amount,
                    #items = :items
            ''',
            ExpressionAttributeNames={
                '#items': 'items'
            },
            ExpressionAttributeValues={
                ':completed': True,
                ':checkout_time': datetime.now().isoformat(),
                ':timestamp': datetime.now().isoformat(),
                ':amount': Decimal('45.0'),  # Test amount
                ':items': [
                    {
                        'product_name': 'Test Item',
                        'price': Decimal('45.0'),
                        'quantity': 1
                    }
                ]
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Manually updated checkout for {customer_id}',
            'original_session': current_session
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/test_lambda_payload')
def test_lambda_payload():
    """Test what payload would be sent to Lambda"""
    if not cloud_session.current_session:
        return jsonify({'error': 'No current session'})
    
    try:
        session_id = cloud_session.current_session.get('session_id')
        
        # Build test payload like the real one
        payload = {
            'session_id': session_id,
            'customer_id': cloud_session.current_session.get('customer_id'),
            'customer_name': cloud_session.current_session.get('customer_name'),
            'trigger': 'session_end',
            'timestamp': datetime.now().isoformat(),
            'total_amount': 45.0,
            'total_items': 1,
            'items': []
        }
        
        # Get current items
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.id, s.tag_id, s.weight, p.product_name, p.price, p.is_grocery
                FROM scanned_items s
                JOIN product_data p ON s.product_id = p.id
                WHERE s.is_validated = TRUE
            """)
            items = cursor.fetchall()
            
            payload['items'] = [
                {
                    'id': item['id'],
                    'product_name': item['product_name'],
                    'price': float(item['price']),
                    'weight': float(item['weight']) if item['weight'] else None,
                    'is_grocery': item['is_grocery'],
                    'tag_id': item['tag_id']
                }
                for item in items
            ]
            
            cursor.close()
            conn.close()
        
        return jsonify({
            'success': True,
            'lambda_payload': payload,
            'current_session': cloud_session.current_session
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/create_session', methods=['POST'])
def create_session():
    """Create a new shopping session for a customer - ROBUST VERSION."""
    try:
        # Log the incoming request
        logging.info("=== CREATE SESSION REQUEST RECEIVED ===")
        logging.info(f"Form data: {dict(request.form)}")
        
        name = request.form.get('name')
        address = request.form.get('address')
        
        if not name:
            logging.error("Create session failed: Name is required")
            return jsonify({'error': 'Name is required'}), 400
        
        logging.info(f"Creating session for customer: {name}")
        
        # Test database connection first
        conn = get_db_connection()
        if not conn:
            logging.error("Create session failed: Database connection failed")
            return jsonify({'error': 'Local database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # STEP 1: Handle customer in local MySQL (CRITICAL - must work)
            logging.info("Step 1: Managing customer in local database")
            
            cursor.execute("SELECT id, name, address FROM customers WHERE name = %s", (name,))
            customer = cursor.fetchone()
            
            returning_customer = False
            
            if customer:
                # Update existing customer
                customer_id = customer['id']
                if address and address != customer['address']:
                    cursor.execute(
                        "UPDATE customers SET address = %s, last_visit = NOW() WHERE id = %s",
                        (address, customer_id)
                    )
                    logging.info(f"Updated address for existing customer {name}")
                else:
                    cursor.execute(
                        "UPDATE customers SET last_visit = NOW() WHERE id = %s",
                        (customer_id,)
                    )
                    logging.info(f"Updated last_visit for existing customer {name}")
                returning_customer = True
            else:
                # Create new customer
                cursor.execute(
                    "INSERT INTO customers (name, address) VALUES (%s, %s)",
                    (name, address)
                )
                customer_id = cursor.lastrowid
                logging.info(f"Created new customer {name} with ID {customer_id}")
            
            # STEP 2: Try cloud session (OPTIONAL - failure is acceptable)
            cloud_session_id = None
            cloud_success = False
            
            logging.info("Step 2: Attempting cloud session creation")
            
            try:
                # Check if AWS is configured
                if 'dynamodb' in globals() and dynamodb is not None:
                    logging.info("AWS DynamoDB is configured, attempting cloud session")
                    cloud_session_data = cloud_session.create_cloud_session(name, address)
                    
                    if cloud_session_data:
                        cloud_session_id = cloud_session_data.get('session_id')
                        if cloud_session_id:
                            logging.info(f"✅ Cloud session created successfully: {cloud_session_id}")
                            cloud_success = True
                        else:
                            logging.warning("⚠️ Cloud session creation returned no session ID")
                    else:
                        logging.warning("⚠️ Cloud session creation returned None")
                else:
                    logging.info("ℹ️ AWS DynamoDB not configured - running in local-only mode")
                    
            except Exception as cloud_err:
                logging.error(f"❌ Cloud session creation failed: {str(cloud_err)}")
                logging.error(f"Cloud error traceback: {traceback.format_exc()}")
                # Continue - this is not critical
            
            # STEP 3: Create local session (CRITICAL - must work)
            logging.info("Step 3: Creating local session")
            
            cursor.execute(
                "INSERT INTO shopping_sessions (customer_id, cloud_session_id, status) VALUES (%s, %s, 'active')",
                (customer_id, cloud_session_id)
            )
            local_session_id = cursor.lastrowid
            logging.info(f"Created local session with ID {local_session_id}")
            
            # STEP 4: Store in Flask session
            logging.info("Step 4: Storing session in Flask")
            
            flask_session['session_id'] = local_session_id
            flask_session['cloud_session_id'] = cloud_session_id
            flask_session['customer_id'] = customer_id
            flask_session['customer_name'] = name
            
            # STEP 5: Commit transaction
            conn.commit()
            logging.info("✅ All database operations committed successfully")
            
            # STEP 6: Return success response
            response_data = {
                'success': True,
                'session_id': local_session_id,
                'cloud_session_id': cloud_session_id,
                'customer_id': customer_id,
                'returning_customer': returning_customer,
                'customer_name': name,
                'cloud_enabled': cloud_success,
                'message': 'Session created successfully'
            }
            
            logging.info(f"✅ Session creation completed successfully: {response_data}")
            return jsonify(response_data)
            
        except mysql.connector.Error as db_err:
            logging.error(f"❌ MySQL database error: {str(db_err)}")
            logging.error(f"Database error traceback: {traceback.format_exc()}")
            conn.rollback()
            return jsonify({
                'error': f'Database error: {str(db_err)}',
                'details': 'Check MySQL connection and database structure'
            }), 500
            
        finally:
            cursor.close()
            conn.close()
            logging.info("Database connection closed")
            
    except Exception as e:
        logging.error(f"❌ CRITICAL ERROR in create_session: {str(e)}")
        logging.error(f"Full error traceback: {traceback.format_exc()}")
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'details': 'Check server logs for more information'
        }), 500

@app.route('/check_active_session')
def check_active_session():
    """Check AWS DynamoDB for active session assigned to this cart."""
    if not dynamodb:
        return jsonify({'has_active_session': False, 'error': 'AWS not configured'})
    
    try:
        cart_id = "cart-001"
        
        # Query active sessions table
        active_sessions_table = dynamodb.Table('iot-convenience-store-active-sessions-production')
        
        # Instead of filtering by assigned_cart, let's get all active sessions
        # and find ones that haven't completed checkout
        response = active_sessions_table.scan(
            FilterExpression='checkout_completed = :checkout_completed',
            ExpressionAttributeValues={':checkout_completed': False}
        )
        
        sessions = response.get('Items', [])
        
        if sessions:
            # Get the most recent session (or you could filter by cart assignment)
            active_session = sessions[0]
            
            return jsonify({
                'has_active_session': True,
                'session_data': {
                    'customer_id': active_session.get('customer_id'),
                    'customer_name': active_session.get('customer_name'),
                    'customer_address': active_session.get('customer_address', ''),
                    'assigned_cart': active_session.get('assigned_cart', cart_id),
                    'cloud_session_id': active_session.get('session_id'),
                    'entry_time': active_session.get('entry_time')
                }
            })
        else:
            return jsonify({'has_active_session': False})
            
    except Exception as e:
        logging.error(f"Error checking active session: {e}")
        return jsonify({
            'has_active_session': False, 
            'error': str(e)
        })

@app.route('/create_session_from_active', methods=['POST'])
def create_session_from_active():
    """Create a local session using active session data from AWS."""
    try:
        customer_name = request.form.get('customer_name')
        customer_address = request.form.get('customer_address', '')
        cloud_session_id = request.form.get('cloud_session_id')
        aws_customer_id = request.form.get('aws_customer_id')  # This is the important one!
        
        if not customer_name:
            return jsonify({'error': 'Customer name is required'}), 400
        
        logging.info(f"Creating session from active AWS session for: {customer_name}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Handle customer in local MySQL (same as before)
            cursor.execute("SELECT id, name, address FROM customers WHERE name = %s", (customer_name,))
            customer = cursor.fetchone()
            
            returning_customer = False
            
            if customer:
                customer_id = customer['id']
                if customer_address and customer_address != customer['address']:
                    cursor.execute(
                        "UPDATE customers SET address = %s, last_visit = NOW() WHERE id = %s",
                        (customer_address, customer_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE customers SET last_visit = NOW() WHERE id = %s",
                        (customer_id,)
                    )
                returning_customer = True
            else:
                cursor.execute(
                    "INSERT INTO customers (name, address) VALUES (%s, %s)",
                    (customer_name, customer_address)
                )
                customer_id = cursor.lastrowid
            
            # Create local session
            cursor.execute(
                "INSERT INTO shopping_sessions (customer_id, cloud_session_id, status) VALUES (%s, %s, 'active')",
                (customer_id, cloud_session_id)
            )
            local_session_id = cursor.lastrowid
            
            # Store in Flask session
            flask_session['session_id'] = local_session_id
            flask_session['cloud_session_id'] = cloud_session_id
            flask_session['customer_id'] = customer_id
            flask_session['customer_name'] = customer_name
            
            # IMPORTANT: Update cloud session manager with AWS customer_id
            if cloud_session_id:
                cloud_session.current_session = {
                    'session_id': cloud_session_id,
                    'customer_id': aws_customer_id,  # Use AWS customer_id, not local one!
                    'customer_name': customer_name
                }
            
            conn.commit()
            
            response_data = {
                'success': True,
                'session_id': local_session_id,
                'cloud_session_id': cloud_session_id,
                'customer_id': customer_id,
                'aws_customer_id': aws_customer_id,  # Add this for debugging
                'returning_customer': returning_customer,
                'customer_name': customer_name,
                'cloud_enabled': cloud_session_id is not None,
                'message': 'Session created from door access',
                'session_source': 'door_access'
            }
            
            logging.info(f"✅ Session created from AWS active session: {response_data}")
            return jsonify(response_data)
            
        except mysql.connector.Error as db_err:
            logging.error(f"❌ MySQL database error: {str(db_err)}")
            conn.rollback()
            return jsonify({'error': f'Database error: {str(db_err)}'}, 500)
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logging.error(f"❌ Error in create_session_from_active: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}, 500)

# Test endpoint (optional - for testing without door system)
@app.route('/test_create_active_session', methods=['POST'])
def test_create_active_session():
    """Test endpoint to create an active session in AWS DynamoDB."""
    if not dynamodb:
        return jsonify({'error': 'AWS not configured'}), 500
    
    try:
        customer_name = request.form.get('customer_name', 'Test Customer')
        customer_address = request.form.get('customer_address', '123 Test St')
        
        # Create test session in AWS active sessions table
        active_sessions_table = dynamodb.Table('iot-convenience-store-active-sessions-production')
        
        import uuid
        test_customer_id = f"aws_cust_{uuid.uuid4().hex[:8]}"
        test_session_id = f"aws_sess_{uuid.uuid4().hex[:8]}"
        
        session_data = {
            'customer_id': test_customer_id,
            'session_id': test_session_id,
            'customer_name': customer_name,
            'customer_address': customer_address,
            'assigned_cart': 'cart-001',
            'entry_time': datetime.now().isoformat(),
            'checkout_completed': False,
            'last_activity': datetime.now().isoformat()
        }
        
        active_sessions_table.put_item(Item=session_data)
        
        return jsonify({
            'success': True,
            'message': f'Test active session created for {customer_name}',
            'session_data': session_data
        })
        
    except Exception as e:
        logging.error(f"Error creating test active session: {e}")
        return jsonify({'error': str(e)}), 500
        
        
# ALSO ADD this test endpoint to help debug
@app.route('/test_session_components')
def test_session_components():
    """Test endpoint to check all session components"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: MySQL Connection
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            results['tests']['mysql'] = {'status': 'success', 'message': 'MySQL connection working'}
        else:
            results['tests']['mysql'] = {'status': 'failed', 'message': 'Cannot connect to MySQL'}
    except Exception as e:
        results['tests']['mysql'] = {'status': 'failed', 'message': str(e)}
    
    # Test 2: AWS DynamoDB
    try:
        if 'dynamodb' in globals() and dynamodb is not None:
            # Try to describe the sessions table
            response = sessions_table.meta.client.describe_table(
                TableName=DYNAMODB_TABLES['sessions']
            )
            results['tests']['aws_dynamodb'] = {
                'status': 'success', 
                'message': f"DynamoDB accessible, table status: {response['Table']['TableStatus']}"
            }
        else:
            results['tests']['aws_dynamodb'] = {
                'status': 'not_configured', 
                'message': 'AWS DynamoDB not configured'
            }
    except Exception as e:
        results['tests']['aws_dynamodb'] = {'status': 'failed', 'message': str(e)}
    
    # Test 3: Environment Variables
    env_vars = ['AWS_REGION', 'ACCOUNT_ID', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in env_vars if not os.getenv(var)]
    
    if missing_vars:
        results['tests']['environment'] = {
            'status': 'incomplete',
            'message': f'Missing environment variables: {missing_vars}'
        }
    else:
        results['tests']['environment'] = {
            'status': 'success',
            'message': 'All environment variables present'
        }
    
    # Test 4: Required Tables
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        required_tables = ['customers', 'shopping_sessions', 'scanned_items', 'product_data']
        missing_tables = []
        
        for table in required_tables:
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = '{table}'
            """)
            if cursor.fetchone()[0] == 0:
                missing_tables.append(table)
        
        if missing_tables:
            results['tests']['database_schema'] = {
                'status': 'incomplete',
                'message': f'Missing tables: {missing_tables}'
            }
        else:
            results['tests']['database_schema'] = {
                'status': 'success',
                'message': 'All required tables exist'
            }
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        results['tests']['database_schema'] = {'status': 'failed', 'message': str(e)}
    
    return jsonify(results)

@app.route('/end_session', methods=['POST'])
def end_session():
    """End the current shopping session - HYBRID APPROACH."""
    if 'session_id' not in flask_session:
        return jsonify({'error': 'No active session'}), 400
    
    local_session_id = flask_session['session_id']
    cloud_session_id = flask_session.get('cloud_session_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Get the total amount from transactions
        cursor.execute(
            "SELECT SUM(total_amount) FROM transactions WHERE session_id = %s",
            (local_session_id,)
        )
        result = cursor.fetchone()
        total_amount = result[0] if result[0] else 0
        
        # Get the fraud count
        cursor.execute(
            "SELECT COUNT(*) FROM fraud_logs WHERE session_id = %s",
            (local_session_id,)
        )
        fraud_count = cursor.fetchone()[0]
        
        # Get item count
        cursor.execute(
            "SELECT COUNT(*) FROM scanned_items s JOIN product_data p ON s.product_id = p.id WHERE s.is_validated = TRUE"
        )
        item_count = cursor.fetchone()[0]
        
        # Update the local session
        cursor.execute(
            """
            UPDATE shopping_sessions 
            SET end_time = NOW(), total_amount = %s, fraud_alerts = %s, status = 'completed'
            WHERE id = %s
            """,
            (total_amount, fraud_count, local_session_id)
        )
        
        conn.commit()
        
        # End cloud session
        if cloud_session_id:
            cloud_session.end_cloud_session(cloud_session_id, total_amount, item_count)
        
        # Clear Flask session
        flask_session.pop('session_id', None)
        flask_session.pop('cloud_session_id', None)
        flask_session.pop('customer_id', None)
        flask_session.pop('customer_name', None)
        
        logging.info(f"✅ Hybrid session ended - Local: {local_session_id}, Cloud: {cloud_session_id}")
        
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Database error ending session: {err}")
        return jsonify({'error': f'Database error: {str(err)}'}), 500
    finally:
        cursor.close()
        conn.close()

# ADD CLOUD TEST ENDPOINT
@app.route('/test_cloud_connection')
def test_cloud_connection():
    """Test AWS DynamoDB connection."""
    if not dynamodb:
        return jsonify({
            'success': False,
            'message': 'AWS DynamoDB not configured'
        })
    
    try:
        # Test connection by describing a table
        response = sessions_table.meta.client.describe_table(TableName=DYNAMODB_TABLES['sessions'])
        
        return jsonify({
            'success': True,
            'message': 'AWS DynamoDB connection successful',
            'table_status': response['Table']['TableStatus'],
            'item_count': response['Table']['ItemCount']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AWS DynamoDB connection failed: {str(e)}'
        })


@app.route('/get_session_info')
def get_session_info():
    """Get information about the current session."""
    if 'session_id' not in flask_session:
        return jsonify({'active_session': False})
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT ss.*, c.name, c.address
            FROM shopping_sessions ss
            JOIN customers c ON ss.customer_id = c.id
            WHERE ss.id = %s
            """,
            (flask_session['session_id'],)
        )
        session_info = cursor.fetchone()
        
        if not session_info:
            # Session exists in Flask but not in database
            flask_session.pop('session_id', None)
            flask_session.pop('customer_id', None)
            flask_session.pop('customer_name', None)
            return jsonify({'active_session': False})
        
        return jsonify({
            'active_session': True,
            'session_info': session_info
        })
    except mysql.connector.Error as err:
        logging.error(f"Database error getting session info: {err}")
        return jsonify({'error': f'Database error: {str(err)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_cart_items')
def get_cart_items():
    """Return all items currently in the cart."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get session ID from Flask session or use None
        session_id = flask_session.get('session_id')
        cloud_session_id = flask_session.get('cloud_session_id')
        
        # Join scanned_items with product_data to get product information
        cursor.execute("""
            SELECT s.id, s.tag_id, s.timestamp, s.weight, s.is_validated, 
                   p.product_name, p.price, p.is_grocery
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            WHERE s.is_validated = TRUE
            ORDER BY s.timestamp DESC
        """)
        items = cursor.fetchall()
        
        # Calculate total price
        total = sum(item['price'] for item in items)
        
        return jsonify({
            'items': items,
            'total': total,
            'session_id': session_id,
            'cloud_session_id': cloud_session_id
        })
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_recent_scan')
def get_recent_scan():
    """Return the most recently scanned item that hasn't been validated yet."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT s.id, s.tag_id, s.timestamp, s.weight, s.is_validated, 
                   p.product_name, p.price, p.is_grocery
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            WHERE s.is_validated = FALSE AND s.product_id IS NOT NULL
            ORDER BY s.timestamp DESC
            LIMIT 1
        """)
        item = cursor.fetchone()
        
        if item:
            # Check if there are any fraud logs for this item
            cursor.execute("""
                SELECT * FROM fraud_logs 
                WHERE timestamp > %s 
                ORDER BY timestamp DESC
                LIMIT 1
            """, (item['timestamp'],))
            fraud = cursor.fetchone()
            
            # ✅ HOTFIX: Sync fraud to cloud if detected and not already synced
            if fraud:
                cloud_session_id = flask_session.get('cloud_session_id')
                if cloud_session_id and not fraud.get('synced_to_cloud', False):
                    try:
                        logging.info(f"🚨 Syncing fraud event to cloud: {fraud['event_type']}")
                        success = cloud_session.log_fraud_event(
                            cloud_session_id,
                            fraud['event_type'],
                            fraud['details']
                        )
                        
                        if success:
                            # Mark as synced if column exists
                            try:
                                cursor.execute(
                                    "UPDATE fraud_logs SET synced_to_cloud = TRUE WHERE id = %s",
                                    (fraud['id'],)
                                )
                                conn.commit()
                                logging.info(f"✅ Fraud event {fraud['id']} synced to cloud successfully")
                            except mysql.connector.Error:
                                # Column doesn't exist yet, skip marking
                                logging.info("✅ Fraud synced to cloud (sync tracking not available)")
                        else:
                            logging.warning(f"⚠️ Failed to sync fraud event to cloud")
                            
                    except Exception as e:
                        logging.error(f"❌ Error syncing fraud to cloud: {e}")
            
            return jsonify({
                'item': item,
                'fraud': fraud
            })
        else:
            # Check if there's a scanned item without product_id (still being processed)
            cursor.execute("""
                SELECT id, tag_id, timestamp 
                FROM scanned_items 
                WHERE product_id IS NULL AND is_validated = FALSE
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            pending_item = cursor.fetchone()
            
            if pending_item:
                return jsonify({
                    'item': None,
                    'pending': True,
                    'message': 'Card detected. Reading product information...'
                })
            else:
                return jsonify({'item': None})
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/sync_fraud_manual', methods=['POST'])
def sync_fraud_manual():
    """Manually sync recent fraud events to cloud for testing."""
    if 'cloud_session_id' not in flask_session:
        return jsonify({'error': 'No active cloud session'}), 400
    
    cloud_session_id = flask_session['cloud_session_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get recent fraud events (last 24 hours)
        cursor.execute("""
            SELECT * FROM fraud_logs 
            WHERE timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        fraud_events = cursor.fetchall()
        
        synced_count = 0
        errors = []
        
        for fraud in fraud_events:
            try:
                success = cloud_session.log_fraud_event(
                    cloud_session_id,
                    fraud['event_type'],
                    fraud['details']
                )
                
                if success:
                    synced_count += 1
                    logging.info(f"✅ Manually synced fraud event: {fraud['event_type']}")
                else:
                    errors.append(f"Failed to sync event {fraud['id']}")
                    
            except Exception as e:
                error_msg = f"Error syncing event {fraud['id']}: {str(e)}"
                errors.append(error_msg)
                logging.error(f"❌ {error_msg}")
        
        return jsonify({
            'success': True,
            'total_events': len(fraud_events),
            'synced_count': synced_count,
            'errors': errors,
            'message': f'Synced {synced_count}/{len(fraud_events)} fraud events to cloud session {cloud_session_id}'
        })
        
    except Exception as e:
        logging.error(f"Error in manual fraud sync: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/validate_item', methods=['POST'])
def validate_item():
    """Mark an item as validated (confirmed by user)."""
    item_id = request.form.get('item_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE scanned_items SET is_validated = TRUE WHERE id = %s",
            (item_id,)
        )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Database update error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/weigh_item', methods=['POST'])
def weigh_item():
    """Request Arduino to weigh an item."""
    item_id = request.form.get('item_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Verify this is a grocery item that needs weighing
        cursor.execute("""
            SELECT s.id, p.is_grocery 
            FROM scanned_items s 
            JOIN product_data p ON s.product_id = p.id 
            WHERE s.id = %s
        """, (item_id,))
        
        item_info = cursor.fetchone()
        if not item_info:
            return jsonify({'error': 'Item not found'}), 404
        
        item_id, is_grocery = item_info
        if not is_grocery:
            return jsonify({'error': 'Only grocery items need to be weighed'}), 400
        
        # Add weigh_item command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('weigh_item', json.dumps({'item_id': item_id}), 'pending', timestamp)
        )
        conn.commit()
        
        # Wait for weight to be updated (polling)
        max_retries = 10
        for _ in range(max_retries):
            time.sleep(0.5)  # Wait for serial handler to process
            
            cursor.execute(
                "SELECT weight FROM scanned_items WHERE id = %s",
                (item_id,)
            )
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                return jsonify({'success': True, 'weight': result[0]})
        
        return jsonify({'error': 'Weight measurement timed out. Please try again.'}), 408
    except mysql.connector.Error as err:
        logging.error(f"Database operation error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# @app.route('/checkout', methods=['POST'])
# def checkout():
#     """Process checkout for all validated items."""
#     conn = get_db_connection()
#     if not conn:
#         return jsonify({'error': 'Database connection failed'}), 500
    
#     cursor = conn.cursor(dictionary=True)
#     try:
#         # Get all validated items
#         cursor.execute("""
#             SELECT s.id, s.tag_id, p.product_name, p.price
#             FROM scanned_items s
#             JOIN product_data p ON s.product_id = p.id
#             WHERE s.is_validated = TRUE
#         """)
#         items = cursor.fetchall()
        
#         if not items:
#             return jsonify({'error': 'No items to checkout'}), 400
        
#         # Calculate total
#         total_amount = sum(item['price'] for item in items)
        
#         # Get session ID from Flask session
#         session_id = flask_session.get('session_id')
        
#         # Create transaction record
#         timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         item_ids = [item['id'] for item in items]
        
#         if session_id:
#             cursor.execute(
#                 "INSERT INTO transactions (user_id, session_id, total_amount, items, timestamp) VALUES (%s, %s, %s, %s, %s)",
#                 (flask_session.get('customer_id'), session_id, total_amount, json.dumps(item_ids), timestamp)
#             )
            
#             # Update shopping session
#             cursor.execute(
#                 "UPDATE shopping_sessions SET total_amount = %s WHERE id = %s",
#                 (total_amount, session_id)
#             )
#         else:
#             cursor.execute(
#                 "INSERT INTO transactions (user_id, total_amount, items, timestamp) VALUES (%s, %s, %s, %s)",
#                 (None, total_amount, json.dumps(item_ids), timestamp)
#             )
        
#         # Clear validated items
#         cursor.execute(
#             "DELETE FROM scanned_items WHERE is_validated = TRUE"
#         )
        
#         conn.commit()
        
#         # If this was part of a session, end it
#         if session_id:
#             cursor.execute(
#                 "UPDATE shopping_sessions SET end_time = NOW(), status = 'completed' WHERE id = %s",
#                 (session_id,)
#             )
#             conn.commit()
            
#             # Clear Flask session
#             flask_session.pop('session_id', None)
#             flask_session.pop('customer_id', None)
#             flask_session.pop('customer_name', None)
        
#         return jsonify({
#             'success': True,
#             'total': total_amount,
#             'items': len(items)
#         })
#     except mysql.connector.Error as err:
#         logging.error(f"Checkout error: {err}")
#         return jsonify({'error': str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# @app.route('/checkout_page')
# def checkout_page():
#     """Display the checkout page."""
#     # Check if there's an active session
#     if 'session_id' not in flask_session:
#         return redirect(url_for('welcome'))
    
#     return render_template('checkout.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    """Process checkout for all validated items - WITH CLOUD SYNC AND SIMPLE DISCOUNT SUPPORT."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get all validated items
        cursor.execute("""
            SELECT s.id, s.tag_id, p.product_name, p.price, p.is_grocery, s.weight
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            WHERE s.is_validated = TRUE
        """)
        items = cursor.fetchall()
        
        if not items:
            return jsonify({'error': 'No items to checkout'}), 400
        
        # SIMPLE DISCOUNT CHECK - Only for cust_002 with Smartphone
        cloud_customer_id = None
        if cloud_session.current_session:
            cloud_customer_id = cloud_session.current_session.get('customer_id')
        
        item_names = [item['product_name'] for item in items]
        discounts = get_applicable_discounts(cloud_customer_id, item_names)
        
        # Apply discount and calculate total
        total_amount = 0
        discount_applied = False
        total_savings = 0
        
        for item in items:
            original_price = float(item['price'])
            
            if item['product_name'] == "Smartphone" and "Smartphone" in discounts:
                # Apply discount to Smartphone
                discount_percent = discounts["Smartphone"]
                discounted_price = original_price * (1 - discount_percent / 100)
                savings = original_price - discounted_price
                
                item['original_price'] = original_price
                item['discounted_price'] = discounted_price
                item['discount_percent'] = discount_percent
                item['price'] = discounted_price  # Update price for transaction
                
                total_amount += discounted_price
                total_savings += savings
                discount_applied = True
                
                logging.info(f"✅ Applied {discount_percent}% discount to Smartphone: ${original_price:.2f} -> ${discounted_price:.2f}")
            else:
                total_amount += original_price
        
        # Get session info
        local_session_id = flask_session.get('session_id')
        cloud_session_id = flask_session.get('cloud_session_id')
        
        # Create LOCAL transaction record
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item_ids = [item['id'] for item in items]
        
        local_transaction_id = None
        if local_session_id:
            cursor.execute(
                "INSERT INTO transactions (user_id, session_id, total_amount, items, timestamp) VALUES (%s, %s, %s, %s, %s)",
                (flask_session.get('customer_id'), local_session_id, total_amount, json.dumps(item_ids), timestamp)
            )
            local_transaction_id = cursor.lastrowid
            
            # Update local shopping session
            cursor.execute(
                "UPDATE shopping_sessions SET total_amount = %s WHERE id = %s",
                (total_amount, local_session_id)
            )
        
        # Create CLOUD transaction record
        cloud_transaction_id = None
        if cloud_session_id:
            try:
                logging.info(f"Creating cloud transaction for session {cloud_session_id} with {len(items)} items")
                cloud_transaction_id = cloud_session.create_cloud_transaction(
                    cloud_session_id, 
                    items, 
                    total_amount
                )
                if cloud_transaction_id:
                    logging.info(f"[SUCCESS] Cloud transaction created successfully: {cloud_transaction_id}")
                else:
                    logging.warning("[WARNING] Cloud transaction creation returned None")
            except Exception as cloud_err:
                logging.error(f"[ERROR] Error during cloud transaction creation: {cloud_err}")
                logging.error(f"Cloud transaction error traceback: {traceback.format_exc()}")
        else:
            logging.info("[INFO] No cloud session ID available, skipping cloud transaction")
        
        conn.commit()

        if cloud_session_id:
            try:
                cursor.execute("""
                    SELECT * FROM fraud_logs 
                    WHERE session_id = %s
                    ORDER BY timestamp DESC
                """, (local_session_id,))
                session_fraud_events = cursor.fetchall()
                
                for fraud in session_fraud_events:
                    try:
                        cloud_session.log_fraud_event(
                            cloud_session_id,
                            fraud['event_type'],
                            fraud['details']
                        )
                        logging.info(f"✅ Synced fraud event during checkout: {fraud['event_type']}")
                    except Exception as fraud_sync_err:
                        logging.error(f"❌ Failed to sync fraud during checkout: {fraud_sync_err}")
                        
            except Exception as e:
                logging.error(f"❌ Error syncing fraud events during checkout: {e}")

        customer_id = flask_session.get('customer_id')
        customer_name = flask_session.get('customer_name')
        
        # End local session
        if local_session_id:
            cursor.execute(
                "UPDATE shopping_sessions SET end_time = NOW(), status = 'completed' WHERE id = %s",
                (local_session_id,)
            )
            conn.commit()
            
            # Clear Flask session
            flask_session.pop('session_id', None)
            flask_session.pop('customer_id', None)
            flask_session.pop('customer_name', None)
        
        # End cloud session
        if cloud_session_id:
            cloud_session.end_cloud_session(cloud_session_id, total_amount, len(items))
            
        # Clear validated items
        cursor.execute("DELETE FROM scanned_items WHERE is_validated = TRUE")
        conn.commit()
        
        # Build response with discount information
        response_data = {
            'success': True,
            'total': total_amount,
            'items': len(items),
            'local_transaction_id': local_transaction_id,
            'cloud_transaction_id': cloud_transaction_id,
            'cloud_enabled': cloud_transaction_id is not None,
            'discount_applied': discount_applied,
            'customer_id': cloud_customer_id
        }
        
        # Add discount info if applicable
        if discount_applied:
            response_data['original_total'] = total_amount + total_savings
            response_data['total_savings'] = total_savings
            response_data['message'] = f'Checkout successful! You saved ${total_savings:.2f} with discounts!'
        else:
            response_data['message'] = f'Checkout successful! {"Cloud sync enabled." if cloud_transaction_id else "Local only."}'

        try:
            mqtt_client = SmartCartMQTT()
            if mqtt_client.connect():
                session_data = {
                    "session_id": cloud_session_id or f"local_{local_session_id}",
                    "local_session_id": local_session_id,
                    "cloud_session_id": cloud_session_id,
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "total_amount": float(total_amount),
                    "item_count": len(items),
                    "items": [
                        {
                            "product_name": item['product_name'],
                            "price": float(item['price']),
                            "original_price": item.get('original_price', item['price']),
                            "discount_percent": item.get('discount_percent', 0),
                            "is_grocery": item.get('is_grocery', False),
                            "weight": item.get('weight')
                        } for item in items
                    ],
                    "fraud_events": [],
                    "transaction_ids": {
                        "local": local_transaction_id,
                        "cloud": cloud_transaction_id
                    },
                    "discount_applied": discount_applied,
                    "total_savings": total_savings if discount_applied else 0,
                    "completed_at": datetime.now().isoformat()
                }
                
                if mqtt_client.publish_session_complete(session_data):
                    logging.info(f"✅ MQTT session sync successful for session {cloud_session_id}")
                    response_data['mqtt_sync'] = True
                else:
                    logging.warning("⚠️ MQTT session sync failed")
                    response_data['mqtt_sync'] = False
                
                mqtt_client.disconnect()
            else:
                logging.warning("⚠️ MQTT connection failed")
                response_data['mqtt_sync'] = False
                
        except Exception as mqtt_error:
            logging.error(f"❌ MQTT sync error: {mqtt_error}")
            response_data['mqtt_sync'] = False

        if discount_applied:
            logging.info(f"[SUCCESS] Checkout completed with discount: Local ID={local_transaction_id}, Cloud ID={cloud_transaction_id}, Total=${total_amount:.2f}, Savings=${total_savings:.2f}")
        else:
            logging.info(f"[SUCCESS] Checkout completed: Local ID={local_transaction_id}, Cloud ID={cloud_transaction_id}, Total=${total_amount}")
        
        return jsonify(response_data)
        
    except mysql.connector.Error as err:
        logging.error(f"[ERROR] Checkout database error: {err}")
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        logging.error(f"[ERROR] Checkout general error: {e}")
        logging.error(f"Checkout error traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Checkout failed: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/control')
def control_panel():
    """RFID tag management control panel."""
    return render_template('control.html')

@app.route('/write_tag', methods=['POST'])
def write_tag():
    """Send command to write data to RFID tag."""
    product_name = request.form.get('product_name')
    price = request.form.get('price')
    is_grocery = request.form.get('is_grocery', 'false').lower() == 'true'
    is_control = request.form.get('is_control', 'false').lower() == 'true'  # New parameter
    
    # Data string format: product_name#price for Arduino
    data = f"{product_name}#{price}"
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Only update product_data if not in control mode
        if not is_control:
            # First check if this product already exists in product_data
            cursor.execute(
                "SELECT id FROM product_data WHERE product_name = %s AND price = %s",
                (product_name, float(price))
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing product
                cursor.execute(
                    "UPDATE product_data SET is_grocery = %s WHERE product_name = %s AND price = %s",
                    (is_grocery, product_name, float(price))
                )
                logging.info(f"Updated existing product: {product_name}")
            else:
                # Insert new product
                cursor.execute(
                    "INSERT INTO product_data (product_name, price, is_grocery) VALUES (%s, %s, %s)",
                    (product_name, float(price), is_grocery)
                )
                logging.info(f"Created new product: {product_name}")
        
        # Add write_tag command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('write_tag', json.dumps({'data': data, 'control_mode': is_control}), 'pending', timestamp)
        )
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Write command sent to Arduino. Place your tag on the reader now.'
        })
    except mysql.connector.Error as err:
        logging.error(f"Write tag error: {err}")
        return jsonify({'error': str(err)}), 500
    except ValueError:
        return jsonify({'error': 'Invalid price value'}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/read_tag', methods=['POST'])
def read_tag():
    """Send command to read data from RFID tag."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add read_tag command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('read_tag', '{}', 'pending', timestamp)
        )
        conn.commit()
        
        # In a real application, we would need to implement a way to get the data back
        # For now, we'll just return success
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Read tag error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/reset_tag', methods=['POST'])
def reset_tag():
    """Send command to reset/erase RFID tag."""
    is_control = request.form.get('is_control', 'false').lower() == 'true'  # New parameter
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add reset_tag command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('reset_tag', json.dumps({'control_mode': is_control}), 'pending', timestamp)
        )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Reset tag error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/tare_scale', methods=['POST'])
def tare_scale():
    """Send command to tare the load cell."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add tare command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('tare', '{}', 'pending', timestamp)
        )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Tare scale error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/analytics')
def analytics():
    """Display analytics and statistics."""
    return render_template('analytics.html')

@app.route('/get_analytics_data')
def get_analytics_data():
    """Return analytics data for dashboard."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get total sales
        cursor.execute("SELECT SUM(total_amount) as total_sales FROM transactions")
        sales = cursor.fetchone()['total_sales'] or 0
        
        # Get number of transactions
        cursor.execute("SELECT COUNT(*) as transaction_count FROM transactions")
        transaction_count = cursor.fetchone()['transaction_count']
        
        # Get average transaction value
        avg_transaction = sales / transaction_count if transaction_count > 0 else 0
        
        # Get customer count
        cursor.execute("SELECT COUNT(*) as customer_count FROM customers")
        customer_count = cursor.fetchone()['customer_count']
        
        # Get top products
        cursor.execute("""
            SELECT p.product_name, COUNT(*) as count
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            GROUP BY p.product_name
            ORDER BY count DESC
            LIMIT 5
        """)
        top_products = cursor.fetchall()
        
        # Get fraud events
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM fraud_logs
            GROUP BY event_type
            ORDER BY count DESC
        """)
        fraud_data = cursor.fetchall()
        
        # Get session data
        cursor.execute("""
            SELECT 
                COUNT(*) as session_count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                SUM(CASE WHEN status = 'abandoned' THEN 1 ELSE 0 END) as abandoned_sessions,
                AVG(total_amount) as avg_session_amount
            FROM shopping_sessions
        """)
        session_data = cursor.fetchone()
        
        # Get daily transactions (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as count,
                SUM(total_amount) as amount
            FROM transactions
            WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """)
        daily_transactions = cursor.fetchall()
        
        return jsonify({
            'total_sales': sales,
            'transaction_count': transaction_count,
            'avg_transaction': avg_transaction,
            'customer_count': customer_count,
            'top_products': top_products,
            'fraud_data': fraud_data,
            'session_data': session_data,
            'daily_transactions': daily_transactions
        })
    except mysql.connector.Error as err:
        logging.error(f"Analytics query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/grocery')
def grocery():
    """Grocery items page."""
    return render_template('grocery.html')

@app.route('/get_grocery_items')
def get_grocery_items():
    """Return all available grocery items."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # First check if grocery_items table exists
        try:
            cursor.execute("""
                SELECT id, product_name, price_per_kg, image_path, description, is_available
                FROM grocery_items
                WHERE is_available = TRUE
                ORDER BY product_name
            """)
            items = cursor.fetchall()
        except mysql.connector.Error as table_err:
            # Table might not exist, provide default items
            logging.warning(f"Error accessing grocery_items table: {table_err}")
            
            # Return some default items if table doesn't exist
            items = [
                {
                    'id': 1, 
                    'product_name': 'Apples', 
                    'price_per_kg': 2.99, 
                    'image_path': '/static/images/default.jpg', 
                    'description': 'Fresh red apples',
                    'is_available': True
                },
                {
                    'id': 2, 
                    'product_name': 'Bananas', 
                    'price_per_kg': 1.49, 
                    'image_path': '/static/images/default.jpg', 
                    'description': 'Ripe yellow bananas',
                    'is_available': True
                },
                {
                    'id': 3, 
                    'product_name': 'Tomatoes', 
                    'price_per_kg': 2.49, 
                    'image_path': '/static/images/default.jpg', 
                    'description': 'Vine-ripened tomatoes',
                    'is_available': True
                },
                {
                    'id': 4, 
                    'product_name': 'Potatoes', 
                    'price_per_kg': 1.99, 
                    'image_path': '/static/images/default.jpg', 
                    'description': 'Russet potatoes',
                    'is_available': True
                }
            ]
        
        return jsonify({
            'items': items
        })
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_grocery_weight', methods=['POST'])
def get_grocery_weight():
    """Get the weight of a grocery item."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Check if weight_readings table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'weight_readings'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            # If table doesn't exist, send command to create it and get a weight
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
                ('weigh_item', '{}', 'pending', timestamp)
            )
            conn.commit()
            
            # Wait a bit for serial handler to process
            time.sleep(1.0)
            
            return jsonify({'error': 'Please wait, initializing scale...'}), 202
        
        # First, send the weigh command to Arduino
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('weigh_item', '{}', 'pending', timestamp)
        )
        conn.commit()
        
        # Wait a bit for the serial handler to process the command
        time.sleep(0.5)
        
        # Get the most recent weight reading
        cursor.execute("""
            SELECT weight, timestamp 
            FROM weight_readings
            WHERE timestamp > DATE_SUB(NOW(), INTERVAL 10 SECOND)
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result and result[0] is not None:
            weight = float(result[0])
            
            # Only return if the weight is above a minimum threshold
            if weight > 10:
                # Success - we have a valid weight
                return jsonify({'weight': weight})
        
        # If we didn't get a valid weight, return an error
        return jsonify({'error': 'Waiting for item on scale...'}), 202
    except mysql.connector.Error as err:
        logging.error(f"Database operation error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_cart_items_with_discounts')
def get_cart_items_with_discounts():
    """Return cart items with discount information applied"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get all validated items
        cursor.execute("""
            SELECT s.id, s.tag_id, s.timestamp, s.weight, s.is_validated, 
                   p.product_name, p.price, p.is_grocery
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            WHERE s.is_validated = TRUE
            ORDER BY s.timestamp DESC
        """)
        items = cursor.fetchall()
        
        # Get customer ID for discounts
        cloud_customer_id = None
        if cloud_session.current_session:
            cloud_customer_id = cloud_session.current_session.get('customer_id')
        
        # Apply discounts to items
        item_names = [item['product_name'] for item in items]
        discounts = get_applicable_discounts(cloud_customer_id, item_names)
        
        total = 0
        original_total = 0
        total_savings = 0
        
        for item in items:
            original_price = float(item['price'])
            original_total += original_price
            
            if item['product_name'] == "Smartphone" and "Smartphone" in discounts:
                # Apply discount
                discount_percent = discounts["Smartphone"]
                discounted_price = original_price * (1 - discount_percent / 100)
                savings = original_price - discounted_price
                
                # Add discount info to item
                item['original_price'] = original_price
                item['discounted_price'] = discounted_price
                item['discount_percent'] = discount_percent
                item['savings'] = savings
                item['price'] = discounted_price  # Update current price
                
                total += discounted_price
                total_savings += savings
            else:
                total += original_price
        
        return jsonify({
            'items': items,
            'total': total,
            'original_total': original_total,
            'total_savings': total_savings,
            'discount_applied': total_savings > 0,
            'session_id': flask_session.get('session_id'),
            'cloud_session_id': flask_session.get('cloud_session_id')
        })
        
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        logging.error(f"Error in get_cart_items_with_discounts: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add_grocery_to_cart', methods=['POST'])
def add_grocery_to_cart():
    """Add a weighed grocery item to the cart."""
    grocery_id = request.form.get('grocery_id')
    weight = request.form.get('weight')
    price = request.form.get('price')
    
    if not grocery_id or not weight or not price:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        weight = float(weight)
        price = float(price)
    except ValueError:
        return jsonify({'error': 'Invalid weight or price format'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Get the grocery item details
        cursor.execute(
            "SELECT product_name, price_per_kg FROM grocery_items WHERE id = %s",
            (grocery_id,)
        )
        grocery = cursor.fetchone()
        
        if not grocery:
            return jsonify({'error': 'Grocery item not found'}), 404
        
        product_name, price_per_kg = grocery
        
        # Create a temporary entry in product_data for this specific weight/price
        # or find an existing one
        cursor.execute(
            "SELECT id FROM product_data WHERE product_name = %s AND price = %s AND is_grocery = TRUE",
            (product_name, price)
        )
        product = cursor.fetchone()
        
        if product:
            product_id = product[0]
        else:
            # Insert a new product record
            cursor.execute(
                "INSERT INTO product_data (product_name, price, is_grocery) VALUES (%s, %s, %s)",
                (product_name, price, True)
            )
            product_id = cursor.lastrowid
        
        # Create a scanned_item entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        session_id = flask_session.get('session_id')
        
        cursor.execute(
            "INSERT INTO scanned_items (tag_id, timestamp, product_id, weight, is_validated) VALUES (%s, %s, %s, %s, %s)",
            (f"GROCERY-{grocery_id}", timestamp, product_id, weight, True)  # Already validated
        )
        
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Database operation error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/session_dashboard')
def session_dashboard():
    """Display a dashboard of all shopping sessions."""
    return render_template('session_dashboard.html')

@app.route('/get_sessions')
def get_sessions():
    """Return all shopping sessions."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ss.*, c.name as customer_name, c.address as customer_address
            FROM shopping_sessions ss
            JOIN customers c ON ss.customer_id = c.id
            ORDER BY ss.start_time DESC
        """)
        sessions = cursor.fetchall()
        
        return jsonify({
            'sessions': sessions
        })
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/checkout_page')
def checkout_page():
    """Checkout page."""
    return render_template('checkout.html')

@app.route('/customer_details')
def customer_details():
    """Display customer details."""
    if 'customer_id' not in flask_session:
        return redirect(url_for('welcome'))
    
    customer_id = flask_session['customer_id']
    
    conn = get_db_connection()
    if not conn:
        return render_template('error.html', message='Database connection failed')
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT ss.id) as session_count,
                   SUM(ss.total_amount) as total_spent
            FROM customers c
            LEFT JOIN shopping_sessions ss ON c.id = ss.customer_id
            WHERE c.id = %s
            GROUP BY c.id
        """, (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            return render_template('error.html', message='Customer not found')
        
        cursor.execute("""
            SELECT ss.*, 
                   (SELECT COUNT(*) FROM fraud_logs fl WHERE fl.session_id = ss.id) as fraud_count
            FROM shopping_sessions ss
            WHERE ss.customer_id = %s
            ORDER BY ss.start_time DESC
        """, (customer_id,))
        sessions = cursor.fetchall()
        
        return render_template('customer_details.html', customer=customer, sessions=sessions)
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return render_template('error.html', message='Database error: ' + str(err))
    finally:
        cursor.close()
        conn.close()

@app.route('/get_customers')
def get_customers():
    """Return all customers with their statistics."""
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'last_visit')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Build the query
        query = """
            SELECT c.*, 
                   COUNT(DISTINCT ss.id) as session_count,
                   SUM(ss.total_amount) as total_spent,
                   (SELECT COUNT(*) FROM fraud_logs fl JOIN shopping_sessions ss2 ON fl.session_id = ss2.id WHERE ss2.customer_id = c.id) as fraud_count
            FROM customers c
            LEFT JOIN shopping_sessions ss ON c.id = ss.customer_id
        """
        
        # Add search condition if provided
        params = []
        if search:
            query += " WHERE c.name LIKE %s OR c.address LIKE %s"
            params = [f"%{search}%", f"%{search}%"]
        
        # Group by customer
        query += " GROUP BY c.id"
        
        # Add sorting
        if sort_by == 'name':
            query += " ORDER BY c.name"
        elif sort_by == 'total_spent':
            query += " ORDER BY total_spent DESC"
        elif sort_by == 'session_count':
            query += " ORDER BY session_count DESC"
        else:  # default to last_visit
            query += " ORDER BY c.last_visit DESC"
        
        cursor.execute(query, params)
        customers = cursor.fetchall()
        
        return jsonify({'customers': customers})
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_customer_details')
def get_customer_details():
    """Get detailed information about a specific customer."""
    customer_id = request.args.get('customer_id')
    
    if not customer_id:
        return jsonify({'error': 'Customer ID is required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get customer details
        cursor.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT ss.id) as session_count,
                   SUM(ss.total_amount) as total_spent,
                   (SELECT COUNT(*) FROM fraud_logs fl JOIN shopping_sessions ss2 ON fl.session_id = ss2.id WHERE ss2.customer_id = c.id) as fraud_count
            FROM customers c
            LEFT JOIN shopping_sessions ss ON c.id = ss.customer_id
            WHERE c.id = %s
            GROUP BY c.id
        """, (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get customer sessions
        cursor.execute("""
            SELECT ss.*, 
                   (SELECT COUNT(*) FROM fraud_logs fl WHERE fl.session_id = ss.id) as fraud_count
            FROM shopping_sessions ss
            WHERE ss.customer_id = %s
            ORDER BY ss.start_time DESC
        """, (customer_id,))
        sessions = cursor.fetchall()
        
        return jsonify({
            'customer': customer,
            'sessions': sessions
        })
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_session_details')
def get_session_details():
    """Get detailed information about a specific session."""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get session details
        cursor.execute("""
            SELECT ss.*, c.name as customer_name
            FROM shopping_sessions ss
            JOIN customers c ON ss.customer_id = c.id
            WHERE ss.id = %s
        """, (session_id,))
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get session items
        cursor.execute("""
            SELECT t.id, p.product_name, p.price, s.weight, p.is_grocery
            FROM transactions t
            JOIN JSON_TABLE(t.items, '$[*]' COLUMNS(item_id INT PATH '$')) AS j
            JOIN scanned_items s ON j.item_id = s.id
            JOIN product_data p ON s.product_id = p.id
            WHERE t.session_id = %s
        """, (session_id,))
        items = cursor.fetchall()
        
        # Get fraud logs
        cursor.execute("""
            SELECT * FROM fraud_logs
            WHERE session_id = %s
            ORDER BY timestamp DESC
        """, (session_id,))
        fraud_logs = cursor.fetchall()
        
        return jsonify({
            'session': session,
            'items': items,
            'fraud_logs': fraud_logs
        })
    except mysql.connector.Error as err:
        logging.error(f"Database query error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add_customer', methods=['POST'])
def add_customer():
    """Add a new customer."""
    name = request.form.get('name')
    address = request.form.get('address')
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Check if customer already exists
        cursor.execute("SELECT id FROM customers WHERE name = %s", (name,))
        existing = cursor.fetchone()
        
        if existing:
            return jsonify({'error': 'A customer with this name already exists'}), 400
        
        # Insert new customer
        cursor.execute(
            "INSERT INTO customers (name, address) VALUES (%s, %s)",
            (name, address)
        )
        customer_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'success': True,
            'customer_id': customer_id
        })
    except mysql.connector.Error as err:
        logging.error(f"Database error adding customer: {err}")
        return jsonify({'error': f'Database error: {str(err)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/read_tag_control', methods=['POST'])
def read_tag_control():
    """Read RFID tag data for control page - won't affect cart."""
    logging.info("read_tag_control route called")
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Create control_results table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tag_id VARCHAR(100),
                data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # First, set the control flag
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('_control_read_flag', json.dumps({'purpose': 'control_read_only'}), 'pending', timestamp)
        )
        
        # Then add the actual read command
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('read_tag', json.dumps({'control_mode': True}), 'pending', timestamp)
        )
        
        conn.commit()
        logging.info("Control read commands added to database")
        
        # Wait for serial handler to process and store results
        max_retries = 15
        tag_data = None
        tag_id = None
        
        for _ in range(max_retries):
            time.sleep(1)
            
            # Check for results in control_results table
            cursor.execute("""
                SELECT tag_id, data 
                FROM control_results 
                WHERE timestamp > %s 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (timestamp,))
            
            result = cursor.fetchone()
            if result:
                tag_id, tag_data = result
                logging.info(f"Found control read result: {tag_data}")
                break
        
        if tag_data:
            return jsonify({'data': tag_data, 'tag_id': tag_id})
        else:
            return jsonify({'message': 'No data read from tag or timeout occurred'})
    except mysql.connector.Error as err:
        logging.error(f"Read tag control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/read_weight_control', methods=['POST'])
def read_weight_control():
    """Read weight from load cell for control page."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Send command to read weight
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('weigh_item', json.dumps({'control_mode': True}), 'pending', timestamp)
        )
        conn.commit()
        
        # Wait briefly for command to be processed
        time.sleep(1)
        
        # Check for recent weight readings
        max_retries = 10
        weight_value = None
        
        for _ in range(max_retries):
            cursor.execute("""
                SELECT weight
                FROM weight_readings
                WHERE timestamp > %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (timestamp,))
            
            result = cursor.fetchone()
            if result and result[0]:
                weight_value = float(result[0])
                break
            
            time.sleep(1)
        
        if weight_value is not None:
            return jsonify({'success': True, 'weight': weight_value})
        else:
            # Return a partial success to let the frontend know to keep polling
            return jsonify({'success': True, 'message': 'Reading weight, please wait...'})
    except mysql.connector.Error as err:
        logging.error(f"Read weight control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_latest_weight', methods=['GET'])
def get_latest_weight():
    """Get the latest weight reading."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Check if weight_readings table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'weight_readings'
        """)
        
        if cursor.fetchone()[0] == 0:
            return jsonify({'error': 'Weight readings not available'}), 404
        
        # Get the most recent weight reading
        cursor.execute("""
            SELECT weight, timestamp 
            FROM weight_readings
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'No weight readings available'}), 404
            
        # Handle possible NULL values
        weight = float(result[0]) if result[0] is not None else 0
        
        # Format timestamp
        if result[1]:
            if hasattr(result[1], 'strftime'):
                timestamp = result[1].strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp = str(result[1])
        else:
            timestamp = 'Unknown'
            
        # Check if we have a valid weight (above zero)
        if weight <= 0:
            return jsonify({'error': 'No valid weight readings available'}), 404
            
        return jsonify({
            'weight': weight, 
            'timestamp': timestamp
        })
            
    except mysql.connector.Error as err:
        logging.error(f"Get latest weight error: {err}")
        return jsonify({'error': f'Database error: {str(err)}'}), 500
    except Exception as e:
        logging.error(f"Unexpected error in get_latest_weight: {e}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/read_tag_control_only', methods=['POST'])
def read_tag_control_only():
    """Read RFID tag data for control page - completely separate from cart."""
    logging.info("Control-only RFID read requested")
    
    # Get tag ID if available (usually won't be until after read)
    tag_id = request.form.get('tag_id', 'pending')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Ensure control_results table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tag_id VARCHAR(100),
                data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Send READC command directly
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('READC', json.dumps({'tag_id': tag_id}), 'pending', timestamp)
        )
        conn.commit()
        
        logging.info("READC command sent to serial handler")
        
        # Wait for a result to appear in control_results
        max_retries = 15
        tag_data = None
        result_tag_id = None
        
        for _ in range(max_retries):
            time.sleep(1)
            cursor.execute("""
                SELECT tag_id, data 
                FROM control_results 
                WHERE timestamp > %s 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (timestamp,))
            
            result = cursor.fetchone()
            if result:
                result_tag_id, tag_data = result
                logging.info(f"Found control read result: tag={result_tag_id}, data={tag_data}")
                break
        
        if tag_data:
            return jsonify({'success': True, 'data': tag_data, 'tag_id': result_tag_id})
        else:
            return jsonify({'success': False, 'message': 'No data read from tag or timeout occurred'})
    except mysql.connector.Error as err:
        logging.error(f"Database error in read_tag_control_only: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_latest_tag_data', methods=['GET'])
def get_latest_tag_data():
    """Get the most recent tag data from the control_results table."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Check if control_results table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'control_results'
        """)
        
        if cursor.fetchone()[0] == 0:
            return jsonify({'message': 'No tag data available yet'})
        
        # Get the most recent tag data
        cursor.execute("""
            SELECT tag_id, data, timestamp 
            FROM control_results
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'message': 'No tag data available yet'})
        
        tag_id, data, timestamp = result
        
        # Format timestamp if needed
        if hasattr(timestamp, 'strftime'):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'tag_id': tag_id,
            'data': data,
            'timestamp': timestamp
        })
    except mysql.connector.Error as err:
        logging.error(f"Get latest tag data error: {err}")
        return jsonify({'error': str(err)})
    finally:
        cursor.close()
        conn.close()

@app.route('/tare_scale_control', methods=['POST'])
def tare_scale_control():
    """Send command to tare the load cell from control page."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add tare command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('tare', json.dumps({'control_mode': True}), 'pending', timestamp)
        )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Tare scale control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/open_lid_control', methods=['POST'])
def open_lid_control():
    """Send command to open lid from control page."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add open_lid command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('OPEN_LID', json.dumps({'control_mode': True}), 'pending', timestamp)
        )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Open lid control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/close_lid_control', methods=['POST'])
def close_lid_control():
    """Send command to close lid from control page."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add close_lid command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('CLOSE_LID', json.dumps({'control_mode': True}), 'pending', timestamp)
        )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Close lid control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/trigger_buzzer_control', methods=['POST'])
def trigger_buzzer_control():
    """Send command to trigger buzzer from control page."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add buzzer command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Define command type explicitly as a variable for clarity
        command_type = 'BUZZER'
        parameters = json.dumps({'control_mode': True})
        status = 'pending'
        
        # Super detailed logging
        logging.info(f"BUZZER COMMAND DEBUG - About to insert: command_type='{command_type}' (type: {type(command_type)}), parameters={parameters}, status={status}")
        
        # Insert the command
        sql_statement = "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)"
        values = (command_type, parameters, status, timestamp)
        logging.info(f"SQL statement: {sql_statement}")
        logging.info(f"Values: {values}")
        
        cursor.execute(sql_statement, values)
        inserted_id = cursor.lastrowid
        logging.info(f"Inserted command with ID {inserted_id}")
        
        # Verify the value was properly stored by selecting it back
        cursor.execute("SELECT command_type, parameters FROM commands WHERE id = %s", (inserted_id,))
        result = cursor.fetchone()
        if result:
            stored_command, stored_params = result
            logging.info(f"VERIFICATION: Stored command_type='{stored_command}' (type: {type(stored_command)}), parameters={stored_params}")
        else:
            logging.warning("VERIFICATION FAILED: Could not retrieve the inserted command")
        
        conn.commit()
        logging.info("Transaction committed successfully")
        
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Trigger buzzer control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/toggle_led_control', methods=['POST'])
def toggle_led_control():
    """Send command to toggle LED from control page."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Add LED toggle command to commands table
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
        "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
        ('LED', json.dumps({'control_mode': True}), 'pending', timestamp)
    )
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        logging.error(f"Toggle LED control error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/test_command_insert', methods=['GET'])
def test_command_insert():
    """Test route to directly insert a command into the database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Test data
        command_type = 'TEST_COMMAND'
        parameters = json.dumps({'test': True})
        status = 'pending'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Log before insertion
        logging.info(f"TEST ROUTE - About to insert: command_type='{command_type}'")
        
        # Insert command
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            (command_type, parameters, status, timestamp)
        )
        
        inserted_id = cursor.lastrowid
        logging.info(f"TEST ROUTE - Inserted command ID: {inserted_id}")
        
        # Verify insertion
        cursor.execute("SELECT * FROM commands WHERE id = %s", (inserted_id,))
        result = cursor.fetchone()
        logging.info(f"TEST ROUTE - Retrieved from DB: {result}")
        
        conn.commit()
        logging.info("TEST ROUTE - Transaction committed")
        
        return jsonify({
            'success': True,
            'message': f'Test command inserted with ID {inserted_id}',
            'data': {'command_id': inserted_id}
        })
    except mysql.connector.Error as err:
        logging.error(f"TEST ROUTE - Database error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/check_db_structure', methods=['GET'])
def check_db_structure():
    """Check the database structure for the commands table."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        # Check if commands table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'commands'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            return jsonify({'error': 'Commands table does not exist'}), 404
        
        # Get table structure
        cursor.execute("DESCRIBE commands")
        columns = cursor.fetchall()
        
        # Get recent commands
        cursor.execute("SELECT * FROM commands ORDER BY id DESC LIMIT 5")
        recent_commands = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'table_structure': columns,
            'recent_commands': recent_commands
        })
    except mysql.connector.Error as err:
        logging.error(f"Check DB structure error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/direct_buzzer_insert', methods=['POST'])
def direct_buzzer_insert():
    """Direct SQL insertion for buzzer command."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Direct SQL execution
        sql = """
        INSERT INTO commands (command_type, parameters, status, timestamp) 
        VALUES ('BUZZER', '{"control_mode": true}', 'pending', %s)
        """
        
        cursor.execute(sql, (timestamp,))
        inserted_id = cursor.lastrowid
        
        conn.commit()
        logging.info(f"DIRECT SQL - Inserted buzzer command with ID {inserted_id}")
        
        return jsonify({
            'success': True,
            'command_id': inserted_id
        })
    except mysql.connector.Error as err:
        logging.error(f"Direct SQL error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
