#!/usr/bin/env python3
"""
Enhanced IoT Store Admin & Customer Portal
Complete system management and customer self-service
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
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
from functools import wraps
import traceback

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Add custom Jinja2 filters


@app.template_filter('strftime')
def strftime_filter(datetime_str, format='%H:%M:%S'):
    """Custom filter to format current time"""
    try:
        if datetime_str == 'now':
            return datetime.now().strftime(format)
        else:
            # If it's an actual datetime string, parse and format it
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime(format)
    except:
        return datetime.now().strftime(format)


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'iot-store-secret-key-prod-change-this')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

    # DynamoDB Table Names - Enhanced
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
    SYSTEM_NODES_TABLE = os.environ.get(
        'SYSTEM_NODES_TABLE', 'iot-convenience-store-system-nodes-production')
    ACTIVE_SESSIONS_TABLE = os.environ.get(
        'ACTIVE_SESSIONS_TABLE', 'iot-convenience-store-active-sessions-production')
    CUSTOMER_PROFILES_TABLE = os.environ.get(
        'CUSTOMER_PROFILES_TABLE', 'iot-convenience-store-customer-profiles-production')
    CUSTOMER_CLUSTERS_TABLE = os.environ.get(
        'CUSTOMER_CLUSTERS_TABLE', 'iot-convenience-store-customer-clusters-production')
    DISCOUNT_EFFECTIVENESS_TABLE = os.environ.get(
        'DISCOUNT_EFFECTIVENESS_TABLE', 'iot-convenience-store-discount-effectiveness-production')
    PURCHASE_BEHAVIOR_TABLE = os.environ.get(
        'PURCHASE_BEHAVIOR_TABLE', 'iot-convenience-store-purchase-behavior-production')


app.config.from_object(Config)


class EnhancedDynamoDBClient:
    def __init__(self):
        try:
            logger.info("Initializing DynamoDB client...")

            # Check AWS credentials
            if not os.environ.get('AWS_ACCESS_KEY_ID'):
                logger.warning("AWS_ACCESS_KEY_ID not found in environment")
            if not os.environ.get('AWS_SECRET_ACCESS_KEY'):
                logger.warning(
                    "AWS_SECRET_ACCESS_KEY not found in environment")

            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=app.config['AWS_REGION'],
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
            )

            self.iot_client = boto3.client(
                'iot-data',
                region_name=app.config['AWS_REGION'],
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
            )

            # Initialize tables with error handling
            self.tables = {}
            table_configs = {
                'customers': app.config['CUSTOMERS_TABLE'],
                'products': app.config['PRODUCTS_TABLE'],
                'sessions': app.config['SESSIONS_TABLE'],
                'transactions': app.config['TRANSACTIONS_TABLE'],
                'fraud_events': app.config['FRAUD_EVENTS_TABLE'],
                'access_logs': app.config['ACCESS_LOGS_TABLE'],
                'system_nodes': app.config['SYSTEM_NODES_TABLE'],
                'active_sessions': app.config['ACTIVE_SESSIONS_TABLE'],
                'customer_profiles': app.config['CUSTOMER_PROFILES_TABLE'],
                'customer_clusters': app.config['CUSTOMER_CLUSTERS_TABLE'],
                'discount_effectiveness': app.config['DISCOUNT_EFFECTIVENESS_TABLE'],
                'purchase_behavior': app.config['PURCHASE_BEHAVIOR_TABLE']
            }

            for table_name, table_config in table_configs.items():
                try:
                    table = self.dynamodb.Table(table_config)
                    # Test table access
                    table.load()
                    self.tables[table_name] = table
                    logger.info(
                        f"✅ Successfully connected to table: {table_config}")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not connect to table {table_config}: {e}")
                    self.tables[table_name] = None

            self.connected = True
            logger.info(
                f"✅ DynamoDB client initialized in {app.config['AWS_REGION']}")

        except Exception as e:
            logger.error(f"❌ DynamoDB connection error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.connected = False
            self.tables = {}

    def safe_table_operation(self, table_name, operation, default_value=None):
        """Safely perform table operations with error handling"""
        try:
            if not self.tables.get(table_name):
                logger.warning(f"Table {table_name} not available")
                return default_value

            return operation()
        except Exception as e:
            logger.error(f"Error in {table_name} operation: {e}")
            return default_value

    def get_real_time_dashboard_data(self):
        """Get comprehensive real-time dashboard data with robust error handling"""
        logger.info("Getting real-time dashboard data...")

        try:
            # Initialize with safe defaults
            dashboard_data = {
                'active_sessions': [],
                'active_customers': 0,
                'total_sales_today': 0.0,
                'recent_transactions': [],
                'fraud_events': [],
                'fraud_count': 0,
                'system_nodes': [],
                'online_devices': 0,
                'total_devices': 0,
                'system_health': 100.0
            }

            # Active Sessions - with safe operation
            def get_active_sessions():
                response = self.tables['active_sessions'].scan(Limit=10)
                return response.get('Items', [])

            active_sessions = self.safe_table_operation(
                'active_sessions',
                get_active_sessions,
                []
            )

            # Recent Transactions
            def get_recent_transactions():
                response = self.tables['transactions'].scan(Limit=10)
                return response.get('Items', [])

            recent_transactions = self.safe_table_operation(
                'transactions',
                get_recent_transactions,
                []
            )

            # Fraud Events
            def get_fraud_events():
                response = self.tables['fraud_events'].scan(Limit=10)
                return response.get('Items', [])

            fraud_events = self.safe_table_operation(
                'fraud_events',
                get_fraud_events,
                []
            )

            # System Nodes
            def get_system_nodes():
                response = self.tables['system_nodes'].scan()
                return response.get('Items', [])

            system_nodes = self.safe_table_operation(
                'system_nodes',
                get_system_nodes,
                []
            )

            # Calculate metrics safely
            total_sales_today = 0.0
            try:
                for transaction in recent_transactions:
                    amount = transaction.get('total_amount', 0)
                    if isinstance(amount, Decimal):
                        total_sales_today += float(amount)
                    elif isinstance(amount, (int, float)):
                        total_sales_today += amount
            except Exception as e:
                logger.warning(f"Error calculating sales: {e}")
                total_sales_today = 0.0

            # Count metrics
            active_customers = len(active_sessions)
            online_devices = len(
                [n for n in system_nodes if n.get('is_online', False)])
            total_devices = len(system_nodes) if system_nodes else 1
            system_health = round(
                (online_devices / total_devices * 100), 1) if total_devices > 0 else 100.0

            # Format active sessions with duration
            for session in active_sessions:
                try:
                    if session.get('entry_time'):
                        entry_time = datetime.fromisoformat(
                            session['entry_time'].replace('Z', '+00:00'))
                        duration = datetime.utcnow() - entry_time.replace(tzinfo=None)
                        session['duration'] = f"{duration.seconds // 60}m"
                    else:
                        session['duration'] = "0m"
                except Exception as e:
                    logger.warning(f"Error calculating session duration: {e}")
                    session['duration'] = "0m"

            # Update dashboard data
            dashboard_data.update({
                'active_sessions': active_sessions,
                'active_customers': active_customers,
                'total_sales_today': total_sales_today,
                'recent_transactions': recent_transactions,
                'fraud_events': fraud_events,
                'fraud_count': len(fraud_events),
                'system_nodes': system_nodes,
                'online_devices': online_devices,
                'total_devices': total_devices,
                'system_health': system_health
            })

            logger.info(
                f"Dashboard data compiled successfully: {active_customers} active customers, ${total_sales_today:.2f} sales")
            return dashboard_data

        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._get_fallback_dashboard()

    def get_customers(self):
        """Get all customers with enhanced error handling"""
        def get_customers_operation():
            response = self.tables['customers'].scan()
            customers = response.get('Items', [])

            # Convert Decimal to float for JSON serialization
            formatted_customers = []
            for customer in customers:
                formatted_customer = {}
                for key, value in customer.items():
                    if isinstance(value, Decimal):
                        formatted_customer[key] = float(value)
                    else:
                        formatted_customer[key] = value
                formatted_customers.append(formatted_customer)

            return formatted_customers

        return self.safe_table_operation('customers', get_customers_operation, [])

    def get_enhanced_customer_analytics(self):
        """Get detailed customer analytics with AI insights"""
        try:
            # Customer Profiles
            try:
                profiles_response = self.tables['customer_profiles'].scan()
                customer_profiles = profiles_response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get customer profiles: {e}")
                customer_profiles = []

            # Customer Clusters
            try:
                clusters_response = self.tables['customer_clusters'].scan()
                customer_clusters = clusters_response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get customer clusters: {e}")
                customer_clusters = []

            # Purchase Behavior
            try:
                behavior_response = self.tables['purchase_behavior'].scan()
                purchase_behaviors = behavior_response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get purchase behaviors: {e}")
                purchase_behaviors = []

            # Discount Effectiveness
            try:
                discount_response = self.tables['discount_effectiveness'].scan(
                )
                discount_data = discount_response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get discount data: {e}")
                discount_data = []

            return {
                'customer_profiles': customer_profiles,
                'customer_clusters': customer_clusters,
                'purchase_behaviors': purchase_behaviors,
                'discount_effectiveness': discount_data,
                'cluster_count': len(customer_clusters),
                'profiled_customers': len(customer_profiles),
                'total_sales_today': 0  # Add this for analytics template
            }

        except Exception as e:
            logger.error(f"Error getting customer analytics: {e}")
            return {
                'customer_profiles': [],
                'customer_clusters': [],
                'purchase_behaviors': [],
                'discount_effectiveness': [],
                'cluster_count': 0,
                'profiled_customers': 0,
                'total_sales_today': 0
            }

    def get_fraud_monitoring_data(self):
        """Get comprehensive fraud monitoring data"""
        try:
            fraud_response = self.tables['fraud_events'].scan()
            fraud_events = fraud_response.get('Items', [])

            # Sort by timestamp
            fraud_events.sort(key=lambda x: x.get(
                'timestamp', ''), reverse=True)

            # Categorize by severity and type
            fraud_by_type = {}
            fraud_by_severity = {}

            for event in fraud_events:
                event_type = event.get('fraud_type', 'unknown')
                severity = event.get('severity', 'medium')

                fraud_by_type[event_type] = fraud_by_type.get(
                    event_type, 0) + 1
                fraud_by_severity[severity] = fraud_by_severity.get(
                    severity, 0) + 1

                # Format for display
                event['event_type'] = event_type.replace('_', ' ').title()
                event['auto_resolved'] = False

            return {
                'events': fraud_events,
                'fraud_by_type': fraud_by_type,
                'fraud_by_severity': fraud_by_severity,
                'total_events': len(fraud_events),
                'high_severity': fraud_by_severity.get('high', 0) + fraud_by_severity.get('critical', 0)
            }

        except Exception as e:
            logger.error(f"Error getting fraud data: {e}")
            return {'events': [], 'fraud_by_type': {}, 'fraud_by_severity': {}, 'total_events': 0, 'high_severity': 0}

    def get_inventory_data(self):
        """Get inventory and product data"""
        try:
            products_response = self.tables['products'].scan()
            products = products_response.get('Items', [])

            formatted_products = []
            for product in products:
                formatted_products.append({
                    'product_id': product.get('product_id', ''),
                    'product_name': product.get('product_name', ''),
                    'category': product.get('category', ''),
                    'regular_price': float(product.get('regular_price', 0)),
                    'current_price': float(product.get('current_price', 0)),
                    'vip_price': float(product.get('vip_price', 0)),
                    'inventory_level': product.get('inventory_level', 0),
                    'reorder_threshold': product.get('reorder_threshold', 0),
                    'is_active': product.get('is_active', True),
                    'is_premium': product.get('is_premium', False),
                    'product_rfid': product.get('product_rfid', ''),
                    'description': product.get('description', ''),
                    'weight_per_unit': product.get('weight_per_unit', 0),
                    'discount_eligible': product.get('discount_eligible', True),
                    'needs_reorder': product.get('inventory_level', 0) <= product.get('reorder_threshold', 0)
                })

            return formatted_products

        except Exception as e:
            logger.error(f"Error getting inventory data: {e}")
            return []

    def get_system_monitoring_data(self):
        """Get detailed system monitoring data"""
        try:
            nodes_response = self.tables['system_nodes'].scan()
            system_nodes = nodes_response.get('Items', [])

            try:
                sessions_response = self.tables['active_sessions'].scan()
                active_sessions = sessions_response.get('Items', [])
            except Exception as e:
                logger.warning(
                    f"Could not get active sessions for monitoring: {e}")
                active_sessions = []

            # Add session info to nodes
            session_by_cart = {s.get('assigned_cart')                               : s for s in active_sessions}

            for node in system_nodes:
                node_id = node.get('node_id', '')
                if node_id in session_by_cart:
                    session = session_by_cart[node_id]
                    node['current_session_id'] = session.get('session_id', '')
                    node['current_customer'] = session.get('customer_name', '')
                    node['total_sessions_today'] = 1

            return {
                'nodes': system_nodes,
                'active_sessions': active_sessions,
                'device_utilization': len(active_sessions)
            }

        except Exception as e:
            logger.error(f"Error getting system monitoring data: {e}")
            return {'nodes': [], 'active_sessions': [], 'device_utilization': 0}

    def assign_rfid_to_customer(self, customer_id, rfid_uid):
        """Assign RFID card to customer (admin function)"""
        try:
            self.tables['customers'].update_item(
                Key={'customer_id': customer_id},
                UpdateExpression='SET rfid_card_uid = :rfid, membership_status = :status, updated_at = :updated',
                ExpressionAttributeValues={
                    ':rfid': rfid_uid,
                    ':status': 'ACTIVE',
                    ':updated': datetime.utcnow().isoformat()
                }
            )
            logger.info(
                f"✅ Assigned RFID {rfid_uid} to customer {customer_id}")
            return True
        except Exception as e:
            logger.error(f"Error assigning RFID: {e}")
            return False

    def send_device_command(self, device_id, command):
        """Send command to IoT device"""
        try:
            topic = f'store/devices/{device_id}/commands'
            message = {
                'command': command,
                'timestamp': datetime.utcnow().isoformat(),
                'sent_by': 'admin_ui'
            }

            self.iot_client.publish(
                topic=topic,
                qos=1,
                payload=json.dumps(message)
            )
            logger.info(f"✅ Sent {command} to {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending device command: {e}")
            return False

    def _get_fallback_dashboard(self):
        """Fallback dashboard data when database is unavailable"""
        logger.warning("Using fallback dashboard data")
        return {
            'active_sessions': [],
            'active_customers': 0,
            'total_sales_today': 0.0,
            'recent_transactions': [],
            'fraud_events': [],
            'fraud_count': 0,
            'system_nodes': [],
            'online_devices': 0,
            'total_devices': 1,
            'system_health': 100.0
        }


# Initialize enhanced client
db_client = EnhancedDynamoDBClient()

# Authentication decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            logger.warning(
                f"Unauthorized access attempt to {request.endpoint}")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# === ADMIN ROUTES ===


@app.route('/')
def index():
    """Root route - redirect to admin login"""
    return redirect(url_for('admin_login'))


@app.route('/admin')
def admin_redirect():
    """Admin route - redirect to dashboard if logged in, otherwise login"""
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))


@app.route('/admin/login')
def admin_login():
    """Admin login page"""
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    """Process admin login"""
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        logger.info(f"Login attempt for user: {username}")

        # Simple auth - replace with proper authentication
        if username == 'admin' and password == 'admin123':
            session['is_admin'] = True
            session['admin_user'] = username
            logger.info(f"Successful login for user: {username}")
            flash('Welcome to IoT Store Admin Portal', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            logger.warning(f"Failed login attempt for user: {username}")
            flash('Invalid credentials', 'error')
            return redirect(url_for('admin_login'))
    except Exception as e:
        logger.error(f"Login error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Login error occurred', 'error')
        return redirect(url_for('admin_login'))


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    user = session.get('admin_user', 'Unknown')
    session.clear()
    logger.info(f"User {user} logged out")
    flash('Logged out successfully', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Enhanced admin dashboard with comprehensive error handling"""
    try:
        logger.info("Loading admin dashboard...")

        # Check database connection
        if not db_client.connected:
            logger.error("Database not connected - using fallback data")
            flash('Database connection unavailable - showing limited data', 'warning')
            dashboard_data = db_client._get_fallback_dashboard()
        else:
            dashboard_data = db_client.get_real_time_dashboard_data()

        logger.info("Dashboard data loaded successfully")
        return render_template('admin/dashboard.html', data=dashboard_data)

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error loading dashboard data - showing fallback view', 'error')

        # Return with fallback data
        fallback_data = db_client._get_fallback_dashboard()
        return render_template('admin/dashboard.html', data=fallback_data)


@app.route('/admin/customers')
@admin_required
def admin_customers():
    """Enhanced customer management with analytics data"""
    try:
        # Get customers data
        customers = db_client.get_customers()

        # Get analytics data for the template
        analytics_data = db_client.get_enhanced_customer_analytics()

        # Add default values if analytics data is missing
        if not analytics_data:
            analytics_data = {
                'profiled_customers': 0,
                'customer_clusters': [],
                'customer_profiles': [],
                'cluster_count': 0
            }

        logger.info(
            f"Loading customers page with {len(customers)} customers and {analytics_data.get('profiled_customers', 0)} profiles")

        return render_template('admin/customers.html',
                               customers=customers,
                               analytics=analytics_data)

    except Exception as e:
        logger.error(f"Customers error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error loading customer data', 'error')

        # Return with minimal data to prevent template errors
        return render_template('admin/customers.html',
                               customers=[],
                               analytics={
                                   'profiled_customers': 0,
                                   'customer_clusters': [],
                                   'customer_profiles': [],
                                   'cluster_count': 0
                               })

@app.route('/admin/fraud')
@admin_required
def admin_fraud():
    """Fraud monitoring dashboard"""
    try:
        fraud_data = db_client.get_fraud_monitoring_data()
        return render_template('admin/fraud_events.html', **fraud_data)
    except Exception as e:
        logger.error(f"Fraud monitoring error: {e}")
        flash('Error loading fraud data', 'error')
        return render_template('admin/fraud_events.html', events=[])


@app.route('/admin/inventory')
@admin_required
def admin_inventory():
    """Inventory management with enhanced error handling"""
    try:
        logger.info("Loading inventory page...")

        # Get inventory data with safe operation
        def get_products_operation():
            response = db_client.tables['products'].scan()
            products = response.get('Items', [])

            # Format products for template
            formatted_products = []
            for product in products:
                formatted_product = {}

                # Convert all fields safely
                for key, value in product.items():
                    if isinstance(value, Decimal):
                        formatted_product[key] = float(value)
                    else:
                        formatted_product[key] = value

                # Ensure all required fields exist with defaults
                required_fields = {
                    'product_id': formatted_product.get('product_id', ''),
                    'product_name': formatted_product.get('product_name', 'Unknown Product'),
                    'category': formatted_product.get('category', 'General'),
                    'regular_price': formatted_product.get('regular_price', 0.0),
                    'current_price': formatted_product.get('current_price', 0.0),
                    'vip_price': formatted_product.get('vip_price', 0.0),
                    'inventory_level': formatted_product.get('inventory_level', 0),
                    'reorder_threshold': formatted_product.get('reorder_threshold', 10),
                    'is_active': formatted_product.get('is_active', True),
                    'is_premium': formatted_product.get('is_premium', False),
                    'product_rfid': formatted_product.get('product_rfid', ''),
                    'description': formatted_product.get('description', ''),
                    'weight_per_unit': formatted_product.get('weight_per_unit', 0.0),
                    'discount_eligible': formatted_product.get('discount_eligible', True)
                }

                # Add calculated fields
                required_fields['needs_reorder'] = required_fields['inventory_level'] <= required_fields['reorder_threshold']

                formatted_products.append(required_fields)

            return formatted_products

        products = db_client.safe_table_operation(
            'products', get_products_operation, [])

        logger.info(f"Loaded {len(products)} products for inventory page")
        return render_template('admin/inventory.html', products=products)

    except Exception as e:
        logger.error(f"Inventory error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error loading inventory data', 'error')

        # Return with empty products list to prevent template errors
        return render_template('admin/inventory.html', products=[])


@app.route('/admin/system')
@admin_required
def admin_system():
    """System monitoring"""
    try:
        system_data = db_client.get_system_monitoring_data()
        return render_template('admin/system_status.html', **system_data)
    except Exception as e:
        logger.error(f"System monitoring error: {e}")
        flash('Error loading system data', 'error')
        return render_template('admin/system_status.html', nodes=[])


@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Advanced analytics"""
    try:
        analytics_data = db_client.get_enhanced_customer_analytics()
        dashboard_data = db_client.get_real_time_dashboard_data()
        combined_data = {**analytics_data, **dashboard_data}
        return render_template('admin/analytics.html', analytics=combined_data)
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        flash('Error loading analytics data', 'error')
        return render_template('admin/analytics.html', analytics={'total_sales_today': 0, 'customer_profiles': [], 'customer_clusters': [], 'discount_effectiveness': []})


@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    """Transaction management"""
    try:
        # Get recent transactions
        transactions_response = db_client.tables['transactions'].scan()
        transactions = transactions_response.get('Items', [])

        # Sort by timestamp
        transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return render_template('admin/transactions.html', transactions=transactions)
    except Exception as e:
        logger.error(f"Transactions error: {e}")
        flash('Error loading transaction data', 'error')
        return render_template('admin/transactions.html', transactions=[])


@app.route('/admin/register-card')
@admin_required
def admin_register_card():
    """RFID card registration"""
    try:
        # Get pending customers (those without RFID cards)
        customers_response = db_client.tables['customers'].scan()
        all_customers = customers_response.get('Items', [])

        # Filter for pending customers
        pending_customers = []
        for customer in all_customers:
            if not customer.get('rfid_card_uid') or customer.get('membership_status') == 'PENDING':
                pending_customers.append(customer)

        return render_template('admin/register_card.html', pending_customers=pending_customers)
    except Exception as e:
        logger.error(f"Register card error: {e}")
        flash('Error loading registration page', 'error')
        return render_template('admin/register_card.html', pending_customers=[])

# === API ROUTES ===


@app.route('/api/admin/assign-rfid', methods=['POST'])
@admin_required
def api_assign_rfid():
    """Assign RFID card to customer"""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        rfid_uid = data.get('rfid_uid')

        success = db_client.assign_rfid_to_customer(customer_id, rfid_uid)

        return jsonify({
            'success': success,
            'message': 'RFID assigned successfully' if success else 'Failed to assign RFID'
        })

    except Exception as e:
        logger.error(f"RFID assignment error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/device-command', methods=['POST'])
@admin_required
def api_device_command():
    """Send command to IoT device"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        command = data.get('command')

        success = db_client.send_device_command(device_id, command)

        return jsonify({
            'success': success,
            'message': f'Command {command} sent to {device_id}' if success else 'Failed to send command'
        })

    except Exception as e:
        logger.error(f"Device command error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/simulate-rfid-scan')
def simulate_rfid_scan():
    """Simulate RFID card scan"""
    try:
        rfid_uid = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=10))
        return jsonify({
            'rfid_uid': rfid_uid,
            'scan_time': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"RFID simulation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/dashboard/realtime')
def api_dashboard_realtime():
    """Get real-time dashboard data"""
    try:
        data = db_client.get_real_time_dashboard_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Real-time API error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health_check():
    """Enhanced health check endpoint"""
    try:
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected' if db_client.connected else 'disconnected',
            'aws_region': app.config['AWS_REGION'],
            'tables_available': len([t for t in db_client.tables.values() if t is not None])
        }

        # Test a simple database operation
        if db_client.connected and db_client.tables.get('customers'):
            try:
                db_client.tables['customers'].load()
                health_data['database_test'] = 'passed'
            except Exception as e:
                health_data['database_test'] = f'failed: {str(e)}'

        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Error handlers


@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return render_template('admin/login.html'), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info("🚀 Starting Enhanced IoT Store Admin Portal...")
    logger.info(f"📍 Port: {port}")
    logger.info(f"🗄️ Database Connected: {db_client.connected}")
    logger.info(f"🌍 AWS Region: {app.config['AWS_REGION']}")
    logger.info(
        f"📊 Tables Available: {len([t for t in db_client.tables.values() if t is not None])}")

    if debug_mode:
        app.run(debug=True, host='127.0.0.1', port=port)
    else:
        app.run(debug=False, host='0.0.0.0', port=port)
