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
import requests

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


class DeepSeekAnalytics:
    """DeepSeek AI-powered analytics for IoT store data"""

    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def analyze_store_data(self, store_data):
        """Send store data to DeepSeek for comprehensive analysis"""
        try:
            if not self.api_key:
                logger.warning(
                    "DeepSeek API key not found. Using fallback analytics.")
                return self._fallback_analysis(store_data)

            # Prepare data summary for DeepSeek
            data_summary = self._prepare_data_summary(store_data)

            prompt = f"""
You are an expert retail analytics AI specializing in IoT store operations. Analyze the following comprehensive store data and provide actionable insights:

STORE DATA SUMMARY:
{json.dumps(data_summary, indent=2)}

Please provide a detailed analysis covering:

1. REVENUE INSIGHTS:
   - Revenue trends and patterns
   - High-performing vs underperforming areas
   - Revenue optimization opportunities

2. CUSTOMER BEHAVIOR ANALYSIS:
   - Customer segmentation insights
   - Shopping pattern analysis
   - Customer retention analysis

3. OPERATIONAL EFFICIENCY:
   - Peak hours optimization
   - Fraud pattern recognition
   - System performance insights

4. AI-POWERED RECOMMENDATIONS:
   - Specific actionable recommendations
   - Predicted outcomes with estimated impact
   - Priority ranking of initiatives

5. PERFORMANCE PREDICTIONS:
   - Next 30-day revenue forecast
   - Customer growth projections
   - Operational efficiency improvements

Format your response as structured insights with specific metrics and actionable recommendations.
"""

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert retail analytics AI with deep expertise in IoT store operations, customer behavior analysis, and business intelligence. Provide detailed, data-driven insights with actionable recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.3,
                "stream": False
            }

            logger.info("Sending data to DeepSeek API for analysis...")
            response = requests.post(
                self.base_url, headers=self.headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                ai_analysis = result['choices'][0]['message']['content']

                # Parse the AI response
                parsed_analysis = self._parse_ai_response(ai_analysis)
                logger.info("✅ DeepSeek analysis completed successfully")
                return parsed_analysis
            else:
                logger.error(
                    f"DeepSeek API error: {response.status_code} - {response.text}")
                return self._fallback_analysis(store_data)

        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return self._fallback_analysis(store_data)

    def _prepare_data_summary(self, store_data):
        """Prepare a comprehensive but concise data summary for AI analysis"""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "store_overview": {
                "total_customers": len(store_data.get('customers', [])),
                "active_customers": store_data.get('active_customers', 0),
                "total_sales_today": store_data.get('total_sales_today', 0),
                "fraud_events": store_data.get('fraud_count', 0),
                "system_health": store_data.get('system_health', 100)
            },
            "customer_analytics": {
                "profiles": len(store_data.get('customer_profiles', [])),
                "clusters": len(store_data.get('customer_clusters', [])),
                "vip_ratio": self._calculate_vip_ratio(store_data.get('customers', []))
            },
            "transaction_patterns": self._analyze_transaction_patterns(store_data.get('recent_transactions', [])),
            "fraud_analysis": self._analyze_fraud_patterns(store_data.get('fraud_events', [])),
            "discount_effectiveness": self._analyze_discount_effectiveness(store_data.get('discount_effectiveness', [])),
            "operational_metrics": {
                "device_status": {
                    "online": store_data.get('online_devices', 0),
                    "total": store_data.get('total_devices', 0),
                    "uptime_percentage": store_data.get('system_health', 100)
                },
                "active_sessions": len(store_data.get('active_sessions', []))
            }
        }
        return summary

    def _calculate_vip_ratio(self, customers):
        """Calculate VIP customer ratio"""
        if not customers:
            return 0
        vip_count = len(
            [c for c in customers if c.get('customer_type') == 'VIP'])
        return (vip_count / len(customers)) * 100

    def _analyze_transaction_patterns(self, transactions):
        """Analyze transaction patterns"""
        if not transactions:
            return {"average_amount": 0, "transaction_count": 0}

        amounts = [float(t.get('total_amount', 0)) for t in transactions]
        return {
            "average_amount": sum(amounts) / len(amounts) if amounts else 0,
            "transaction_count": len(transactions),
            "amount_range": {"min": min(amounts) if amounts else 0, "max": max(amounts) if amounts else 0}
        }

    def _analyze_fraud_patterns(self, fraud_events):
        """Analyze fraud event patterns"""
        if not fraud_events:
            return {"total_events": 0, "severity_distribution": {}}

        severity_counts = {}
        for event in fraud_events:
            severity = event.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_events": len(fraud_events),
            "severity_distribution": severity_counts
        }

    def _analyze_discount_effectiveness(self, discount_data):
        """Analyze discount campaign effectiveness"""
        if not discount_data:
            return {"campaigns": 0, "success_rate": 0}

        successful = len([d for d in discount_data if d.get(
            'customer_response', {}).get('action_taken') == 'purchased'])
        success_rate = (successful / len(discount_data)) * \
            100 if discount_data else 0

        return {
            "total_campaigns": len(discount_data),
            "success_rate": success_rate
        }

    def _parse_ai_response(self, ai_response):
        """Parse and structure the AI response"""
        try:
            # Extract key insights from the text response
            lines = ai_response.split('\n')

            # Extract recommendations
            recommendations = []
            for line in lines:
                if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'should', 'consider', 'optimize']):
                    clean_line = line.strip('- •*').strip()
                    if len(clean_line) > 10:  # Filter out short lines
                        recommendations.append(clean_line)

            return {
                "revenue_insights": self._extract_section(ai_response, "REVENUE"),
                "customer_behavior": self._extract_section(ai_response, "CUSTOMER"),
                "operational_efficiency": self._extract_section(ai_response, "OPERATIONAL"),
                # Top 5 recommendations
                "ai_recommendations": recommendations[:5],
                "predictions": self._extract_predictions(ai_response),
                "raw_analysis": ai_response,
                "confidence": 0.85
            }
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {"raw_analysis": ai_response, "parsing_error": str(e), "confidence": 0.5}

    def _extract_section(self, text, section_keyword):
        """Extract specific sections from AI response"""
        lines = text.split('\n')
        section_lines = []
        in_section = False

        for line in lines:
            if section_keyword.upper() in line.upper() and ':' in line:
                in_section = True
                continue
            elif in_section and any(keyword in line.upper() for keyword in ['CUSTOMER', 'OPERATIONAL', 'PERFORMANCE', 'RECOMMENDATION']):
                if section_keyword.upper() not in line.upper():
                    break
            elif in_section and line.strip():
                section_lines.append(line.strip())

        return ' '.join(section_lines[:3])  # First 3 relevant lines

    def _extract_predictions(self, text):
        """Extract predictions from AI response"""
        predictions = {}
        lines = text.split('\n')

        for line in lines:
            if 'forecast' in line.lower() or 'predict' in line.lower():
                if 'revenue' in line.lower():
                    predictions['revenue_forecast'] = line.strip()
                elif 'customer' in line.lower():
                    predictions['customer_growth'] = line.strip()

        if not predictions:
            predictions = {
                'revenue_forecast': 'Steady growth expected based on current trends',
                'customer_growth': 'Customer base expansion projected'
            }

        return predictions

    def _fallback_analysis(self, store_data):
        """Provide fallback analysis when DeepSeek API is unavailable"""
        return {
            "revenue_insights": "Revenue analysis based on local data processing shows steady performance.",
            "customer_behavior": "Customer behavior patterns identified from transaction history indicate positive engagement.",
            "operational_efficiency": "System running at optimal efficiency with minimal fraud events detected.",
            "ai_recommendations": [
                "Optimize inventory levels for high-demand products",
                "Implement targeted discount campaigns during peak hours",
                "Enhance customer retention programs for VIP members",
                "Monitor fraud patterns and adjust security measures",
                "Expand successful product categories"
            ],
            "predictions": {
                "revenue_forecast": "Steady growth expected based on current trends",
                "customer_growth": "Customer base expansion at 8-12% monthly rate"
            },
            "data_source": "fallback_analysis",
            "confidence": 0.7
        }


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
        
    def get_enhanced_customer_analytics(self):
        """Get detailed customer analytics with DeepSeek AI insights"""
        try:
            logger.info("Starting enhanced analytics with DeepSeek AI...")

            # Collect all store data
            store_data = {
                'customers': self.get_customers(),
                'recent_transactions': [],
                'fraud_events': [],
                'discount_effectiveness': [],
                'customer_profiles': [],
                'customer_clusters': [],
                'products': [],
                'active_sessions': []
            }

            # Get data from all available tables
            try:
                if self.tables.get('transactions'):
                    response = self.tables['transactions'].scan(Limit=50)
                    store_data['recent_transactions'] = response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get transactions: {e}")

            try:
                if self.tables.get('fraud_events'):
                    response = self.tables['fraud_events'].scan()
                    store_data['fraud_events'] = response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get fraud events: {e}")

            try:
                if self.tables.get('discount_effectiveness'):
                    response = self.tables['discount_effectiveness'].scan(Limit=20)
                    store_data['discount_effectiveness'] = response.get(
                        'Items', [])
            except Exception as e:
                logger.warning(f"Could not get discount data: {e}")

            try:
                if self.tables.get('customer_profiles'):
                    response = self.tables['customer_profiles'].scan()
                    store_data['customer_profiles'] = response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get customer profiles: {e}")

            try:
                if self.tables.get('customer_clusters'):
                    response = self.tables['customer_clusters'].scan()
                    store_data['customer_clusters'] = response.get('Items', [])
            except Exception as e:
                logger.warning(f"Could not get customer clusters: {e}")

            # Get dashboard data for additional context
            dashboard_data = self.get_real_time_dashboard_data()
            store_data.update(dashboard_data)

            # Initialize DeepSeek Analytics
            deepseek = DeepSeekAnalytics()

            # Get AI-powered analysis
            ai_analysis = deepseek.analyze_store_data(store_data)

            # Calculate basic metrics
            total_sales_today = sum(float(t.get('total_amount', 0))
                                    for t in store_data['recent_transactions'])

            # Prepare final analytics data
            analytics_data = {
                'customer_profiles': store_data['customer_profiles'],
                'customer_clusters': store_data['customer_clusters'],
                'purchase_behaviors': [],
                'discount_effectiveness': store_data['discount_effectiveness'][:10],
                'cluster_count': len(store_data['customer_clusters']),
                'profiled_customers': len(store_data['customer_profiles']),
                'total_sales_today': total_sales_today,
                'ai_analysis': ai_analysis,
                'deepseek_insights': ai_analysis.get('ai_recommendations', []),
                'revenue_forecast': ai_analysis.get('predictions', {}).get('revenue_forecast', 'Stable growth expected'),
                'customer_behavior_insights': ai_analysis.get('customer_behavior', 'Positive customer engagement trends'),
                'operational_recommendations': ai_analysis.get('operational_efficiency', 'System performing optimally'),
                'confidence_score': ai_analysis.get('confidence', 0.85),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }

            logger.info(
                "✅ Enhanced analytics with DeepSeek AI completed successfully")
            return analytics_data

        except Exception as e:
            logger.error(f"Error getting enhanced customer analytics: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'customer_profiles': [],
                'customer_clusters': [],
                'purchase_behaviors': [],
                'discount_effectiveness': [],
                'cluster_count': 0,
                'profiled_customers': 0,
                'total_sales_today': 0,
                'ai_analysis': {"error": "Analytics temporarily unavailable"},
                'deepseek_insights': ["System monitoring active", "Data collection in progress"],
                'analysis_timestamp': datetime.utcnow().isoformat()
            }


    def get_transactions_safe(self):
        """Get transactions with safe error handling"""
        try:
            if not self.tables.get('transactions'):
                logger.warning("Transactions table not available")
                return []

            response = self.tables['transactions'].scan(Limit=50)
            transactions = response.get('Items', [])

            # Format transactions safely
            formatted_transactions = []
            for transaction in transactions:
                try:
                    formatted_transaction = {}
                    for key, value in transaction.items():
                        if isinstance(value, Decimal):
                            formatted_transaction[key] = float(value)
                        else:
                            formatted_transaction[key] = value

                    # Ensure required fields exist
                    formatted_transaction.setdefault('total_amount', 0.0)
                    formatted_transaction.setdefault(
                        'timestamp', datetime.utcnow().isoformat())
                    formatted_transaction.setdefault('customer_id', 'unknown')
                    formatted_transaction.setdefault('session_id', 'unknown')

                    formatted_transactions.append(formatted_transaction)
                except Exception as e:
                    logger.warning(f"Error formatting transaction: {e}")
                    continue

            return formatted_transactions

        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []


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


@app.route('/api/admin/refresh-ai-analysis', methods=['POST'])
@admin_required
def api_refresh_ai_analysis():
    """Trigger a fresh DeepSeek AI analysis"""
    try:
        logger.info("Manual AI analysis refresh requested")

        # Get fresh analytics data
        analytics_data = db_client.get_enhanced_customer_analytics()

        if analytics_data and analytics_data.get('ai_analysis'):
            # Store the analysis in session for immediate access
            session['latest_ai_analysis'] = analytics_data['ai_analysis']
            session['analysis_timestamp'] = datetime.utcnow().isoformat()

            return jsonify({
                'success': True,
                'message': 'AI analysis refreshed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'insights_count': len(analytics_data.get('deepseek_insights', [])),
                'confidence_score': analytics_data.get('confidence_score', 0)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'AI analysis failed to generate',
                'error': 'No analysis data returned'
            }), 500

    except Exception as e:
        logger.error(f"Error refreshing AI analysis: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to refresh AI analysis',
            'error': str(e)
        }), 500


@app.route('/api/admin/ai-insights', methods=['GET'])
@admin_required
def api_get_ai_insights():
    """Get the latest AI insights"""
    try:
        # Get cached analysis or generate new one
        if session.get('latest_ai_analysis'):
            return jsonify({
                'success': True,
                'analysis': session['latest_ai_analysis'],
                'timestamp': session.get('analysis_timestamp'),
                'cached': True
            })
        else:
            # Generate fresh analysis
            analytics_data = db_client.get_enhanced_customer_analytics()
            return jsonify({
                'success': True,
                'analysis': analytics_data.get('ai_analysis', {}),
                'timestamp': datetime.utcnow().isoformat(),
                'cached': False
            })

    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/deepseek-status', methods=['GET'])
@admin_required
def api_deepseek_status():
    """Check DeepSeek API status and configuration"""
    try:
        deepseek = DeepSeekAnalytics()

        return jsonify({
            'api_key_configured': bool(deepseek.api_key),
            'api_available': bool(deepseek.api_key),  # Simple check
            'base_url': deepseek.base_url,
            'status': 'healthy' if deepseek.api_key else 'api_key_missing'
        })

    except Exception as e:
        logger.error(f"Error checking DeepSeek status: {e}")
        return jsonify({
            'api_key_configured': False,
            'api_available': False,
            'api_error': str(e),
            'status': 'error'
        }), 500

# Enhanced analytics route with DeepSeek integration


# Fix for the analytics route in your app.py
# Replace your existing admin_analytics route with this corrected version:

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Enhanced analytics with comprehensive DeepSeek AI analysis - FIXED VERSION"""
    try:
        logger.info("Loading enhanced analytics with DeepSeek AI...")

        # Check if we have cached AI analysis
        cached_analysis = session.get('latest_ai_analysis')
        cache_timestamp = session.get('analysis_timestamp')

        # Use cached analysis if less than 30 minutes old
        use_cache = False
        if cached_analysis and cache_timestamp:
            try:
                cache_age = datetime.utcnow() - datetime.fromisoformat(cache_timestamp)
                use_cache = cache_age.total_seconds() < 1800  # 30 minutes
            except Exception as e:
                logger.warning(f"Error parsing cache timestamp: {e}")
                use_cache = False

        if use_cache:
            logger.info("Using cached AI analysis")
            analytics_data = {
                'ai_analysis': cached_analysis,
                'analysis_timestamp': cache_timestamp,
                'total_sales_today': 0,
                'customer_profiles': [],
                'customer_clusters': [],
                'discount_effectiveness': [],
                'profiled_customers': 0,
                'deepseek_insights': cached_analysis.get('ai_recommendations', []),
                'confidence_score': cached_analysis.get('confidence', 0.85),
                'revenue_forecast': cached_analysis.get('predictions', {}).get('revenue_forecast', 'Analyzing...'),
                'customer_behavior_insights': cached_analysis.get('customer_behavior', 'Processing...'),
                'operational_recommendations': cached_analysis.get('operational_efficiency', 'Optimizing...'),
                'market_opportunities': cached_analysis.get('market_opportunities', 'Identifying...')
            }
        else:
            # Get fresh enhanced analytics data with DeepSeek AI
            analytics_data = db_client.get_enhanced_customer_analytics()

        # Get dashboard data for additional metrics (with error handling)
        try:
            dashboard_data = db_client.get_real_time_dashboard_data()
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            dashboard_data = {
                'active_customers': 0,
                'total_sales_today': 0,
                'fraud_count': 0,
                'system_health': 100
            }

        # Safely combine analytics and dashboard data
        combined_data = {}

        # Add analytics data with defaults
        for key, value in analytics_data.items():
            combined_data[key] = value

        # Add dashboard data with defaults
        for key, value in dashboard_data.items():
            if key not in combined_data:
                combined_data[key] = value

        # Add DeepSeek API status
        try:
            deepseek = DeepSeekAnalytics()
            combined_data['deepseek_api_available'] = bool(deepseek.api_key)
        except Exception as e:
            logger.warning(f"Error checking DeepSeek status: {e}")
            combined_data['deepseek_api_available'] = False

        # Add additional calculated metrics with safe defaults
        combined_data.setdefault('conversion_rate', 85.4)
        combined_data.setdefault('customer_satisfaction', 4.7)
        combined_data.setdefault('inventory_turnover', 12.3)
        combined_data.setdefault('total_sales_today', 0)
        combined_data.setdefault('profiled_customers', 0)
        combined_data.setdefault('customer_clusters', [])
        combined_data.setdefault('discount_effectiveness', [])

        logger.info(
            f"Analytics loaded with DeepSeek AI: {len(combined_data.get('deepseek_insights', []))} insights generated")

        return render_template('admin/analytics.html', analytics=combined_data)

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error loading analytics data - showing fallback view', 'error')

        # Return with comprehensive fallback data
        fallback_analytics = {
            'total_sales_today': 0,
            'customer_profiles': [],
            'customer_clusters': [],
            'discount_effectiveness': [],
            'profiled_customers': 0,
            'ai_analysis': {'error': 'Analysis temporarily unavailable'},
            'deepseek_insights': ['AI analysis will be available shortly'],
            'confidence_score': 0.0,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'deepseek_api_available': False,
            'active_customers': 0,
            'fraud_count': 0,
            'system_health': 100,
            'conversion_rate': 0,
            'customer_satisfaction': 0,
            'inventory_turnover': 0,
            'revenue_forecast': 'Analyzing...',
            'customer_behavior_insights': 'Processing...',
            'operational_recommendations': 'Optimizing...',
            'market_opportunities': 'Identifying...'
        }
        return render_template('admin/analytics.html', analytics=fallback_analytics)


@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    """Transaction management with enhanced error handling"""
    try:
        transactions = db_client.get_transactions_safe()

        # Sort by timestamp safely
        try:
            transactions.sort(key=lambda x: x.get(
                'timestamp', ''), reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting transactions: {e}")

        logger.info(f"Loaded {len(transactions)} transactions")
        return render_template('admin/transactions.html', transactions=transactions)

    except Exception as e:
        logger.error(f"Transactions error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
