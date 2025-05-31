# ============================================================================
# IoT CONVENIENCE STORE - ENVIRONMENT VARIABLE BASED CONFIGURATION
# ============================================================================
# This configuration uses environment variables instead of AWS CLI
# Set your AWS credentials in .env file and load them before running terraform
# ============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure AWS Provider using environment variables
provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key_id
  secret_key = var.aws_secret_access_key
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "terraform"
      CreatedDate = formatdate("YYYY-MM-DD", timestamp())
    }
  }
}

# ============================================================================
# VARIABLES - Updated to use environment variables
# ============================================================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key_id" {
  description = "AWS Access Key ID"
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key"
  type        = string
  sensitive   = true
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "iot-convenience-store"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "github_repo_url" {
  description = "GitHub repository URL for admin UI"
  type        = string
  default     = "https://github.com/MuniebA/IOT-Automated-Convenience-Store.git"
}

variable "admin_ui_port" {
  description = "Port for admin UI Flask application"
  type        = number
  default     = 5000
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access admin UI"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

# ============================================================================
# DATA SOURCES
# ============================================================================

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get default subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ============================================================================
# DYNAMODB TABLES - ENHANCED SCHEMA
# ============================================================================

# Customers Table - Customer profiles with RFID authentication
resource "aws_dynamodb_table" "customers" {
  name           = "${var.project_name}-customers-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "rfid_card_uid"
    type = "S"
  }

  # GSI for RFID lookups
  global_secondary_index {
    name               = "rfid-lookup-index"
    hash_key           = "rfid_card_uid"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Customers Table"
    Purpose = "Customer profiles and RFID authentication"
  }
}

# Products Table - Product catalog with RFID tags
resource "aws_dynamodb_table" "products" {
  name           = "${var.project_name}-products-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "product_id"

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "product_rfid"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  # GSI for RFID product lookups
  global_secondary_index {
    name               = "rfid-lookup-index"
    hash_key           = "product_rfid"
    projection_type    = "ALL"
  }

  # GSI for category-based queries
  global_secondary_index {
    name               = "category-index"
    hash_key           = "category"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Products Table"
    Purpose = "Product catalog with RFID tags"
  }
}

# Sessions Table - Shopping sessions across all nodes
resource "aws_dynamodb_table" "sessions" {
  name           = "${var.project_name}-sessions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "start_time"
    type = "S"
  }

  attribute {
    name = "node_id"
    type = "S"
  }

  attribute {
    name = "session_status"
    type = "S"
  }

  # GSI for customer session history
  global_secondary_index {
    name               = "customer-time-index"
    hash_key           = "customer_id"
    range_key          = "start_time"
    projection_type    = "ALL"
  }

  # GSI for active sessions by node
  global_secondary_index {
    name               = "node-active-index"
    hash_key           = "node_id"
    range_key          = "session_status"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Sessions Table"
    Purpose = "Shopping sessions across all nodes"
  }
}

# Transactions Table - Individual item transactions
resource "aws_dynamodb_table" "transactions" {
  name           = "${var.project_name}-transactions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "transaction_id"
  range_key      = "session_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # GSI for session-based transaction queries
  global_secondary_index {
    name               = "session-time-index"
    hash_key           = "session_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for user transaction history
  global_secondary_index {
    name               = "user-time-index"
    hash_key           = "user_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Transactions Table"
    Purpose = "Individual item transactions and payments"
  }
}

# Scanned Items Table - Real-time RFID scans
resource "aws_dynamodb_table" "scanned_items" {
  name           = "${var.project_name}-scanned-items-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "scan_id"
  range_key      = "timestamp"

  attribute {
    name = "scan_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "tag_id"
    type = "S"
  }

  attribute {
    name = "product_id"
    type = "S"
  }

  # GSI for tag-based scan history
  global_secondary_index {
    name               = "tag-time-index"
    hash_key           = "tag_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for product scan analytics
  global_secondary_index {
    name               = "product-scan-index"
    hash_key           = "product_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Scanned Items Table"
    Purpose = "Real-time RFID scans from smart carts"
  }
}

# Fraud Events Table - Security and fraud detection
resource "aws_dynamodb_table" "fraud_events" {
  name           = "${var.project_name}-fraud-events-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "event_id"
  range_key      = "timestamp"

  attribute {
    name = "event_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "event_type"
    type = "S"
  }

  # GSI for session-based fraud analysis
  global_secondary_index {
    name               = "session-fraud-index"
    hash_key           = "session_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for fraud type analytics
  global_secondary_index {
    name               = "event-type-index"
    hash_key           = "event_type"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Fraud Events Table"
    Purpose = "Security and fraud detection events"
  }
}

# Access Logs Table - Door access and security
resource "aws_dynamodb_table" "access_logs" {
  name           = "${var.project_name}-access-logs-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "log_id"
  range_key      = "timestamp"

  attribute {
    name = "log_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "door_node_id"
    type = "S"
  }

  # GSI for customer access history
  global_secondary_index {
    name               = "customer-access-index"
    hash_key           = "customer_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for door-specific logs
  global_secondary_index {
    name               = "door-time-index"
    hash_key           = "door_node_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Access Logs Table"
    Purpose = "Door access events and security logs"
  }
}

# Shelf Displays Table - Smart shelf management
resource "aws_dynamodb_table" "shelf_displays" {
  name           = "${var.project_name}-shelf-displays-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "display_id"

  attribute {
    name = "display_id"
    type = "S"
  }

  attribute {
    name = "shelf_node_id"
    type = "S"
  }

  attribute {
    name = "start_time"
    type = "S"
  }

  attribute {
    name = "product_id"
    type = "S"
  }

  # GSI for shelf-based queries
  global_secondary_index {
    name               = "shelf-time-index"
    hash_key           = "shelf_node_id"
    range_key          = "start_time"
    projection_type    = "ALL"
  }

  # GSI for product display tracking
  global_secondary_index {
    name               = "product-display-index"
    hash_key           = "product_id"
    range_key          = "start_time"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Shelf Displays Table"
    Purpose = "Smart shelf discount displays and interactions"
  }
}

# System Nodes Table - IoT device registry
resource "aws_dynamodb_table" "system_nodes" {
  name           = "${var.project_name}-system-nodes-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "node_id"

  attribute {
    name = "node_id"
    type = "S"
  }

  attribute {
    name = "node_type"
    type = "S"
  }

  attribute {
    name = "store_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "last_heartbeat"
    type = "S"
  }

  # GSI for node type queries
  global_secondary_index {
    name               = "type-store-index"
    hash_key           = "node_type"
    range_key          = "store_id"
    projection_type    = "ALL"
  }

  # GSI for status monitoring
  global_secondary_index {
    name               = "status-index"
    hash_key           = "status"
    range_key          = "last_heartbeat"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "System Nodes Table"
    Purpose = "IoT device registry and health monitoring"
  }
}

# Sensor Data Table - Real-time sensor readings
resource "aws_dynamodb_table" "sensor_data" {
  name           = "${var.project_name}-sensor-data-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "reading_id"
  range_key      = "timestamp"

  attribute {
    name = "reading_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "node_id"
    type = "S"
  }

  # GSI for session-based sensor queries
  global_secondary_index {
    name               = "session-sensor-index"
    hash_key           = "session_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for node-based sensor monitoring
  global_secondary_index {
    name               = "node-sensor-index"
    hash_key           = "node_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # TTL for automatic data cleanup (30 days)
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name    = "Sensor Data Table"
    Purpose = "Real-time sensor readings from all Pi devices"
  }
}

# Inventory Transactions Table - Inventory changes
resource "aws_dynamodb_table" "inventory_transactions" {
  name           = "${var.project_name}-inventory-transactions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "inventory_id"

  attribute {
    name = "inventory_id"
    type = "S"
  }

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "node_id"
    type = "S"
  }

  # GSI for product inventory tracking
  global_secondary_index {
    name               = "product-time-index"
    hash_key           = "product_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for node inventory monitoring
  global_secondary_index {
    name               = "node-inventory-index"
    hash_key           = "node_id"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  tags = {
    Name    = "Inventory Transactions Table"
    Purpose = "All inventory changes across nodes"
  }
}

# ============================================================================
# IAM ROLES AND POLICIES
# ============================================================================

# Lambda Execution Role
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "Lambda Execution Role"
  }
}

# DynamoDB Policy for Lambda
resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "${var.project_name}-lambda-dynamodb-policy-${var.environment}"
  description = "IAM policy for Lambda to access DynamoDB tables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.customers.arn,
          aws_dynamodb_table.products.arn,
          aws_dynamodb_table.sessions.arn,
          aws_dynamodb_table.transactions.arn,
          aws_dynamodb_table.scanned_items.arn,
          aws_dynamodb_table.fraud_events.arn,
          aws_dynamodb_table.access_logs.arn,
          aws_dynamodb_table.shelf_displays.arn,
          aws_dynamodb_table.system_nodes.arn,
          "${aws_dynamodb_table.customers.arn}/index/*",
          "${aws_dynamodb_table.products.arn}/index/*",
          "${aws_dynamodb_table.sessions.arn}/index/*",
          "${aws_dynamodb_table.transactions.arn}/index/*",
          "${aws_dynamodb_table.scanned_items.arn}/index/*",
          "${aws_dynamodb_table.fraud_events.arn}/index/*",
          "${aws_dynamodb_table.access_logs.arn}/index/*",
          "${aws_dynamodb_table.shelf_displays.arn}/index/*",
          "${aws_dynamodb_table.system_nodes.arn}/index/*"
        ]
      }
    ]
  })
}

# Attach policies to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

# EC2 Role for Admin UI
resource "aws_iam_role" "admin_ui_role" {
  name = "${var.project_name}-admin-ui-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "Admin UI EC2 Role"
  }
}

# DynamoDB Policy for Admin UI
resource "aws_iam_policy" "admin_ui_dynamodb_policy" {
  name        = "${var.project_name}-admin-ui-dynamodb-policy-${var.environment}"
  description = "IAM policy for Admin UI to access DynamoDB tables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable",
          "dynamodb:ListTables"
        ]
        Resource = [
          aws_dynamodb_table.customers.arn,
          aws_dynamodb_table.products.arn,
          aws_dynamodb_table.sessions.arn,
          aws_dynamodb_table.transactions.arn,
          aws_dynamodb_table.scanned_items.arn,
          aws_dynamodb_table.fraud_events.arn,
          aws_dynamodb_table.access_logs.arn,
          aws_dynamodb_table.shelf_displays.arn,
          aws_dynamodb_table.system_nodes.arn,
          "${aws_dynamodb_table.customers.arn}/index/*",
          "${aws_dynamodb_table.products.arn}/index/*",
          "${aws_dynamodb_table.sessions.arn}/index/*",
          "${aws_dynamodb_table.transactions.arn}/index/*",
          "${aws_dynamodb_table.scanned_items.arn}/index/*",
          "${aws_dynamodb_table.fraud_events.arn}/index/*",
          "${aws_dynamodb_table.access_logs.arn}/index/*",
          "${aws_dynamodb_table.shelf_displays.arn}/index/*",
          "${aws_dynamodb_table.system_nodes.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "admin_ui_dynamodb_policy_attachment" {
  role       = aws_iam_role.admin_ui_role.name
  policy_arn = aws_iam_policy.admin_ui_dynamodb_policy.arn
}

# Instance Profile for EC2
resource "aws_iam_instance_profile" "admin_ui_profile" {
  name = "${var.project_name}-admin-ui-profile-${var.environment}"
  role = aws_iam_role.admin_ui_role.name
}

# ============================================================================
# IOT CORE - MQTT CONFIGURATION
# ============================================================================

# IoT Things for each node type
resource "aws_iot_thing" "smart_cart" {
  name = "${var.project_name}-cart-001-${var.environment}"

  attributes = {
    node_type = "smart-cart"
    location  = "store-floor"
    version   = "2.0.0"
  }
}

resource "aws_iot_thing" "door_access" {
  name = "${var.project_name}-door-001-${var.environment}"

  attributes = {
    node_type = "door-access"
    location  = "store-entrance"
    version   = "2.0.0"
  }
}

resource "aws_iot_thing" "smart_shelf" {
  name = "${var.project_name}-shelf-001-${var.environment}"

  attributes = {
    node_type = "smart-shelf"
    location  = "store-premium-section"
    version   = "2.0.0"
  }
}

# IoT Certificates (will be generated but not output for security)
resource "aws_iot_certificate" "device_certificates" {
  for_each = {
    cart  = aws_iot_thing.smart_cart.name
    door  = aws_iot_thing.door_access.name
    shelf = aws_iot_thing.smart_shelf.name
  }

  active = true
}

# IoT Policies for device communication
resource "aws_iot_policy" "device_policy" {
  name = "${var.project_name}-device-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iot:Connect"
        ]
        Resource = "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:client/${var.project_name}-*-${var.environment}"
      },
      {
        Effect = "Allow"
        Action = [
          "iot:Publish"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/*/status",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/*/item/scanned",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/*/item/validated",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/*/fraud",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/*/checkout",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/door/*/entry",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/door/*/exit",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/door/*/status",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/door/*/errors",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/shelf/*/status",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/shelf/*/interactions",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/shelf/*/errors"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iot:Subscribe",
          "iot:Receive"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/*/commands",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/discounts/active",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/door/*/commands",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/cart/+/checkout",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/customers/valid",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/shelf/*/active",
          "arn:aws:iot:${var.aws_region}:${var.aws_account_id}:topic/store/shelf/*/commands"
        ]
      }
    ]
  })
}

# Attach policies to certificates
resource "aws_iot_policy_attachment" "device_policy_attachments" {
  for_each = aws_iot_certificate.device_certificates

  policy = aws_iot_policy.device_policy.name
  target = each.value.arn
}

# Attach certificates to things
resource "aws_iot_thing_principal_attachment" "device_cert_attachments" {
  for_each = {
    cart  = { thing = aws_iot_thing.smart_cart.name, cert = aws_iot_certificate.device_certificates["cart"].arn }
    door  = { thing = aws_iot_thing.door_access.name, cert = aws_iot_certificate.device_certificates["door"].arn }
    shelf = { thing = aws_iot_thing.smart_shelf.name, cert = aws_iot_certificate.device_certificates["shelf"].arn }
  }

  principal = each.value.cert
  thing     = each.value.thing
}

# ============================================================================
# LAMBDA FUNCTIONS
# ============================================================================

# Lambda function package for session processor
data "archive_file" "session_processor_zip" {
  type        = "zip"
  output_path = "${path.module}/session_processor.zip"
  
  source {
    content = file("${path.module}/lambda_session_processor.py")
    filename = "lambda_function.py"
  }
}

# Session Processor Lambda
resource "aws_lambda_function" "session_processor" {
  filename         = data.archive_file.session_processor_zip.output_path
  function_name    = "${var.project_name}-session-processor-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.session_processor_zip.output_base64sha256
  runtime         = "python3.9"
  timeout         = 30

  environment {
    variables = {
      CUSTOMERS_TABLE     = aws_dynamodb_table.customers.name
      SESSIONS_TABLE      = aws_dynamodb_table.sessions.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FRAUD_EVENTS_TABLE  = aws_dynamodb_table.fraud_events.name
      ENVIRONMENT        = var.environment
    }
  }

  tags = {
    Name    = "Session Processor Function"
    Purpose = "Process completed shopping sessions"
  }
}

# IoT Rules for message processing
resource "aws_iot_topic_rule" "session_complete" {
  name        = "${replace(var.project_name, "-", "_")}_session_complete_${var.environment}"
  description = "Process completed sessions from smart cart"
  enabled     = true
  sql         = "SELECT * FROM 'store/cart/+/checkout'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.session_processor.arn
  }
}

# Lambda permission for IoT rule
resource "aws_lambda_permission" "iot_session_processor" {
  statement_id  = "AllowExecutionFromIoTRule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.session_processor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.session_complete.arn
}

# ============================================================================
# EC2 INSTANCE FOR ADMIN UI - FIXED VERSION
# ============================================================================

# Security Group for Admin UI
resource "aws_security_group" "admin_ui_sg" {
  name        = "${var.project_name}-admin-ui-sg-${var.environment}"
  description = "Security group for IoT Store Admin UI"
  vpc_id      = data.aws_vpc.default.id

  # HTTP access for admin UI
  ingress {
    from_port   = var.admin_ui_port
    to_port     = var.admin_ui_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # HTTP access for nginx (port 80)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # SSH access for management (optional)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict this in production
  }

  # HTTPS outbound for GitHub clone
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP outbound for package downloads
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS outbound
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "Admin UI Security Group"
  }
}

# EC2 Instance for Admin UI - CORRECTED RESOURCE TYPE
resource "aws_instance" "admin_ui" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"  # Free tier eligible
  vpc_security_group_ids = [aws_security_group.admin_ui_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.admin_ui_profile.name
  
  user_data = templatefile("${path.module}/admin_ui_bootstrap.sh", {
    github_repo_url      = var.github_repo_url
    admin_ui_port       = var.admin_ui_port
    aws_region          = var.aws_region
    customers_table     = aws_dynamodb_table.customers.name
    products_table      = aws_dynamodb_table.products.name
    sessions_table      = aws_dynamodb_table.sessions.name
    transactions_table  = aws_dynamodb_table.transactions.name
    fraud_events_table  = aws_dynamodb_table.fraud_events.name
    access_logs_table   = aws_dynamodb_table.access_logs.name
    shelf_displays_table = aws_dynamodb_table.shelf_displays.name
    system_nodes_table  = aws_dynamodb_table.system_nodes.name
  })

  tags = {
    Name = "IoT Store Admin UI Server"
    Type = "Admin Interface"
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "admin_ui_url" {
  description = "URL to access the Admin UI"
  value       = "http://${aws_instance.admin_ui.public_ip}:${var.admin_ui_port}"
}

output "admin_ui_ip" {
  description = "Public IP of the Admin UI server"
  value       = aws_instance.admin_ui.public_ip
}

output "dynamodb_tables" {
  description = "Created DynamoDB table names"
  value = {
    customers             = aws_dynamodb_table.customers.name
    products             = aws_dynamodb_table.products.name
    sessions             = aws_dynamodb_table.sessions.name
    transactions         = aws_dynamodb_table.transactions.name
    scanned_items        = aws_dynamodb_table.scanned_items.name
    fraud_events         = aws_dynamodb_table.fraud_events.name
    access_logs          = aws_dynamodb_table.access_logs.name
    shelf_displays       = aws_dynamodb_table.shelf_displays.name
    system_nodes         = aws_dynamodb_table.system_nodes.name
    sensor_data          = aws_dynamodb_table.sensor_data.name          # NEW
    inventory_transactions = aws_dynamodb_table.inventory_transactions.name # NEW
  }
}

output "iot_endpoints" {
  description = "IoT Core endpoints and topics"
  value = {
    mqtt_endpoint = "Use: aws iot describe-endpoint --endpoint-type iot:Data-ATS"
    thing_names = {
      cart  = aws_iot_thing.smart_cart.name
      door  = aws_iot_thing.door_access.name
      shelf = aws_iot_thing.smart_shelf.name
    }
  }
}

output "lambda_functions" {
  description = "Created Lambda function names"
  value = {
    session_processor = aws_lambda_function.session_processor.function_name
  }
}