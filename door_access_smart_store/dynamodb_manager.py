#!/usr/bin/env python3
"""
DynamoDB Manager for Cloud-Direct Door Access System
NOW WITH UID NORMALIZATION SUPPORT
"""

import boto3
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

class DynamoDBManager:
    def __init__(self, region='us-east-1'):
        """Initialize DynamoDB manager with AWS credentials"""
        self.region = region
        
        # Table names (production environment)
        self.tables = {
            'customers': 'iot-convenience-store-customers-production',
            'active_sessions': 'iot-convenience-store-active-sessions-production', 
            'sessions': 'iot-convenience-store-sessions-production',
            'transactions': 'iot-convenience-store-transactions-production',
            'fraud_events': 'iot-convenience-store-fraud-events-production',
            'access_logs': 'iot-convenience-store-access-logs-production'
        }
        
        try:
            # Initialize DynamoDB resource
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            
            # Test connection
            self._test_connection()
            logger.info("✅ DynamoDB Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DynamoDB: {e}")
            raise
    
    def _test_connection(self):
        """Test DynamoDB connection"""
        try:
            # Simple test - list tables
            client = boto3.client('dynamodb', region_name=self.region)
            client.list_tables(Limit=1)
            return True
        except Exception as e:
            raise Exception(f"DynamoDB connection test failed: {e}")
    
    def _normalize_uid(self, uid):
        """
        ADDED: Normalize RFID UID to handle different formats
        Converts formats like '63 99 C2 2F' to '6399C22F'
        """
        if not uid:
            return None
        
        # Convert to string and strip whitespace
        uid_str = str(uid).strip()
        
        # Remove common prefixes
        if uid_str.lower().startswith('0x'):
            uid_str = uid_str[2:]
        
        # Remove all separators (spaces, colons, dashes, dots)
        import re
        normalized = re.sub(r'[:\s\-\.]', '', uid_str)
        
        # Convert to uppercase
        normalized = normalized.upper()
        
        # Validate that it's a valid hex string
        if not re.match(r'^[0-9A-F]+$', normalized):
            logger.warning(f"Invalid UID format: {normalized}")
            return None
        
        # Pad with leading zeros if needed (common RFID UIDs are 8 characters)
        if len(normalized) < 8:
            normalized = normalized.zfill(8)
        
        logger.debug(f"Normalized UID: '{uid}' → '{normalized}'")
        return normalized
    
    def _generate_uid_variants(self, uid):
        """
        ADDED: Generate different UID format variants for lookup
        """
        normalized = self._normalize_uid(uid)
        if not normalized:
            return [uid]  # Return original if normalization fails
        
        # Generate common variants
        variants = [
            normalized,  # 6399C22F
            normalized.lower(),  # 6399c22f
            ' '.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]),  # 63 99 C2 2F
            ':'.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]),  # 63:99:C2:2F
            '-'.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]),  # 63-99-C2-2F
        ]
        
        # Add spaced lowercase variant
        spaced_lower = ' '.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]).lower()
        variants.append(spaced_lower)
        
        # Remove duplicates while preserving order
        unique_variants = []
        for variant in variants:
            if variant not in unique_variants:
                unique_variants.append(variant)
        
        return unique_variants
    
    def get_customer_by_rfid(self, rfid_uid):
        """ENHANCED: Get customer information by RFID UID with format handling"""
        try:
            customers_table = self.dynamodb.Table(self.tables['customers'])
            
            logger.info(f"🔍 Looking up customer with RFID: {rfid_uid}")
            
            # Generate all possible UID variants
            uid_variants = self._generate_uid_variants(rfid_uid)
            logger.debug(f"Trying {len(uid_variants)} UID variants: {uid_variants}")
            
            # Try each variant until we find a match
            for i, variant_uid in enumerate(uid_variants):
                try:
                    # Query using RFID lookup GSI
                    response = customers_table.query(
                        IndexName='rfid-lookup-index',
                        KeyConditionExpression='rfid_card_uid = :rfid_uid',
                        ExpressionAttributeValues={':rfid_uid': variant_uid}
                    )
                    
                    customers = response.get('Items', [])
                    
                    if customers:
                        customer = customers[0]  # Should be unique
                        logger.info(f"✅ Customer found with UID format '{variant_uid}': {customer.get('customer_name', 'Unknown')}")
                        
                        # Convert Decimal types for JSON serialization
                        customer_data = self._convert_decimals(customer)
                        
                        return {
                            'found': True,
                            'customer_id': customer_data.get('customer_id'),
                            'customer_name': customer_data.get('customer_name', 'Unknown'),
                            'rfid_card_uid': customer_data.get('rfid_card_uid'),
                            'customer_type': customer_data.get('customer_type', 'REGULAR'),
                            'membership_status': customer_data.get('membership_status', 'ACTIVE'),
                            'discount_percentage': customer_data.get('discount_percentage', 0),
                            'total_spent': customer_data.get('total_spent', 0.0),
                            'total_visits': customer_data.get('total_visits', 0),
                            'matched_format': variant_uid,  # ADDED: Track which format worked
                            'original_input': rfid_uid      # ADDED: Track original input
                        }
                
                except Exception as e:
                    logger.debug(f"Error trying UID variant '{variant_uid}': {e}")
                    continue
            
            # No customer found with any variant
            logger.warning(f"❌ No customer found with any UID variant of: {rfid_uid}")
            return {
                'found': False,
                'rfid_card_uid': rfid_uid,
                'reason': 'RFID not registered (tried multiple formats)',
                'variants_tried': uid_variants
            }
                
        except Exception as e:
            logger.error(f"❌ Error looking up customer by RFID: {e}")
            return {
                'found': False,
                'rfid_card_uid': rfid_uid,
                'reason': 'Database error',
                'error': str(e)
            }
    
    def create_customer(self, customer_name, rfid_uid, customer_type='REGULAR'):
        """ENHANCED: Create new customer in DynamoDB with normalized UID"""
        try:
            customers_table = self.dynamodb.Table(self.tables['customers'])
            
            # ADDED: Normalize the UID before storing
            normalized_uid = self._normalize_uid(rfid_uid)
            if not normalized_uid:
                logger.error(f"❌ Invalid UID format: {rfid_uid}")
                return {
                    'success': False,
                    'reason': 'Invalid UID format',
                    'original_uid': rfid_uid
                }
            
            logger.info(f"📝 Creating customer with normalized UID: '{rfid_uid}' → '{normalized_uid}'")
            
            # Check if RFID already exists (using variant matching)
            existing = self.get_customer_by_rfid(normalized_uid)
            if existing['found']:
                logger.warning(f"⚠️  Customer with RFID {normalized_uid} already exists")
                return {
                    'success': False,
                    'reason': 'RFID already registered',
                    'existing_customer': existing['customer_name'],
                    'original_uid': rfid_uid,
                    'normalized_uid': normalized_uid
                }
            
            # Generate customer ID
            customer_id = f"cust_{uuid.uuid4().hex[:8]}"
            
            # Create customer record with normalized UID
            customer_data = {
                'customer_id': customer_id,
                'customer_name': customer_name,
                'rfid_card_uid': normalized_uid,  # CHANGED: Store normalized UID
                'customer_type': customer_type,
                'membership_status': 'ACTIVE',
                'discount_percentage': Decimal('0'),
                'created_at': datetime.utcnow().isoformat(),
                'total_spent': Decimal('0.0'),
                'total_visits': 0,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            customers_table.put_item(Item=customer_data)
            
            logger.info(f"✅ Created customer: {customer_name} ({customer_id}) with UID: {normalized_uid}")
            
            return {
                'success': True,
                'customer_id': customer_id,
                'customer_name': customer_name,
                'rfid_uid': normalized_uid,
                'original_uid': rfid_uid
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating customer: {e}")
            return {
                'success': False,
                'reason': 'Database error',
                'error': str(e)
            }
    
    # ALL OTHER METHODS REMAIN THE SAME...
    # (keeping the rest of your existing methods unchanged)
    
    def check_customer_active_session(self, customer_id):
        """Check if customer has an active session"""
        try:
            active_sessions_table = self.dynamodb.Table(self.tables['active_sessions'])
            
            logger.info(f"🔍 Checking active session for customer: {customer_id}")
            
            response = active_sessions_table.get_item(
                Key={'customer_id': customer_id}
            )
            
            if 'Item' in response:
                session = self._convert_decimals(response['Item'])
                logger.info(f"✅ Active session found: {session.get('session_id')}")
                return session
            else:
                logger.info(f"ℹ️  No active session for customer: {customer_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error checking active session: {e}")
            return None
    
    def log_access_event(self, customer_id, rfid_uid, event_type, customer_name="Unknown", details=""):
        """Log access event to DynamoDB access logs"""
        try:
            access_logs_table = self.dynamodb.Table(self.tables['access_logs'])
            
            # ADDED: Normalize UID for consistent logging
            normalized_uid = self._normalize_uid(rfid_uid)
            log_uid = normalized_uid if normalized_uid else rfid_uid
            
            log_id = f"access_{uuid.uuid4().hex[:8]}"
            
            log_entry = {
                'log_id': log_id,
                'timestamp': datetime.utcnow().isoformat(),
                'customer_id': customer_id if customer_id else 'unknown',
                'rfid_card_uid': log_uid,
                'door_node_id': 'door-001',
                'event_type': event_type,
                'access_granted': event_type in ['ENTRY_SUCCESS', 'EXIT_SUCCESS'],
                'deny_reason': details if event_type.endswith('_DENIED') else None,
                'customer_name': customer_name,
                'store_id': 'store-001'
            }
            
            access_logs_table.put_item(Item=log_entry)
            logger.info(f"📝 Logged access event: {event_type} for {customer_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging access event: {e}")
            return False
    
    def get_recent_access_logs(self, limit=50):
        """Get recent access logs for dashboard"""
        try:
            access_logs_table = self.dynamodb.Table(self.tables['access_logs'])
            
            response = access_logs_table.scan(Limit=limit)
            logs = response.get('Items', [])
            
            # Convert and sort by timestamp
            formatted_logs = []
            for log in logs:
                log_data = self._convert_decimals(log)
                formatted_logs.append(log_data)
            
            # Sort by timestamp (newest first)
            formatted_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return formatted_logs[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error getting access logs: {e}")
            return []
    
    def get_all_customers(self):
        """Get all customers for management interface"""
        try:
            customers_table = self.dynamodb.Table(self.tables['customers'])
            
            response = customers_table.scan()
            customers = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = customers_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                customers.extend(response.get('Items', []))
            
            # Convert decimals and format
            formatted_customers = []
            for customer in customers:
                customer_data = self._convert_decimals(customer)
                formatted_customers.append(customer_data)
            
            # Sort by creation date (newest first)
            formatted_customers.sort(
                key=lambda x: x.get('created_at', ''), 
                reverse=True
            )
            
            logger.info(f"📋 Retrieved {len(formatted_customers)} customers")
            return formatted_customers
            
        except Exception as e:
            logger.error(f"❌ Error getting all customers: {e}")
            return []
    
    def get_system_stats(self):
        """Get system statistics for dashboard"""
        try:
            # Get recent logs for stats
            recent_logs = self.get_recent_access_logs(100)
            
            # Calculate stats
            now = datetime.utcnow()
            
            stats = {
                'total_customers': len(self.get_all_customers()),
                'total_access_today': 0,
                'successful_access_today': 0,
                'denied_access_today': 0,
                'total_access_week': 0,
                'last_activity': None
            }
            
            for log in recent_logs:
                try:
                    log_time = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                    
                    # Today's stats
                    if log_time.date() == now.date():
                        stats['total_access_today'] += 1
                        if log.get('access_granted', False):
                            stats['successful_access_today'] += 1
                        else:
                            stats['denied_access_today'] += 1
                    
                    # Week's stats
                    if (now - log_time).days <= 7:
                        stats['total_access_week'] += 1
                    
                    # Last activity
                    if not stats['last_activity'] or log_time > datetime.fromisoformat(stats['last_activity']):
                        stats['last_activity'] = log.get('timestamp')
                        
                except Exception:
                    continue  # Skip invalid timestamps
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting system stats: {e}")
            return {
                'total_customers': 0,
                'total_access_today': 0,
                'successful_access_today': 0,
                'denied_access_today': 0,
                'total_access_week': 0,
                'last_activity': None
            }
    
    def _convert_decimals(self, obj):
        """Convert DynamoDB Decimal types to Python float/int for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, Decimal):
            # Convert to int if it's a whole number, otherwise float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        else:
            return obj

# Test function
def test_uid_normalization():
    """Test the UID normalization with various formats"""
    print("🧪 Testing UID Normalization in DynamoDB Manager")
    print("=" * 50)
    
    try:
        # Initialize manager
        db = DynamoDBManager()
        
        # Test different UID formats
        test_uids = [
            'A4F55A07',      # Normal format
            'A4 F5 5A 07',   # Spaced format
            'a4:f5:5a:07',   # Lowercase with colons
            '63 99 C2 2F',   # Your example with spaces
        ]
        
        for test_uid in test_uids:
            print(f"\n🔍 Testing UID: '{test_uid}'")
            customer = db.get_customer_by_rfid(test_uid)
            
            if customer['found']:
                print(f"   ✅ Found: {customer['customer_name']}")
                print(f"   📝 Matched: '{customer['matched_format']}'")
            else:
                print(f"   ❌ Not found")
                print(f"   📝 Tried: {len(customer['variants_tried'])} formats")
        
        print("\n✅ UID normalization test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_uid_normalization()
