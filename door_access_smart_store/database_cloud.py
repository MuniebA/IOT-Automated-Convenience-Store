# database_cloud.py
# Cloud database client for DynamoDB integration
# This file works ALONGSIDE your existing database.py (doesn't replace it)

import boto3
import uuid
from datetime import datetime
import json
from botocore.exceptions import ClientError, NoCredentialsError

class CloudDatabaseManager:
    """
    Cloud database manager for DynamoDB operations
    Works alongside your existing MySQL DatabaseManager
    """
    
    def __init__(self):
        try:
            # Initialize DynamoDB resource
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            # Your existing DynamoDB table names from Terraform
            self.customers_table = self.dynamodb.Table('iot-convenience-store-customers-production')
            self.access_logs_table = self.dynamodb.Table('iot-convenience-store-access-logs-production')
            self.sessions_table = self.dynamodb.Table('iot-convenience-store-sessions-production')
            
            print("✅ Cloud database client initialized successfully")
            
        except NoCredentialsError:
            print("❌ AWS credentials not found")
            raise
        except Exception as e:
            print(f"❌ Error initializing cloud database: {e}")
            raise

    def test_connection(self):
        """Test connection to DynamoDB tables"""
        try:
            # Test customers table access
            response = self.customers_table.scan(Limit=1)
            print(f"✅ Customers table accessible: {self.customers_table.name}")
            
            # Test access logs table access
            response = self.access_logs_table.scan(Limit=1)
            print(f"✅ Access logs table accessible: {self.access_logs_table.name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Cloud database connection test failed: {e}")
            return False

    def register_customer(self, registration_data):
        """
        Register a new customer (public registration)
        
        Args:
            registration_data (dict): {
                'name': 'John Doe',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'student_id': 'STU123',  # optional
                'comments': 'Any additional info'  # optional
            }
            
        Returns:
            dict: Success/error response with customer_id
        """
        try:
            # Generate unique customer ID
            customer_id = f"cust_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.utcnow().isoformat()
            
            # Create customer record
            customer_item = {
                'customer_id': customer_id,
                'customer_name': registration_data['name'],
                'email': registration_data['email'],
                'phone': registration_data.get('phone', ''),
                'student_id': registration_data.get('student_id', ''),
                'comments': registration_data.get('comments', ''),
                
                # Registration status workflow
                'registration_status': 'pending',  # pending -> approved -> active
                'membership_status': 'PENDING',     # PENDING -> ACTIVE -> SUSPENDED
                'customer_type': 'REGULAR',         # Default type
                
                # RFID card info (assigned later by admin)
                'rfid_card_uid': '',                # Empty until card assigned
                'card_issued_date': '',             # Empty until card issued
                
                # Access permissions (activated when card issued)
                'access_permissions': [],           # Empty until approved
                'checkout_required': True,          # Default store policy
                
                # Statistics
                'total_spent': 0.0,
                'total_visits': 0,
                'fraud_incidents': 0,
                
                # Timestamps
                'created_at': timestamp,
                'updated_at': timestamp,
                'last_visit': ''
            }
            
            # Save to DynamoDB
            self.customers_table.put_item(Item=customer_item)
            
            print(f"✅ Customer registered successfully: {customer_id}")
            
            return {
                'success': True,
                'customer_id': customer_id,
                'message': 'Registration submitted successfully! You will receive an email when approved.',
                'status': 'pending'
            }
            
        except Exception as e:
            print(f"❌ Error registering customer: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Registration failed. Please try again.'
            }

    def get_pending_registrations(self):
        """Get all pending customer registrations for admin review"""
        try:
            response = self.customers_table.scan(
                FilterExpression='registration_status = :status',
                ExpressionAttributeValues={':status': 'pending'}
            )
            
            registrations = response.get('Items', [])
            print(f"✅ Found {len(registrations)} pending registrations")
            
            return registrations
            
        except Exception as e:
            print(f"❌ Error getting pending registrations: {e}")
            return []

    def approve_registration(self, customer_id, rfid_card_uid):
        """
        Approve a customer registration and assign RFID card
        
        Args:
            customer_id (str): Customer ID to approve
            rfid_card_uid (str): RFID card UID to assign
            
        Returns:
            dict: Success/error response
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Update customer record
            response = self.customers_table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression="""
                    SET registration_status = :approved,
                        membership_status = :active,
                        rfid_card_uid = :rfid_uid,
                        card_issued_date = :issued_date,
                        access_permissions = :permissions,
                        updated_at = :updated
                """,
                ExpressionAttributeValues={
                    ':approved': 'approved',
                    ':active': 'ACTIVE',
                    ':rfid_uid': rfid_card_uid,
                    ':issued_date': timestamp,
                    ':permissions': ['store_entry', 'checkout_bypass'],
                    ':updated': timestamp
                },
                ReturnValues='ALL_NEW'
            )
            
            print(f"✅ Customer {customer_id} approved with card {rfid_card_uid}")
            
            return {
                'success': True,
                'message': 'Customer approved and card assigned successfully!',
                'customer': response['Attributes']
            }
            
        except Exception as e:
            print(f"❌ Error approving registration: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to approve registration.'
            }

    def validate_rfid_access(self, rfid_card_uid):
        """
        Validate RFID card for door access
        
        Args:
            rfid_card_uid (str): RFID card UID to validate
            
        Returns:
            dict: Access validation result
        """
        try:
            # Query by RFID card UID using GSI
            response = self.customers_table.query(
                IndexName='rfid-lookup-index',
                KeyConditionExpression='rfid_card_uid = :uid',
                ExpressionAttributeValues={':uid': rfid_card_uid}
            )
            
            items = response.get('Items', [])
            
            if not items:
                return {
                    'access_granted': False,
                    'reason': 'Card not found',
                    'customer_name': 'Unknown'
                }
            
            customer = items[0]
            
            # Check if customer is active
            if customer.get('membership_status') != 'ACTIVE':
                return {
                    'access_granted': False,
                    'reason': f"Membership {customer.get('membership_status', 'INACTIVE')}",
                    'customer_name': customer.get('customer_name', 'Unknown')
                }
            
            # Check if card is issued
            if not customer.get('card_issued_date'):
                return {
                    'access_granted': False,
                    'reason': 'Card not activated',
                    'customer_name': customer.get('customer_name', 'Unknown')
                }
            
            # Access granted
            return {
                'access_granted': True,
                'reason': 'Access authorized',
                'customer_name': customer.get('customer_name', 'Unknown'),
                'customer_id': customer.get('customer_id'),
                'customer_type': customer.get('customer_type', 'REGULAR')
            }
            
        except Exception as e:
            print(f"❌ Error validating RFID access: {e}")
            return {
                'access_granted': False,
                'reason': 'System error',
                'customer_name': 'Unknown'
            }

    def log_access_attempt(self, rfid_card_uid, access_result, customer_name=None, deny_reason=None):
        """Log access attempt to cloud database"""
        try:
            log_id = f"log_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.utcnow().isoformat()
            
            log_item = {
                'log_id': log_id,
                'timestamp': timestamp,
                'rfid_card_uid': rfid_card_uid,
                'door_node_id': 'door-001',  # Your single door system
                'event_type': 'entry_success' if access_result == 'GRANTED' else 'entry_denied',
                'access_granted': access_result == 'GRANTED',
                'customer_name': customer_name or 'Unknown',
                'deny_reason': deny_reason or '',
                'offline_mode': False
            }
            
            self.access_logs_table.put_item(Item=log_item)
            print(f"✅ Access logged: {access_result} for {customer_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error logging access: {e}")
            return False

    def get_all_customers(self):
        """Get all customers for admin dashboard"""
        try:
            response = self.customers_table.scan()
            customers = response.get('Items', [])
            
            print(f"✅ Retrieved {len(customers)} customers from cloud")
            return customers
            
        except Exception as e:
            print(f"❌ Error getting customers: {e}")
            return []

    def get_recent_access_logs(self, limit=50):
        """Get recent access logs for admin dashboard"""
        try:
            response = self.access_logs_table.scan(Limit=limit)
            logs = response.get('Items', [])
            
            # Sort by timestamp (newest first)
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            print(f"✅ Retrieved {len(logs)} access logs from cloud")
            return logs[:limit]
            
        except Exception as e:
            print(f"❌ Error getting access logs: {e}")
            return []

# Test function
def test_cloud_database():
    """Test cloud database connectivity and basic operations"""
    print("🧪 Testing Cloud Database Connection...")
    print("=" * 50)
    
    try:
        # Initialize client
        cloud_db = CloudDatabaseManager()
        
        # Test connection
        if cloud_db.test_connection():
            print("✅ Cloud database connection successful!")
            
            # Test customer count
            customers = cloud_db.get_all_customers()
            print(f"✅ Found {len(customers)} existing customers")
            
            # Test access logs
            logs = cloud_db.get_recent_access_logs(5)
            print(f"✅ Found {len(logs)} recent access logs")
            
            print("=" * 50)
            print("🎉 All cloud database tests passed!")
            return True
        else:
            print("❌ Cloud database connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Cloud database test error: {e}")
        return False

if __name__ == "__main__":
    # Run tests when file is executed directly
    test_cloud_database()