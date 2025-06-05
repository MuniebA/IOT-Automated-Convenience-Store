#!/usr/bin/env python3
"""
Debug script to check DynamoDB tables and test the active session route
"""

import boto3
import json
from datetime import datetime

def list_dynamodb_tables():
    """List all DynamoDB tables in the account"""
    try:
        dynamodb = boto3.client('dynamodb')
        response = dynamodb.list_tables()
        
        print("=== DynamoDB Tables ===")
        for table_name in response['TableNames']:
            print(f"  - {table_name}")
        
        return response['TableNames']
    except Exception as e:
        print(f"Error listing tables: {e}")
        return []

def check_active_sessions_table():
    """Check for active sessions tables and their contents"""
    tables = list_dynamodb_tables()
    
    # Look for tables that might be the active sessions table
    possible_tables = [t for t in tables if 'active' in t.lower() or 'session' in t.lower()]
    
    print(f"\n=== Possible Active Sessions Tables ===")
    for table in possible_tables:
        print(f"  - {table}")
        
        try:
            dynamodb = boto3.resource('dynamodb')
            table_resource = dynamodb.Table(table)
            
            # Scan the table to see its contents
            response = table_resource.scan(Limit=5)
            items = response.get('Items', [])
            
            print(f"    Items in table ({len(items)} shown, {response.get('Count', 0)} total):")
            for item in items:
                print(f"      {json.dumps(item, indent=6, default=str)}")
                
        except Exception as e:
            print(f"    Error reading table {table}: {e}")
    
    return possible_tables

def test_check_active_session_route():
    """Test the Flask route directly"""
    import requests
    
    try:
        response = requests.get('http://localhost:5000/check_active_session')
        print(f"\n=== /check_active_session Route Test ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"\n=== Route Test Failed ===")
        print(f"Error: {e}")
        print("Make sure Flask app is running on http://localhost:5000")

if __name__ == "__main__":
    print("🔍 DynamoDB Debug Script")
    print("=" * 50)
    
    # Step 1: List all tables
    list_dynamodb_tables()
    
    # Step 2: Check for active sessions
    possible_tables = check_active_sessions_table()
    
    # Step 3: Test the route
    test_check_active_session_route()
    
    print("\n" + "=" * 50)
    print("📋 RECOMMENDATIONS:")
    
    if not possible_tables:
        print("❌ No active sessions table found!")
        print("   Create the table or check your table names in app.py")
    else:
        print(f"✅ Found {len(possible_tables)} possible active sessions table(s)")
        print("   Update your app.py route to use the correct table name:")
        for table in possible_tables:
            print(f"     active_sessions_table = dynamodb.Table('{table}')")
