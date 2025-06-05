#!/usr/bin/env python3
"""
AWS Environment Verification Script
Phase 1 - Step 1.1: Verify AWS credentials and DynamoDB access
"""

import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

class AWSEnvironmentVerifier:
    def __init__(self):
        self.region = 'us-east-1'
        self.tables = {
            'customers': 'iot-convenience-store-customers-production',
            'active_sessions': 'iot-convenience-store-active-sessions-production',
            'sessions': 'iot-convenience-store-sessions-production',
            'transactions': 'iot-convenience-store-transactions-production',
            'fraud_events': 'iot-convenience-store-fraud-events-production',
            'access_logs': 'iot-convenience-store-access-logs-production'
        }
        
    def verify_credentials(self):
        """Verify AWS credentials are properly configured"""
        print("🔐 Verifying AWS Credentials...")
        try:
            sts = boto3.client('sts', region_name=self.region)
            identity = sts.get_caller_identity()
            
            print(f"✅ AWS Credentials Valid")
            print(f"   Account ID: {identity['Account']}")
            print(f"   User/Role: {identity['Arn']}")
            print(f"   Region: {self.region}")
            return True
            
        except NoCredentialsError:
            print("❌ No AWS credentials found")
            print("   Configure credentials using:")
            print("   - aws configure")
            print("   - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
            print("   - IAM role (if running on EC2)")
            return False
            
        except Exception as e:
            print(f"❌ Error verifying credentials: {e}")
            return False
    
    def test_dynamodb_connection(self):
        """Test DynamoDB connection and permissions"""
        print("\n📊 Testing DynamoDB Connection...")
        try:
            dynamodb = boto3.resource('dynamodb', region_name=self.region)
            
            # List tables to verify connection
            client = boto3.client('dynamodb', region_name=self.region)
            tables = client.list_tables()
            
            print(f"✅ DynamoDB Connection Successful")
            print(f"   Available tables: {len(tables['TableNames'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ DynamoDB connection failed: {e}")
            return False
    
    def verify_table_access(self):
        """Verify access to required DynamoDB tables"""
        print("\n🗃️  Verifying Table Access...")
        
        dynamodb = boto3.resource('dynamodb', region_name=self.region)
        results = {}
        
        for table_name, table_full_name in self.tables.items():
            try:
                table = dynamodb.Table(table_full_name)
                
                # Try to get table metadata
                response = table.meta.client.describe_table(TableName=table_full_name)
                table_status = response['Table']['TableStatus']
                item_count = response['Table']['ItemCount']
                
                print(f"✅ {table_name}: {table_status} ({item_count} items)")
                results[table_name] = {
                    'accessible': True,
                    'status': table_status,
                    'item_count': item_count
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    print(f"❌ {table_name}: Table not found")
                    results[table_name] = {'accessible': False, 'error': 'Not found'}
                elif error_code == 'AccessDeniedException':
                    print(f"❌ {table_name}: Access denied")
                    results[table_name] = {'accessible': False, 'error': 'Access denied'}
                else:
                    print(f"❌ {table_name}: {error_code}")
                    results[table_name] = {'accessible': False, 'error': error_code}
            
            except Exception as e:
                print(f"❌ {table_name}: {str(e)}")
                results[table_name] = {'accessible': False, 'error': str(e)}
        
        return results
    
    def test_customer_query(self):
        """Test querying customer data using RFID lookup"""
        print("\n👤 Testing Customer Query...")
        
        try:
            dynamodb = boto3.resource('dynamodb', region_name=self.region)
            customers_table = dynamodb.Table(self.tables['customers'])
            
            # Try to scan for any customer (limited to 1 item for testing)
            response = customers_table.scan(Limit=1)
            
            if response['Items']:
                customer = response['Items'][0]
                print(f"✅ Sample customer found:")
                print(f"   Customer ID: {customer.get('customer_id', 'N/A')}")
                print(f"   Name: {customer.get('customer_name', 'N/A')}")
                print(f"   RFID: {customer.get('rfid_card_uid', 'N/A')}")
                
                # Test RFID lookup using GSI
                rfid_uid = customer.get('rfid_card_uid')
                if rfid_uid:
                    print(f"\n🔍 Testing RFID lookup for: {rfid_uid}")
                    
                    gsi_response = customers_table.query(
                        IndexName='rfid-lookup-index',
                        KeyConditionExpression='rfid_card_uid = :rfid_uid',
                        ExpressionAttributeValues={':rfid_uid': rfid_uid}
                    )
                    
                    if gsi_response['Items']:
                        print(f"✅ RFID lookup successful via GSI")
                        return True
                    else:
                        print(f"❌ RFID lookup failed - GSI may not be configured")
                        return False
                
            else:
                print(f"⚠️  No customers found in table")
                print(f"   Table exists but is empty")
                return True
                
        except Exception as e:
            print(f"❌ Customer query test failed: {e}")
            return False
    
    def test_iot_core_permissions(self):
        """Test IoT Core permissions"""
        print("\n🌐 Testing IoT Core Permissions...")
        
        try:
            iot_client = boto3.client('iot', region_name=self.region)
            
            # Try to list things (should work with basic IoT permissions)
            response = iot_client.list_things(maxResults=1)
            
            print(f"✅ IoT Core accessible")
            print(f"   Things count: {len(response.get('things', []))}")
            
            # Try to list rules
            rules_response = iot_client.list_topic_rules(maxResults=1)
            print(f"   Rules accessible: {len(rules_response.get('rules', []))}")
            
            return True
            
        except Exception as e:
            print(f"❌ IoT Core test failed: {e}")
            return False
    
    def create_test_customer(self):
        """Create a test customer for system testing"""
        print("\n🧪 Creating Test Customer...")
        
        try:
            dynamodb = boto3.resource('dynamodb', region_name=self.region)
            customers_table = dynamodb.Table(self.tables['customers'])
            
            test_customer = {
                'customer_id': 'test_customer_001',
                'customer_name': 'Test User',
                'rfid_card_uid': 'A4F55A07',  # Default test RFID
                'customer_type': 'REGULAR',
                'membership_status': 'ACTIVE',
                'discount_percentage': 0,
                'created_at': datetime.utcnow().isoformat(),
                'total_spent': 0.0,
                'total_visits': 0
            }
            
            # Check if test customer already exists
            existing = customers_table.query(
                IndexName='rfid-lookup-index',
                KeyConditionExpression='rfid_card_uid = :rfid_uid',
                ExpressionAttributeValues={':rfid_uid': test_customer['rfid_card_uid']}
            )
            
            if existing['Items']:
                print(f"✅ Test customer already exists")
                print(f"   RFID: {test_customer['rfid_card_uid']}")
                print(f"   Name: {existing['Items'][0]['customer_name']}")
                return True
            
            # Create new test customer
            customers_table.put_item(Item=test_customer)
            
            print(f"✅ Test customer created successfully")
            print(f"   Customer ID: {test_customer['customer_id']}")
            print(f"   Name: {test_customer['customer_name']}")
            print(f"   RFID: {test_customer['rfid_card_uid']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create test customer: {e}")
            return False
    
    def run_full_verification(self):
        """Run complete verification suite"""
        print("🚀 AWS Environment Verification")
        print("=" * 50)
        
        all_passed = True
        
        # Step 1: Credentials
        if not self.verify_credentials():
            return False
        
        # Step 2: DynamoDB Connection
        if not self.test_dynamodb_connection():
            return False
        
        # Step 3: Table Access
        table_results = self.verify_table_access()
        customers_accessible = table_results.get('customers', {}).get('accessible', False)
        
        if not customers_accessible:
            print(f"\n❌ Critical: Customers table not accessible")
            all_passed = False
        
        # Step 4: Customer Query Test
        if customers_accessible:
            if not self.test_customer_query():
                all_passed = False
        
        # Step 5: IoT Core Test
        if not self.test_iot_core_permissions():
            all_passed = False
        
        # Step 6: Create Test Data
        if customers_accessible:
            if not self.create_test_customer():
                all_passed = False
        
        print("\n" + "=" * 50)
        if all_passed:
            print("✅ All verification tests passed!")
            print("🎯 Ready to proceed with Phase 2")
        else:
            print("❌ Some verification tests failed")
            print("🔧 Please fix issues before proceeding")
        
        return all_passed

def main():
    verifier = AWSEnvironmentVerifier()
    success = verifier.run_full_verification()
    
    if success:
        print(f"\n📋 Next Steps:")
        print(f"1. Proceed to Phase 2: Arduino Simplification")
        print(f"2. Test RFID scan with card: A4F55A07")
        print(f"3. Monitor system logs during testing")
    else:
        print(f"\n🛠️  Required Actions:")
        print(f"1. Fix AWS credential configuration")
        print(f"2. Ensure DynamoDB tables exist")
        print(f"3. Verify IAM permissions")
        print(f"4. Re-run this verification script")

if __name__ == "__main__":
    main()
