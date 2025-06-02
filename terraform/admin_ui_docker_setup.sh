#!/bin/bash

# ============================================================================
# IoT Store Admin UI - Docker Deployment Script for EC2 (Docker Hub Version)
# ============================================================================
# This script pulls a pre-built image from Docker Hub and runs it
# ============================================================================

set -e

# Configuration from Terraform template
DOCKER_IMAGE="munieb/iot-store-admin:latest"  # YOUR DOCKER HUB IMAGE
ADMIN_UI_PORT="${admin_ui_port}"
AWS_REGION="${aws_region}"

# DynamoDB Table Names
CUSTOMERS_TABLE="${customers_table}"
PRODUCTS_TABLE="${products_table}"
SESSIONS_TABLE="${sessions_table}"
TRANSACTIONS_TABLE="${transactions_table}"
FRAUD_EVENTS_TABLE="${fraud_events_table}"
ACCESS_LOGS_TABLE="${access_logs_table}"
SHELF_DISPLAYS_TABLE="${shelf_displays_table}"
SYSTEM_NODES_TABLE="${system_nodes_table}"

# Script variables
LOG_FILE="/var/log/iot-store-setup.log"
APP_DIR="/home/ec2-user/iot-store-admin"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== Starting IoT Store Docker Deployment (Docker Hub) ==="

# Update system packages
log "Updating system packages..."
yum update -y

# Install Docker
log "Installing Docker..."
yum install -y docker
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Install Docker Compose
log "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p $APP_DIR
chown ec2-user:ec2-user $APP_DIR

# Pull the Docker image
log "Pulling Docker image: $DOCKER_IMAGE"
docker pull $DOCKER_IMAGE

# Create docker-compose file
log "Creating Docker Compose configuration..."
cat > $APP_DIR/docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  iot-admin-ui:
    image: DOCKER_IMAGE_PLACEHOLDER
    container_name: iot-store-admin
    ports:
      - "PORT_PLACEHOLDER:5000"
    environment:
      - AWS_REGION=AWS_REGION_PLACEHOLDER
      - CUSTOMERS_TABLE=CUSTOMERS_TABLE_PLACEHOLDER
      - PRODUCTS_TABLE=PRODUCTS_TABLE_PLACEHOLDER
      - SESSIONS_TABLE=SESSIONS_TABLE_PLACEHOLDER
      - TRANSACTIONS_TABLE=TRANSACTIONS_TABLE_PLACEHOLDER
      - FRAUD_EVENTS_TABLE=FRAUD_EVENTS_TABLE_PLACEHOLDER
      - ACCESS_LOGS_TABLE=ACCESS_LOGS_TABLE_PLACEHOLDER
      - SHELF_DISPLAYS_TABLE=SHELF_DISPLAYS_TABLE_PLACEHOLDER
      - SYSTEM_NODES_TABLE=SYSTEM_NODES_TABLE_PLACEHOLDER
      - PORT=5000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: iot-store-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - iot-admin-ui
    restart: unless-stopped
COMPOSE_EOF

# Replace placeholders
sed -i "s|DOCKER_IMAGE_PLACEHOLDER|$DOCKER_IMAGE|g" $APP_DIR/docker-compose.yml
sed -i "s|PORT_PLACEHOLDER|$ADMIN_UI_PORT|g" $APP_DIR/docker-compose.yml
sed -i "s|AWS_REGION_PLACEHOLDER|$AWS_REGION|g" $APP_DIR/docker-compose.yml
sed -i "s|CUSTOMERS_TABLE_PLACEHOLDER|$CUSTOMERS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|PRODUCTS_TABLE_PLACEHOLDER|$PRODUCTS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|SESSIONS_TABLE_PLACEHOLDER|$SESSIONS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|TRANSACTIONS_TABLE_PLACEHOLDER|$TRANSACTIONS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|FRAUD_EVENTS_TABLE_PLACEHOLDER|$FRAUD_EVENTS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|ACCESS_LOGS_TABLE_PLACEHOLDER|$ACCESS_LOGS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|SHELF_DISPLAYS_TABLE_PLACEHOLDER|$SHELF_DISPLAYS_TABLE|g" $APP_DIR/docker-compose.yml
sed -i "s|SYSTEM_NODES_TABLE_PLACEHOLDER|$SYSTEM_NODES_TABLE|g" $APP_DIR/docker-compose.yml

# Create nginx configuration
log "Creating Nginx configuration..."
cat > $APP_DIR/nginx.conf << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    upstream iot_admin {
        server iot-admin-ui:5000;
    }

    server {
        listen 80;
        server_name _;

        location /nginx-health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://iot_admin;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
NGINX_EOF

# Set ownership
chown -R ec2-user:ec2-user $APP_DIR

# Start services
log "Starting Docker services..."
cd $APP_DIR
docker-compose up -d

# Wait for services
log "Waiting for services to start..."
sleep 30

# Test services
log "Testing application..."
RETRIES=0
MAX_RETRIES=10

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:$ADMIN_UI_PORT/health > /dev/null 2>&1; then
        log "✅ Application is responding on port $ADMIN_UI_PORT"
        break
    else
        log "⏳ Waiting for application... (attempt $((RETRIES + 1))/$MAX_RETRIES)"
        sleep 10
        RETRIES=$((RETRIES + 1))
    fi
done

if curl -f http://localhost:80/health > /dev/null 2>&1; then
    log "✅ Nginx proxy is working on port 80"
else
    log "⚠️ Nginx proxy not responding"
fi

# Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/iot-store-admin.service << 'SERVICE_EOF'
[Unit]
Description=IoT Store Admin UI
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/iot-store-admin
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl enable iot-store-admin

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

log "=== IoT Store Deployment Complete ==="
log "🐳 Using Docker image: $DOCKER_IMAGE"
log "🌐 Admin UI: http://$PUBLIC_IP:$ADMIN_UI_PORT"
log "🌐 Nginx proxy: http://$PUBLIC_IP"
log "📝 Health check: http://$PUBLIC_IP/health"
log "🔄 Manage: systemctl restart iot-store-admin"
log "📋 Logs: docker-compose logs -f (from $APP_DIR)"