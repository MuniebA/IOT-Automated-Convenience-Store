#!/bin/bash

# ============================================================================
# IoT Store Admin UI Bootstrap Script (SHORT VERSION)
# ============================================================================
# This short script downloads and runs the full setup script
# ============================================================================

set -e

# Configuration from Terraform
GITHUB_REPO_URL="${github_repo_url}"
ADMIN_UI_PORT="${admin_ui_port}"
AWS_REGION="${aws_region}"
CUSTOMERS_TABLE="${customers_table}"
PRODUCTS_TABLE="${products_table}"
SESSIONS_TABLE="${sessions_table}"
TRANSACTIONS_TABLE="${transactions_table}"
FRAUD_EVENTS_TABLE="${fraud_events_table}"
ACCESS_LOGS_TABLE="${access_logs_table}"
SHELF_DISPLAYS_TABLE="${shelf_displays_table}"
SYSTEM_NODES_TABLE="${system_nodes_table}"

# Log setup
LOG_FILE="/var/log/iot-store-setup.log"
exec > >(tee -a $LOG_FILE) 2>&1

echo "[$(date)] Starting IoT Store Bootstrap..."

# Update system first
yum update -y
yum install -y git curl

# Download full setup script from GitHub
echo "[$(date)] Downloading full setup script..."
curl -o /tmp/admin_ui_setup_full.sh https://raw.githubusercontent.com/MuniebA/IOT-Automated-Convenience-Store/main/terraform/admin_ui_setup_full.sh

# Make it executable
chmod +x /tmp/admin_ui_setup_full.sh

# Export variables for the full script
export GITHUB_REPO_URL ADMIN_UI_PORT AWS_REGION
export CUSTOMERS_TABLE PRODUCTS_TABLE SESSIONS_TABLE TRANSACTIONS_TABLE
export FRAUD_EVENTS_TABLE ACCESS_LOGS_TABLE SHELF_DISPLAYS_TABLE SYSTEM_NODES_TABLE

# Run the full setup script
echo "[$(date)] Running full setup script..."
/tmp/admin_ui_setup_full.sh

echo "[$(date)] Bootstrap complete!"