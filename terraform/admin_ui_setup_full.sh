#!/bin/bash

# ============================================================================
# IoT Store Admin UI FULL Setup Script (FOR GITHUB)
# ============================================================================
# This is the complete setup script that gets downloaded by the bootstrap
# Upload this file to: terraform/admin_ui_setup_full.sh in your GitHub repo
# ============================================================================

set -e

# Use environment variables passed from bootstrap
GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/MuniebA/IOT-Automated-Convenience-Store.git}"
ADMIN_UI_PORT="${ADMIN_UI_PORT:-5000}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Script variables
APP_USER="ec2-user"
APP_DIR="/home/$APP_USER/iot-store-admin"
LOG_FILE="/var/log/iot-store-setup.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== Starting IoT Store Admin UI FULL Setup ==="

# Install required packages
log "Installing required packages..."
yum install -y \
    python3 \
    python3-pip \
    git \
    nginx \
    htop \
    awscli

# Install Python packages globally
log "Installing Python packages..."
pip3 install --upgrade pip
pip3 install \
    flask \
    flask-cors \
    python-dotenv \
    boto3 \
    gunicorn

# Create application directory
log "Setting up application directory..."
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# Clone repository and setup as app user
log "Cloning GitHub repository..."
sudo -u $APP_USER bash << 'EOF'
cd /home/ec2-user

# Remove existing directory if present
if [ -d "iot-store-admin" ]; then
    rm -rf iot-store-admin
fi

# Clone the repository
git clone $GITHUB_REPO_URL iot-store-admin
cd iot-store-admin/Adminaws

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies in virtual environment
pip install --upgrade pip
pip install flask flask-cors python-dotenv boto3 gunicorn

# Create production configuration
cat > config.py << 'CONFIG_EOF'
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-change-me'
    
    # Production mode - use DynamoDB
    MOCK_MODE = False
    
    # AWS Configuration
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    # DynamoDB Table Names
    CUSTOMERS_TABLE = os.environ.get('CUSTOMERS_TABLE', 'customers')
    PRODUCTS_TABLE = os.environ.get('PRODUCTS_TABLE', 'products')
    SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE', 'sessions')
    TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'transactions')
    FRAUD_EVENTS_TABLE = os.environ.get('FRAUD_EVENTS_TABLE', 'fraud_events')
    ACCESS_LOGS_TABLE = os.environ.get('ACCESS_LOGS_TABLE', 'access_logs')
    SHELF_DISPLAYS_TABLE = os.environ.get('SHELF_DISPLAYS_TABLE', 'shelf_displays')
    SYSTEM_NODES_TABLE = os.environ.get('SYSTEM_NODES_TABLE', 'system_nodes')
    
    # Flask Configuration
    DEBUG = False
    TESTING = False
CONFIG_EOF

# Create production environment file
cat > .env << 'ENV_EOF'
# Production Environment Configuration
SECRET_KEY=iot-store-production-secret-key-$(openssl rand -hex 16)
AWS_REGION=${AWS_REGION}

# DynamoDB Tables (will be set by systemd service)
CUSTOMERS_TABLE=${CUSTOMERS_TABLE}
PRODUCTS_TABLE=${PRODUCTS_TABLE}
SESSIONS_TABLE=${SESSIONS_TABLE}
TRANSACTIONS_TABLE=${TRANSACTIONS_TABLE}
FRAUD_EVENTS_TABLE=${FRAUD_EVENTS_TABLE}
ACCESS_LOGS_TABLE=${ACCESS_LOGS_TABLE}
SHELF_DISPLAYS_TABLE=${SHELF_DISPLAYS_TABLE}
SYSTEM_NODES_TABLE=${SYSTEM_NODES_TABLE}

# Flask Settings
FLASK_ENV=production
FLASK_DEBUG=false
ENV_EOF

# Create utils directory if it doesn't exist
mkdir -p utils

# Create DynamoDB client
cat > utils/dynamodb_client.py << 'DYNAMO_EOF'
import boto3
import json
from datetime import datetime
from config import Config

class DynamoDBClient:
    """DynamoDB client for admin UI operations"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=Config.AWS_REGION)
        self.tables = {
            'customers': self.dynamodb.Table(Config.CUSTOMERS_TABLE),
            'products': self.dynamodb.Table(Config.PRODUCTS_TABLE), 
            'sessions': self.dynamodb.Table(Config.SESSIONS_TABLE),
            'transactions': self.dynamodb.Table(Config.TRANSACTIONS_TABLE),
            'fraud_events': self.dynamodb.Table(Config.FRAUD_EVENTS_TABLE),
            'access_logs': self.dynamodb.Table(Config.ACCESS_LOGS_TABLE),
            'shelf_displays': self.dynamodb.Table(Config.SHELF_DISPLAYS_TABLE),
            'system_nodes': self.dynamodb.Table(Config.SYSTEM_NODES_TABLE)
        }
    
    def get_customers(self, limit=50):
        try:
            response = self.tables['customers'].scan(Limit=limit)
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting customers: {e}")
            return []
    
    def get_sessions(self, limit=50):
        try:
            response = self.tables['sessions'].scan(Limit=limit)
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting sessions: {e}")
            return []
    
    def get_transactions(self, limit=50):
        try:
            response = self.tables['transactions'].scan(Limit=limit)
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
    
    def get_fraud_events(self, limit=50):
        try:
            response = self.tables['fraud_events'].scan(Limit=limit)
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting fraud events: {e}")
            return []
    
    def create_customer(self, customer_data):
        try:
            customer_data['created_at'] = datetime.utcnow().isoformat()
            customer_data['updated_at'] = datetime.utcnow().isoformat()
            customer_data['total_spent'] = 0.0
            customer_data['total_visits'] = 0
            customer_data['membership_status'] = 'ACTIVE'
            
            self.tables['customers'].put_item(Item=customer_data)
            return True
        except Exception as e:
            print(f"Error creating customer: {e}")
            return False
    
    def get_analytics_data(self):
        try:
            customers_count = self.tables['customers'].scan(Select='COUNT')['Count']
            sessions_count = self.tables['sessions'].scan(Select='COUNT')['Count'] 
            transactions_count = self.tables['transactions'].scan(Select='COUNT')['Count']
            fraud_count = self.tables['fraud_events'].scan(Select='COUNT')['Count']
            
            recent_transactions = self.get_transactions(100)
            total_sales = sum(float(t.get('total_amount', 0)) for t in recent_transactions)
            
            return {
                'total_customers': customers_count,
                'active_sessions': sessions_count,
                'total_sales_today': total_sales,
                'fraud_alerts': fraud_count,
                'daily_sales': [
                    {'date': '2024-05-25', 'sales': 1200.50},
                    {'date': '2024-05-26', 'sales': 1450.75},
                    {'date': '2024-05-27', 'sales': 1680.25},
                    {'date': '2024-05-28', 'sales': 1234.00},
                    {'date': '2024-05-29', 'sales': 1890.30},
                    {'date': '2024-05-30', 'sales': 2147.80},
                    {'date': '2024-05-31', 'sales': total_sales}
                ],
                'fraud_events': [
                    {'type': 'unscanned_item', 'count': 12},
                    {'type': 'weight_mismatch', 'count': 8}, 
                    {'type': 'multiple_items', 'count': 5},
                    {'type': 'no_placement', 'count': 15}
                ]
            }
        except Exception as e:
            print(f"Error getting analytics: {e}")
            return {
                'total_customers': 0,
                'active_sessions': 0,
                'total_sales_today': 0.0,
                'fraud_alerts': 0,
                'daily_sales': [],
                'fraud_events': []
            }

# Global instance
db_client = DynamoDBClient()
DYNAMO_EOF

# Update existing app.py for production
if [ -f "app.py" ]; then
    # Backup original
    cp app.py app_original.py
    
    # Replace config import and add DynamoDB client
    sed -i 's/from utils.mock_data import/# from utils.mock_data import/g' app.py
    sed -i '/from config import Config/a from utils.dynamodb_client import db_client' app.py
    sed -i 's/MOCK_MODE = True/MOCK_MODE = False/g' app.py || true
fi

EOF

log "Setting up systemd service..."

# Create systemd service with environment variables
cat > /etc/systemd/system/iot-store-admin.service << SERVICE_EOF
[Unit]
Description=IoT Store Admin UI
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR/Adminaws
Environment=PATH=/home/$APP_USER/iot-store-admin/Adminaws/venv/bin
Environment=CUSTOMERS_TABLE=${CUSTOMERS_TABLE}
Environment=PRODUCTS_TABLE=${PRODUCTS_TABLE}
Environment=SESSIONS_TABLE=${SESSIONS_TABLE}
Environment=TRANSACTIONS_TABLE=${TRANSACTIONS_TABLE}
Environment=FRAUD_EVENTS_TABLE=${FRAUD_EVENTS_TABLE}
Environment=ACCESS_LOGS_TABLE=${ACCESS_LOGS_TABLE}
Environment=SHELF_DISPLAYS_TABLE=${SHELF_DISPLAYS_TABLE}
Environment=SYSTEM_NODES_TABLE=${SYSTEM_NODES_TABLE}
Environment=AWS_REGION=${AWS_REGION}
ExecStart=/home/$APP_USER/iot-store-admin/Adminaws/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable and start the service
log "Starting IoT Store Admin UI service..."
systemctl daemon-reload
systemctl enable iot-store-admin
systemctl start iot-store-admin

# Setup nginx reverse proxy
log "Configuring nginx reverse proxy..."
cat > /etc/nginx/conf.d/iot-store-admin.conf << NGINX_EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:${ADMIN_UI_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static {
        alias $APP_DIR/Adminaws/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_EOF

# Start nginx
systemctl enable nginx
systemctl start nginx

# Wait for service to start
sleep 10

# Check service status
log "Checking service status..."
systemctl status iot-store-admin --no-pager || true

# Test the application
log "Testing application..."
curl -f http://localhost:${ADMIN_UI_PORT}/ || log "WARNING: Application test failed"

# Initialize sample data
log "Initializing sample data..."
sudo -u $APP_USER bash << 'SAMPLE_EOF'
cd /home/ec2-user/iot-store-admin/Adminaws
source venv/bin/activate

python3 << 'PYTHON_EOF'
import boto3
from datetime import datetime

try:
    dynamodb = boto3.resource('dynamodb', region_name='${AWS_REGION}')
    
    # Sample customers
    customers_table = dynamodb.Table('${CUSTOMERS_TABLE}')
    customers_table.put_item(Item={
        'customer_id': 'cust_001',
        'customer_name': 'John Doe',
        'customer_type': 'VIP',
        'rfid_card_uid': 'ABC123456789',
        'email': 'john.doe@university.edu',
        'total_spent': 1250.75,
        'total_visits': 45,
        'membership_status': 'ACTIVE',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    })
    
    # Sample products
    products_table = dynamodb.Table('${PRODUCTS_TABLE}')
    products_table.put_item(Item={
        'product_id': 'prod_001',
        'product_name': 'Red Apple',
        'product_rfid': 'APPLE001',
        'category': 'fruits',
        'regular_price': 2.99,
        'current_price': 2.99,
        'vip_price': 2.49,
        'weight_per_unit': 150,
        'inventory_level': 50,
        'is_active': True,
        'created_at': datetime.utcnow().isoformat()
    })
    
    print("Sample data created successfully!")
    
except Exception as e:
    print(f"Error creating sample data: {e}")
PYTHON_EOF
SAMPLE_EOF

log "=== IoT Store Admin UI Setup Complete ==="
log "Admin UI accessible at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):${ADMIN_UI_PORT}"
log "Also available via nginx: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"