import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Production mode - set to False for production deployment
    MOCK_MODE = False

    # AWS Configuration
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

    # DeepSeek API Configuration
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

    # DynamoDB Table Names (production)
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
