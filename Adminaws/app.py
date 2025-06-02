#!/usr/bin/env python3
"""
IoT Store Admin UI - Production Flask Application
Enhanced version with proper DynamoDB integration
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import boto3
import os
import json
import uuid
import random
import string
from datetime import datetime, timedelta
from botocore.exceptions import NoCredentialsError, ClientError
from decimal import Decimal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'iot-store-secret-key-prod')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

    # DynamoDB Table Names from environment variables
    CUSTOMERS_TABLE = os.environ.get(
        'CUSTOMERS_TABLE', 'iot-convenience-store-customers-production')
    PRODUCTS_TABLE = os.environ.get(
        'PRODUCTS_TABLE', 'iot-convenience-store-products-production')
    SESSIONS_TABLE = os.environ.get(
        'SESSIONS_TABLE', 'iot-convenience-store-sessions-production')
    TRANSACTIONS_TABLE = os.environ.get(
        'TRANSACTIONS_TABLE', 'iot-convenience-store-transactions-production')
    FRAUD_EVENTS_TABLE = os.environ.get(
        'FRAUD_EVENTS_TABLE', 'iot-convenience-store-fraud-events-production')
    ACCESS_LOGS_TABLE = os.environ.get(
        'ACCESS_LOGS_TABLE', 'iot-convenience-store-access-logs-production')
    SHELF_DISPLAYS_TABLE = os.environ.get(
        'SHELF_DISPLAYS_TABLE', 'iot-convenience-store-shelf-displays-production')
    SYSTEM_NODES_TABLE = os.environ.get(
        'SYSTEM_NODES_TABLE', 'iot-convenience-store-system-nodes-production')
    SCANNED_ITEMS_TABLE = os.environ.get(
        'SCANNED_ITEMS_TABLE', 'iot-convenience-store-scanned-items-production')
    SENSOR_DATA_TABLE = os.environ.get(
        'SENSOR_DATA_TABLE', 'iot-convenience-store-sensor-data-production')
    INVENTORY_TRANSACTIONS_TABLE = os.environ.get(
        'INVENTORY_TRANSACTIONS_TABLE', 'iot-convenience-store-inventory-transactions-production')


app.config.from_object(Config)


class DynamoDBClient:
    def __init__(self):
        try:
            self.dynamodb = boto3.resource(
                'dynamodb', region_name=app.config['AWS_REGION'])
            self.tables = {
                'customers': self.dynamodb.Table(app.config['CUSTOMERS_TABLE']),
                'products': self.dynamodb.Table(app.config['PRODUCTS_TABLE']),
                'sessions': self.dynamodb.Table(app.config['SESSIONS_TABLE']),
                'transactions': self.dynamodb.Table(app.config['TRANSACTIONS_TABLE']),
                'fraud_events': self.dynamodb.Table(app.config['FRAUD_EVENTS_TABLE']),
                'access_logs': self.dynamodb.Table(app.config['ACCESS_LOGS_TABLE']),
                'shelf_displays': self.dynamodb.Table(app.config['SHELF_DISPLAYS_TABLE']),
                'system_nodes': self.dynamodb.Table(app.config['SYSTEM_NODES_TABLE']),
                'scanned_items': self.dynamodb.Table(app.config['SCANNED_ITEMS_TABLE']),
                'sensor_data': self.dynamodb.Table(app.config['SENSOR_DATA_TABLE']),
                'inventory_transactions': self.dynamodb.Table(app.config['INVENTORY_TRANSACTIONS_TABLE'])
            }
            self.connected = True
            logger.info(
                f"✅ Connected to DynamoDB in {app.config['AWS_REGION']}")
            logger.info(f"📊 Tables configured: {list(self.tables.keys())}")

            # Initialize tables with sample data if empty
            self._initialize_sample_data()

        except Exception as e:
            logger.error(f"❌ DynamoDB connection error: {e}")
            self.connected = False

    def _initialize_sample_data(self):
        """Initialize tables with sample data if they're empty"""
        try:
            # Add sample customers
            customers_count = self.tables['customers'].scan(Select='COUNT')[
                'Count']
            if customers_count == 0:
                logger.info("🔄 Initializing sample customers...")
                sample_customers = [
                    {
                        'customer_id': 'cust_001',
                        'customer_name': 'John Doe',
                        'customer_type': 'VIP',
                        'rfid_card_uid': 'ABC123456789',
                        'email': 'john.doe@university.edu',
                        'phone': '+1234567890',
                        'total_spent': Decimal('1250.75'),
                        'total_visits': 45,
                        'membership_status': 'ACTIVE',
                        'created_at': datetime.utcnow().isoformat(),
                        'last_visit': datetime.utcnow().isoformat()
                    },
                    {
                        'customer_id': 'cust_002',
                        'customer_name': 'Jane Smith',
                        'customer_type': 'REGULAR',
                        'rfid_card_uid': 'DEF987654321',
                        'email': 'jane.smith@university.edu',
                        'phone': '+1987654321',
                        'total_spent': Decimal('675.25'),
                        'total_visits': 23,
                        'membership_status': 'ACTIVE',
                        'created_at': datetime.utcnow().isoformat(),
                        'last_visit': (datetime.utcnow() - timedelta(days=2)).isoformat()
                    },
                    {
                        'customer_id': 'cust_003',
                        'customer_name': 'Admin User',
                        'customer_type': 'ADMIN',
                        'rfid_card_uid': 'GHI555666777',
                        'email': 'admin@iotstore.com',
                        'phone': '+1555666777',
                        'total_spent': Decimal('0.00'),
                        'total_visits': 5,
                        'membership_status': 'ACTIVE',
                        'created_at': datetime.utcnow().isoformat(),
                        'last_visit': datetime.utcnow().isoformat()
                    }
                ]

                for customer in sample_customers:
                    self.tables['customers'].put_item(Item=customer)
                logger.info(
                    f"✅ Added {len(sample_customers)} sample customers")

            # Add sample products
            products_count = self.tables['products'].scan(Select='COUNT')[
                'Count']
            if products_count == 0:
                logger.info("🔄 Initializing sample products...")
                sample_products = [
                    {
                        'product_id': 'prod_001',
                        'product_rfid': 'RFID001',
                        'product_name': 'Premium Coffee',
                        'description': 'High-quality arabica coffee beans',
                        'category': 'Beverages',
                        'regular_price': Decimal('15.99'),
                        'current_price': Decimal('15.99'),
                        'vip_price': Decimal('12.79'),
                        'weight_per_unit': Decimal('500.0'),
                        'is_premium': True,
                        'is_active': True,
                        'created_at': datetime.utcnow().isoformat()
                    },
                    {
                        'product_id': 'prod_002',
                        'product_rfid': 'RFID002',
                        'product_name': 'Energy Drink',
                        'description': 'Popular energy drink 250ml',
                        'category': 'Beverages',
                        'regular_price': Decimal('3.49'),
                        'current_price': Decimal('2.99'),
                        'vip_price': Decimal('2.79'),
                        'weight_per_unit': Decimal('250.0'),
                        'is_premium': False,
                        'is_active': True,
                        'created_at': datetime.utcnow().isoformat()
                    },
                    {
                        'product_id': 'prod_003',
                        'product_rfid': 'RFID003',
                        'product_name': 'Chocolate Bar',
                        'description': 'Premium dark chocolate 70% cocoa',
                        'category': 'Snacks',
                        'regular_price': Decimal('4.99'),
                        'current_price': Decimal('4.99'),
                        'vip_price': Decimal('4.49'),
                        'weight_per_unit': Decimal('100.0'),
                        'is_premium': True,
                        'is_active': True,
                        'created_at': datetime.utcnow().isoformat()
                    }
                ]

                for product in sample_products:
                    self.tables['products'].put_item(Item=product)
                logger.info(f"✅ Added {len(sample_products)} sample products")

            # Add sample transactions
            transactions_count = self.tables['transactions'].scan(Select='COUNT')[
                'Count']
            if transactions_count == 0:
                logger.info("🔄 Initializing sample transactions...")
                sample_transactions = []
                for i in range(10):
                    transaction = {
                        'transaction_id': f'txn_{uuid.uuid4().hex[:8]}',
                        'session_id': f'sess_{uuid.uuid4().hex[:8]}',
                        'user_id': f'cust_00{(i % 3) + 1}',
                        'total_amount': Decimal(str(round(random.uniform(5.0, 50.0), 2))),
                        'items': json.dumps([{'product_id': f'prod_00{(i % 3) + 1}', 'quantity': random.randint(1, 3)}]),
                        'timestamp': (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
                        'store_id': 'store_001',
                        'payment_method': 'card',
                        'transaction_status': 'completed'
                    }
                    sample_transactions.append(transaction)
                    self.tables['transactions'].put_item(Item=transaction)
                logger.info(
                    f"✅ Added {len(sample_transactions)} sample transactions")

            # Add sample system nodes
            nodes_count = self.tables['system_nodes'].scan(Select='COUNT')[
                'Count']
            if nodes_count == 0:
                logger.info("🔄 Initializing system nodes...")
                sample_nodes = [
                    {
                        'node_id': 'cart-001',
                        'node_type': 'smart-cart',
                        'store_id': 'store_001',
                        'device_identifier': 'cart-001',
                        'location': 'Store Floor',
                        'status': 'active',
                        'is_online': True,
                        'last_heartbeat': datetime.utcnow().isoformat(),
                        'hardware_version': '2.0.0',
                        'firmware_version': '1.5.0'
                    },
                    {
                        'node_id': 'door-001',
                        'node_type': 'door-access',
                        'store_id': 'store_001',
                        'device_identifier': 'door-001',
                        'location': 'Main Entrance',
                        'status': 'active',
                        'is_online': True,
                        'last_heartbeat': datetime.utcnow().isoformat(),
                        'hardware_version': '2.0.0',
                        'firmware_version': '1.5.0'
                    },
                    {
                        'node_id': 'shelf-001',
                        'node_type': 'smart-shelf',
                        'store_id': 'store_001',
                        'device_identifier': 'shelf-001',
                        'location': 'Premium Section',
                        'status': 'active',
                        'is_online': True,
                        'last_heartbeat': datetime.utcnow().isoformat(),
                        'hardware_version': '2.0.0',
                        'firmware_version': '1.5.0'
                    }
                ]

                for node in sample_nodes:
                    self.tables['system_nodes'].put_item(Item=node)
                logger.info(f"✅ Added {len(sample_nodes)} system nodes")

        except Exception as e:
            logger.error(f"❌ Error initializing sample data: {e}")

    def get_customers(self, limit=50):
        """Get customers with proper error handling"""
        try:
            if not self.connected:
                return self._get_fallback_customers()

            response = self.tables['customers'].scan(Limit=limit)
            customers = response.get('Items', [])

            # Convert Decimal to float for JSON serialization
            formatted_customers = []
            for customer in customers:
                formatted_customers.append({
                    'customer_id': customer.get('customer_id', ''),
                    'customer_name': customer.get('customer_name', ''),
                    'customer_type': customer.get('customer_type', 'REGULAR'),
                    'rfid_card_uid': customer.get('rfid_card_uid', ''),
                    'email': customer.get('email', ''),
                    'phone': customer.get('phone', ''),
                    'total_spent': float(customer.get('total_spent', 0)),
                    'total_visits': int(customer.get('total_visits', 0)),
                    'membership_status': customer.get('membership_status', 'ACTIVE'),
                    'last_visit': customer.get('last_visit', datetime.utcnow().isoformat())[:10]
                })

            logger.info(f"📊 Retrieved {len(formatted_customers)} customers")
            return formatted_customers
        except Exception as e:
            logger.error(f"❌ Error getting customers: {e}")
            return self._get_fallback_customers()

    def get_analytics_data(self):
        """Get comprehensive analytics data"""
        try:
            if not self.connected:
                return self._get_fallback_analytics()

            # Get counts from all tables
            customers_count = self.tables['customers'].scan(Select='COUNT')[
                'Count']
            sessions_count = self.tables['sessions'].scan(Select='COUNT')[
                'Count']
            fraud_count = self.tables['fraud_events'].scan(Select='COUNT')[
                'Count']

            # Get recent transactions for sales calculation
            recent_transactions = self.get_recent_transactions(50)
            total_sales = sum(float(t.get('amount', 0))
                              for t in recent_transactions)

            # Generate mock daily sales data (in production, this would come from aggregated data)
            daily_sales = []
            for i in range(7):
                date = datetime.utcnow() - timedelta(days=6-i)
                sales = random.uniform(800, 2000)
                daily_sales.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'sales': round(sales, 2)
                })

            analytics = {
                'total_customers': customers_count,
                'active_sessions': sessions_count,
                'total_sales_today': total_sales,
                'fraud_alerts': fraud_count,
                'daily_sales': daily_sales,
                'fraud_events': [
                    {'type': 'unscanned_item', 'count': 12},
                    {'type': 'weight_mismatch', 'count': 8},
                    {'type': 'multiple_items', 'count': 5},
                    {'type': 'no_placement', 'count': 15}
                ]
            }

            logger.info(
                f"📈 Analytics: {customers_count} customers, {sessions_count} sessions, ${total_sales:.2f} sales")
            return analytics
        except Exception as e:
            logger.error(f"❌ Error getting analytics: {e}")
            return self._get_fallback_analytics()

    def get_recent_transactions(self, limit=10):
        """Get recent transactions"""
        try:
            if not self.connected:
                return self._get_fallback_transactions()

            response = self.tables['transactions'].scan(Limit=limit)
            transactions = response.get('Items', [])

            # Sort by timestamp (most recent first)
            transactions.sort(key=lambda x: x.get(
                'timestamp', ''), reverse=True)

            formatted_transactions = []
            for txn in transactions[:limit]:
                # Parse items JSON
                items_str = txn.get('items', '[]')
                try:
                    items = json.loads(items_str) if items_str else []
                except:
                    items = []

                formatted_transactions.append({
                    'transaction_id': txn.get('transaction_id', ''),
                    'customer_name': f"Customer {txn.get('user_id', 'Unknown')[-3:]}",
                    'amount': float(txn.get('total_amount', 0)),
                    'items': len(items),
                    'timestamp': txn.get('timestamp', datetime.utcnow().isoformat()),
                    'status': txn.get('transaction_status', 'completed')
                })

            logger.info(
                f"💳 Retrieved {len(formatted_transactions)} recent transactions")
            return formatted_transactions
        except Exception as e:
            logger.error(f"❌ Error getting transactions: {e}")
            return self._get_fallback_transactions()

    def get_stores_data(self):
        """Get stores data from system nodes"""
        try:
            if not self.connected:
                return self._get_fallback_stores()

            # Get system nodes to understand store layout
            response = self.tables['system_nodes'].scan()
            nodes = response.get('Items', [])

            # Group by store_id
            stores = {}
            for node in nodes:
                store_id = node.get('store_id', 'store_001')
                if store_id not in stores:
                    stores[store_id] = {
                        'store_id': store_id,
                        'store_name': f'IoT Store {store_id[-3:].upper()}',
                        'location': 'Main Campus, Building A',
                        'status': 'ACTIVE',
                        'devices': {
                            'smart_carts': 0,
                            'door_access': 0,
                            'smart_shelves': 0
                        },
                        'daily_revenue': random.uniform(2000, 3000),
                        'customer_count': random.randint(80, 120)
                    }

                node_type = node.get('node_type', '')
                if 'cart' in node_type:
                    stores[store_id]['devices']['smart_carts'] += 1
                elif 'door' in node_type:
                    stores[store_id]['devices']['door_access'] += 1
                elif 'shelf' in node_type:
                    stores[store_id]['devices']['smart_shelves'] += 1

            store_list = list(stores.values())
            logger.info(f"🏪 Retrieved {len(store_list)} stores")
            return store_list
        except Exception as e:
            logger.error(f"❌ Error getting stores: {e}")
            return self._get_fallback_stores()

    def create_customer(self, customer_data):
        """Create new customer in DynamoDB"""
        try:
            if not self.connected:
                logger.warning(
                    "⚠️ DynamoDB not connected, cannot create customer")
                return False

            # Generate customer ID
            customer_id = f"cust_{uuid.uuid4().hex[:8]}"

            # Prepare customer record
            customer_record = {
                'customer_id': customer_id,
                'customer_name': customer_data.get('name', ''),
                'customer_type': customer_data.get('type', 'REGULAR'),
                'rfid_card_uid': customer_data.get('rfid_uid', ''),
                'email': customer_data.get('email', ''),
                'phone': customer_data.get('phone', ''),
                'total_spent': Decimal('0.0'),
                'total_visits': 0,
                'membership_status': 'ACTIVE',
                'created_at': datetime.utcnow().isoformat(),
                'last_visit': datetime.utcnow().isoformat()
            }

            self.tables['customers'].put_item(Item=customer_record)
            logger.info(f"✅ Created customer: {customer_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating customer: {e}")
            return False

    # Fallback methods for when DynamoDB is not available
    def _get_fallback_customers(self):
        return [
            {
                'customer_id': 'cust_001',
                'customer_name': 'John Doe (Fallback)',
                'customer_type': 'VIP',
                'rfid_card_uid': 'ABC123456789',
                'email': 'john.doe@fallback.edu',
                'phone': '+1234567890',
                'total_spent': 1250.75,
                'total_visits': 45,
                'membership_status': 'ACTIVE',
                'last_visit': '2024-05-31'
            }
        ]

    def _get_fallback_analytics(self):
        return {
            'total_customers': 3,
            'active_sessions': 1,
            'total_sales_today': 247.50,
            'fraud_alerts': 2,
            'daily_sales': [
                {'date': '2024-05-25', 'sales': 1680.25},
                {'date': '2024-05-26', 'sales': 1234.00},
                {'date': '2024-05-27', 'sales': 1890.30},
                {'date': '2024-05-28', 'sales': 2147.80},
                {'date': '2024-05-29', 'sales': 1847.50},
                {'date': '2024-05-30', 'sales': 2247.50},
                {'date': '2024-05-31', 'sales': 1847.50}
            ],
            'fraud_events': [
                {'type': 'unscanned_item', 'count': 5},
                {'type': 'weight_mismatch', 'count': 3}
            ]
        }

    def _get_fallback_transactions(self):
        return [
            {
                'transaction_id': 'txn_fallback_001',
                'customer_name': 'Customer 001',
                'amount': 45.67,
                'items': 3,
                'timestamp': '2024-05-31T15:30:00Z',
                'status': 'completed'
            }
        ]

    def _get_fallback_stores(self):
        return [{
            'store_id': 'store_001',
            'store_name': 'Main Campus Store (Fallback)',
            'location': 'Building A, Floor 1',
            'status': 'ACTIVE',
            'devices': {'smart_carts': 1, 'door_access': 1, 'smart_shelves': 1},
            'daily_revenue': 2847.50,
            'customer_count': 89
        }]


# Initialize DynamoDB client
db_client = DynamoDBClient()

# Routes


@app.route('/')
def dashboard():
    """Main dashboard"""
    try:
        analytics = db_client.get_analytics_data()
        recent_transactions = db_client.get_recent_transactions()
        return render_template('dashboard.html',
                               analytics=analytics,
                               recent_transactions=recent_transactions)
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/users')
def users():
    """User management"""
    try:
        customers = db_client.get_customers()
        return render_template('users.html', customers=customers)
    except Exception as e:
        logger.error(f"❌ Users page error: {e}")
        return f"Error loading users: {str(e)}", 500


@app.route('/analytics')
def analytics():
    """Analytics page"""
    try:
        analytics_data = db_client.get_analytics_data()
        return render_template('analytics.html', analytics=analytics_data)
    except Exception as e:
        logger.error(f"❌ Analytics error: {e}")
        return f"Error loading analytics: {str(e)}", 500


@app.route('/stores')
def stores():
    """Stores management"""
    try:
        stores_data = db_client.get_stores_data()
        return render_template('stores.html', stores=stores_data)
    except Exception as e:
        logger.error(f"❌ Stores error: {e}")
        return f"Error loading stores: {str(e)}", 500


@app.route('/register-card')
def register_card():
    """RFID card registration"""
    try:
        return render_template('register_card.html')
    except Exception as e:
        logger.error(f"❌ Register card page error: {e}")
        return f"Error loading register card: {str(e)}", 500

# API Routes


@app.route('/api/register-card', methods=['POST'])
def api_register_card():
    """Register new RFID card"""
    try:
        data = request.get_json()
        logger.info(f"🔄 Registering card for: {data.get('name', 'Unknown')}")

        # Generate RFID UID if not provided
        rfid_uid = data.get('rfid_uid') or ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=10))

        customer_data = {
            'name': data.get('name', ''),
            'type': data.get('type', 'REGULAR'),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'rfid_uid': rfid_uid
        }

        success = db_client.create_customer(customer_data)

        if success:
            logger.info(f"✅ Card registered successfully: {rfid_uid}")
            return jsonify({
                'success': True,
                'message': 'Card registered successfully!',
                'rfid_uid': rfid_uid
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error saving to database'
            }), 500

    except Exception as e:
        logger.error(f"❌ Register card error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/simulate-rfid-scan')
def simulate_rfid_scan():
    """Simulate RFID card scan"""
    try:
        rfid_uid = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=10))
        logger.info(f"📡 Simulated RFID scan: {rfid_uid}")

        return jsonify({
            'rfid_uid': rfid_uid,
            'scan_time': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ RFID scan simulation error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/status')
def api_status():
    """System status API"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'aws_region': app.config['AWS_REGION'],
        'database_connected': db_client.connected,
        'tables_configured': len(db_client.tables) if db_client.connected else 0,
        'version': '2.1.0',
        'tables': list(db_client.tables.keys()) if db_client.connected else []
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if db_client.connected else 'disconnected'
    })


@app.route('/api/customers')
def api_customers():
    """API endpoint for customers data"""
    try:
        customers = db_client.get_customers()
        return jsonify({
            'customers': customers,
            'count': len(customers)
        })
    except Exception as e:
        logger.error(f"❌ API customers error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info("🚀 Starting IoT Store Admin UI...")
    logger.info(f"📍 Port: {port}")
    logger.info(f"🗄️ Database Connected: {db_client.connected}")
    logger.info(f"🌍 AWS Region: {app.config['AWS_REGION']}")
    logger.info(f"🔧 Debug Mode: {debug_mode}")
    logger.info(
        f"📊 Tables: {list(app.config.keys()) if hasattr(app.config, 'keys') else 'Config loading...'}")

    if debug_mode:
        logger.info("📍 Development mode - Access at: http://127.0.0.1:5000")
        app.run(debug=True, host='127.0.0.1', port=port)
    else:
        logger.info("📍 Production mode - binding to 0.0.0.0")
        app.run(debug=False, host='0.0.0.0', port=port)
