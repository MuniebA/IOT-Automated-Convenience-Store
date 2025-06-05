#!/usr/bin/env python3
"""
Script to debug and fix checkout completion in active sessions table
"""

import boto3
import json
import os
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_active_sessions_table():
    """Check the current state of active sessions table"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # We need to find the correct table name first
        client = boto3.client('dynamodb', region_name='us-east-1')
        tables = client.list_tables()['TableNames']
        
        # Look for active sessions table
        active_table = None
        for table_name in tables:
            if 'active' in table_name.lower() and 'session' in table_name.lower():
                active_table = table_name
                break
        
        if not active_table:
            print("❌ No active sessions table found!")
            print("Available tables:")
            for table in tables:
                print(f"  - {table}")
            return None
        
        print(f"✅ Found active sessions table: {active_table}")
        
        # Scan the table to see current sessions
        table = dynamodb.Table(active_table)
        response = table.scan()
        
        print(f"\n📊 Current sessions in {active_table}:")
        sessions = response.get('Items', [])
        
        if not sessions:
            print("  No sessions found")
            return active_table
        
        for session in sessions:
            print(f"\n  📋 Session: {session.get('session_id', 'N/A')}")
            print(f"     Customer: {session.get('customer_name', 'N/A')}")
            print(f"     Customer ID: {session.get('customer_id', 'N/A')}")
            print(f"     Cart: {session.get('assigned_cart', 'N/A')}")
            print(f"     Checkout Completed: {session.get('checkout_completed', 'NOT_SET')}")
            print(f"     Entry Time: {session.get('entry_time', 'N/A')}")
        
        return active_table
        
    except Exception as e:
        print(f"❌ Error checking active sessions: {e}")
        return None

def update_checkout_status(table_name, customer_id, checkout_completed=True):
    """Manually update checkout status for testing"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table(table_name)
        
        print(f"\n🔄 Updating checkout status for customer: {customer_id}")
        
        # Try to update without condition first
        response = table.update_item(
            Key={'customer_id': customer_id},
            UpdateExpression='SET checkout_completed = :completed, checkout_time = :checkout_time, last_activity = :timestamp',
            ExpressionAttributeValues={
                ':completed': checkout_completed,
                ':checkout_time': datetime.utcnow().isoformat(),
                ':timestamp': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        print(f"✅ Successfully updated checkout status!")
        print(f"Updated item: {json.dumps(response['Attributes'], indent=2, default=str)}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating checkout status: {e}")
        return False

def test_lambda_checkout_update():
    """Test the checkout update like the Lambda function does"""
    try:
        # Get active sessions first
        table_name = check_active_sessions_table()
        if not table_name:
            return
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table(table_name)
        
        # Get all sessions
        response = table.scan()
        sessions = response.get('Items', [])
        
        if not sessions:
            print("\n❌ No sessions to test with")
            return
        
        # Test with the first session
        session = sessions[0]
        customer_id = session.get('customer_id')
        
        if not customer_id:
            print("\n❌ No customer_id found in session")
            return
        
        print(f"\n🧪 Testing Lambda-style update for customer: {customer_id}")
        
        # Simulate what the Lambda function does
        total_amount = Decimal('70.0')
        items = [
            {'product_name': 'Test Item 1', 'price': Decimal('35.0')},
            {'product_name': 'Test Item 2', 'price': Decimal('35.0')}
        ]
        
        # Try the Lambda function's update method
        try:
            table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression='''
                    SET checkout_completed = :completed,
                        total_amount = :amount,
                        #items = :items,
                        checkout_time = :checkout_time,
                        last_activity = :timestamp
                ''',
                ExpressionAttributeNames={
                    '#items': 'items'
                },
                ExpressionAttributeValues={
                    ':completed': True,
                    ':amount': total_amount,
                    ':items': items,
                    ':checkout_time': datetime.utcnow().isoformat(),
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
            print("✅ Lambda-style update successful!")
            
        except Exception as lambda_err:
            print(f"❌ Lambda-style update failed: {lambda_err}")
            
            # Try simpler update
            print("🔄 Trying simpler update...")
            table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression='SET checkout_completed = :completed',
                ExpressionAttributeValues={':completed': True}
            )
            print("✅ Simple update successful!")
        
        # Check the result
        print("\n📊 Final state after update:")
        check_active_sessions_table()
        
    except Exception as e:
        print(f"❌ Error in test: {e}")

if __name__ == "__main__":
    print("🔍 Active Sessions Checkout Debug")
    print("=" * 50)
    
    # Step 1: Check current state
    table_name = check_active_sessions_table()
    
    if table_name:
        print("\n" + "=" * 50)
        print("🧪 TESTING CHECKOUT UPDATE")
        
        # Step 2: Test the update
        test_lambda_checkout_update()
        
        print("\n" + "=" * 50)
        print("📋 RECOMMENDATIONS:")
        print("1. If the update worked, the checkout_completed should now be True")
        print("2. Try your exit flow - it should now allow exit")
        print("3. If it still fails, check the Lambda function logs in AWS CloudWatch")
    else:
        print("\n❌ Cannot proceed without finding the active sessions table")
