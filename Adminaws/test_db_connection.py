#!/usr/bin/env python3
"""
Test script to verify DynamoDB connectivity
Run this on your EC2 instance to debug connection issues
"""
import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError


def test_dynamodb_connection():
    print("🔍 Testing DynamoDB Connection...")

    # Check environment variables
    print(f"AWS_REGION: {os.environ.get('AWS_REGION', 'NOT SET')}")
    print(
        f"AWS_ACCESS_KEY_ID: {'SET' if os.environ.get('AWS_ACCESS_KEY_ID') else 'NOT SET'}")
    print(
        f"AWS_SECRET_ACCESS_KEY: {'SET' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")

    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )

        # Test table names from your system
        table_names = [
            'iot-convenience-store-customers-production',
            'iot-convenience-store-products-production',
            'iot-convenience-store-sessions-production',
            'iot-convenience-store-transactions-production',
            'iot-convenience-store-fraud-events-production',
            'iot-convenience-store-access-logs-production',
            'iot-convenience-store-system-nodes-production',
            'iot-convenience-store-active-sessions-production'
        ]

        print("\n📊 Testing Table Connections:")
        successful_tables = 0

        for table_name in table_names:
            try:
                table = dynamodb.Table(table_name)
                table.load()
                print(f"✅ {table_name}: Connected")

                # Try to get item count
                response = table.scan(Select='COUNT', Limit=1)
                count = response.get('Count', 0)
                print(f"   📈 Contains {count}+ items")
                successful_tables += 1

            except ClientError as e:
                error_code = e.response['Error']['Code']
                print(
                    f"❌ {table_name}: {error_code} - {e.response['Error']['Message']}")
            except Exception as e:
                print(f"❌ {table_name}: {str(e)}")

        print(
            f"\n📋 Summary: {successful_tables}/{len(table_names)} tables accessible")

        if successful_tables == 0:
            print("🚨 No tables accessible - check AWS credentials and permissions")
            return False
        elif successful_tables < len(table_names):
            print(
                "⚠️ Some tables inaccessible - application may have limited functionality")
            return True
        else:
            print("✅ All tables accessible - database connection is healthy")
            return True

    except NoCredentialsError:
        print("❌ AWS credentials not found or invalid")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_dynamodb_connection()
