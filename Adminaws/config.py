import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Mock mode for local testing (no database)
    MOCK_MODE = True
    
    # AWS Configuration (for later deployment)
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    # DynamoDB Table Names (for later)
    CUSTOMERS_TABLE = 'store-customers-prod'
    PRODUCTS_TABLE = 'store-products-prod'
    SESSIONS_TABLE = 'store-sessions-prod'
    TRANSACTIONS_TABLE = 'store-transactions-prod'
    FRAUD_EVENTS_TABLE = 'store-fraud-events-prod'
    ACCESS_LOGS_TABLE = 'store-access-logs-prod'