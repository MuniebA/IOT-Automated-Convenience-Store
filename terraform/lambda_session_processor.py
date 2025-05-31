import json
import boto3
import uuid
from datetime import datetime
import os

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Get table names from environment variables
CUSTOMERS_TABLE = os.environ['CUSTOMERS_TABLE']
SESSIONS_TABLE = os.environ['SESSIONS_TABLE']
TRANSACTIONS_TABLE = os.environ['TRANSACTIONS_TABLE']
FRAUD_EVENTS_TABLE = os.environ['FRAUD_EVENTS_TABLE']


def lambda_handler(event, context):
    """
    Process completed shopping sessions from IoT devices
    This function is triggered by MQTT messages from smart carts
    """

    try:
        print(f"Received event: {json.dumps(event)}")

        # Parse the incoming message
        if 'Records' in event:
            # Handle IoT Rule triggered event
            for record in event['Records']:
                process_session_message(record)
        else:
            # Handle direct invocation
            process_session_message(event)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Session processed successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        print(f"Error processing session: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def process_session_message(message_data):
    """Process individual session completion message"""

    # Extract session data from message
    if 'dynamodb' in str(message_data):
        # Handle DynamoDB stream event
        session_data = extract_from_dynamodb_event(message_data)
    else:
        # Handle IoT Core message
        session_data = extract_from_iot_message(message_data)

    if not session_data:
        print("No valid session data found in message")
        return

    # Process the session
    session_id = session_data.get('session_id')
    customer_id = session_data.get('customer_id')

    print(f"Processing session {session_id} for customer {customer_id}")

    # Update session status
    update_session_status(session_data)

    # Create transaction records
    create_transaction_records(session_data)

    # Update customer statistics
    update_customer_stats(session_data)

    # Process any fraud events
    process_fraud_events(session_data)

    print(f"Successfully processed session {session_id}")


def extract_from_iot_message(message_data):
    """Extract session data from IoT Core message"""

    try:
        # IoT Core message structure
        if 'topic' in message_data:
            topic = message_data['topic']
            payload = json.loads(message_data.get('payload', '{}'))
        else:
            # Direct message payload
            payload = message_data

        # Validate required fields
        required_fields = ['session_id', 'customer_id', 'total_amount']
        for field in required_fields:
            if field not in payload:
                print(f"Missing required field: {field}")
                return None

        return payload

    except Exception as e:
        print(f"Error extracting IoT message: {str(e)}")
        return None


def extract_from_dynamodb_event(event_data):
    """Extract session data from DynamoDB stream event"""

    try:
        # Process DynamoDB stream record
        if 'dynamodb' in event_data:
            dynamodb_data = event_data['dynamodb']
            if 'NewImage' in dynamodb_data:
                # Convert DynamoDB format to regular dict
                return convert_dynamodb_to_dict(dynamodb_data['NewImage'])

        return None

    except Exception as e:
        print(f"Error extracting DynamoDB event: {str(e)}")
        return None


def convert_dynamodb_to_dict(dynamodb_item):
    """Convert DynamoDB item format to regular Python dict"""

    result = {}
    for key, value in dynamodb_item.items():
        if 'S' in value:
            result[key] = value['S']
        elif 'N' in value:
            result[key] = float(value['N'])
        elif 'BOOL' in value:
            result[key] = value['BOOL']
        elif 'L' in value:
            result[key] = [convert_dynamodb_to_dict(
                item) for item in value['L']]
        elif 'M' in value:
            result[key] = convert_dynamodb_to_dict(value['M'])

    return result


def update_session_status(session_data):
    """Update session status to completed"""

    try:
        sessions_table = dynamodb.Table(SESSIONS_TABLE)

        session_id = session_data['session_id']

        # Update session with completion details
        sessions_table.update_item(
            Key={'session_id': session_id},
            UpdateExpression="""
                SET session_status = :status,
                    end_time = :end_time,
                    total_amount = :total_amount,
                    total_items = :total_items,
                    checkout_completed = :checkout_completed,
                    processed_at = :processed_at
            """,
            ExpressionAttributeValues={
                ':status': 'completed',
                ':end_time': datetime.utcnow().isoformat(),
                ':total_amount': session_data.get('total_amount', 0),
                ':total_items': session_data.get('total_items', 0),
                ':checkout_completed': True,
                ':processed_at': datetime.utcnow().isoformat()
            }
        )

        print(f"Updated session status for {session_id}")

    except Exception as e:
        print(f"Error updating session status: {str(e)}")
        raise


def create_transaction_records(session_data):
    """Create transaction records from session data"""

    try:
        transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)

        session_id = session_data['session_id']
        customer_id = session_data.get('customer_id')

        # Create main transaction record
        transaction_id = f"trans_{uuid.uuid4().hex[:8]}"

        transaction_record = {
            'transaction_id': transaction_id,
            'session_id': session_id,
            'user_id': customer_id,
            'timestamp': datetime.utcnow().isoformat(),
            'total_amount': session_data.get('total_amount', 0),
            'items': json.dumps(session_data.get('items', [])),
            'store_id': session_data.get('store_id', 'store_001'),
            'payment_method': session_data.get('payment_method', 'card'),
            'transaction_status': 'completed'
        }

        transactions_table.put_item(Item=transaction_record)

        print(f"Created transaction record {transaction_id}")

    except Exception as e:
        print(f"Error creating transaction records: {str(e)}")
        raise


def update_customer_stats(session_data):
    """Update customer statistics and history"""

    try:
        customers_table = dynamodb.Table(CUSTOMERS_TABLE)

        customer_id = session_data.get('customer_id')
        if not customer_id:
            print("No customer ID found, skipping customer stats update")
            return

        total_amount = session_data.get('total_amount', 0)

        # Update customer totals
        customers_table.update_item(
            Key={'customer_id': customer_id},
            UpdateExpression="""
                ADD total_spent :amount, total_visits :visits
                SET last_visit = :last_visit,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ':amount': total_amount,
                ':visits': 1,
                ':last_visit': datetime.utcnow().isoformat(),
                ':updated_at': datetime.utcnow().isoformat()
            }
        )

        print(f"Updated customer stats for {customer_id}")

    except Exception as e:
        print(f"Error updating customer stats: {str(e)}")
        # Don't raise here, customer stats update is not critical


def process_fraud_events(session_data):
    """Process any fraud events from the session"""

    try:
        fraud_events = session_data.get('fraud_events', [])
        if not fraud_events:
            return

        fraud_events_table = dynamodb.Table(FRAUD_EVENTS_TABLE)
        session_id = session_data['session_id']

        for fraud_event in fraud_events:
            event_id = f"fraud_{uuid.uuid4().hex[:8]}"

            fraud_record = {
                'event_id': event_id,
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id,
                'event_type': fraud_event.get('type', 'unknown'),
                'details': fraud_event.get('details', ''),
                'severity': fraud_event.get('severity', 'medium'),
                'node_type': 'smart-cart',
                'node_id': session_data.get('node_id', 'unknown'),
                'customer_id': session_data.get('customer_id'),
                'auto_resolved': False,
                'staff_notified': fraud_event.get('severity') in ['high', 'critical']
            }

            fraud_events_table.put_item(Item=fraud_record)

            print(f"Created fraud event record {event_id}")

    except Exception as e:
        print(f"Error processing fraud events: {str(e)}")
        # Don't raise here, fraud event logging is not critical for session completion


def validate_session_data(session_data):
    """Validate session data before processing"""

    required_fields = ['session_id', 'customer_id']

    for field in required_fields:
        if not session_data.get(field):
            raise ValueError(f"Missing required field: {field}")

    # Validate data types
    if 'total_amount' in session_data:
        try:
            float(session_data['total_amount'])
        except (ValueError, TypeError):
            session_data['total_amount'] = 0.0

    if 'total_items' in session_data:
        try:
            int(session_data['total_items'])
        except (ValueError, TypeError):
            session_data['total_items'] = 0

    return session_data


def log_session_completion(session_data):
    """Log session completion for monitoring"""

    session_id = session_data.get('session_id', 'unknown')
    customer_id = session_data.get('customer_id', 'unknown')
    total_amount = session_data.get('total_amount', 0)

    print(
        f"SESSION COMPLETED: {session_id} | Customer: {customer_id} | Amount: ${total_amount}")

    # Could add CloudWatch metrics here in production
    # cloudwatch = boto3.client('cloudwatch')
    # cloudwatch.put_metric_data(...)

# Helper function for testing


def create_test_event():
    """Create a test event for Lambda function testing"""

    return {
        'session_id': f'test_session_{uuid.uuid4().hex[:8]}',
        'customer_id': 'test_customer_001',
        'node_id': 'cart-001',
        'store_id': 'store-001',
        'total_amount': 45.67,
        'total_items': 5,
        'payment_method': 'card',
        'items': [
            {'product_id': 'prod_001', 'quantity': 2, 'price': 15.99},
            {'product_id': 'prod_002', 'quantity': 1, 'price': 13.69}
        ],
        'fraud_events': [
            {
                'type': 'weight_mismatch',
                'severity': 'low',
                'details': 'Minor weight discrepancy detected'
            }
        ],
        'timestamp': datetime.utcnow().isoformat()
    }
