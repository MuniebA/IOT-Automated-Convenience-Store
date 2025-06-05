#!/usr/bin/env python3
"""
RFID UID Normalizer
Handles different RFID UID formats and normalizes them for consistent lookup
"""

import re
import logging

logger = logging.getLogger(__name__)

class RFIDUIDNormalizer:
    """Handle different RFID UID formats for consistent database lookup"""
    
    @staticmethod
    def normalize_uid(uid):
        """
        Normalize RFID UID to consistent format: uppercase, no separators
        
        Input formats supported:
        - '63 99 C2 2F' (spaces)
        - '63:99:C2:2F' (colons)
        - '63-99-C2-2F' (dashes)
        - '6399C22F' (no separators)
        - '6399c22f' (lowercase)
        - '0x6399C22F' (hex prefix)
        
        Output format: '6399C22F' (uppercase, no separators)
        """
        if not uid:
            return None
        
        # Convert to string and strip whitespace
        uid_str = str(uid).strip()
        
        # Remove common prefixes
        if uid_str.lower().startswith('0x'):
            uid_str = uid_str[2:]
        
        # Remove all separators (spaces, colons, dashes, dots)
        normalized = re.sub(r'[:\s\-\.]', '', uid_str)
        
        # Convert to uppercase
        normalized = normalized.upper()
        
        # Validate that it's a valid hex string
        if not re.match(r'^[0-9A-F]+$', normalized):
            logger.warning(f"Invalid UID format after normalization: {normalized}")
            return None
        
        # Pad with leading zeros if needed (common RFID UIDs are 8 characters)
        if len(normalized) < 8:
            normalized = normalized.zfill(8)
        
        logger.debug(f"Normalized UID: '{uid}' → '{normalized}'")
        return normalized
    
    @staticmethod
    def generate_uid_variants(uid):
        """
        Generate all possible variants of a UID for database search
        Useful for finding UIDs stored in different formats
        """
        normalized = RFIDUIDNormalizer.normalize_uid(uid)
        if not normalized:
            return []
        
        # Generate common variants
        variants = [
            normalized,  # 6399C22F
            normalized.lower(),  # 6399c22f
            ' '.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]),  # 63 99 C2 2F
            ':'.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]),  # 63:99:C2:2F
            '-'.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]),  # 63-99-C2-2F
            f"0x{normalized}",  # 0x6399C22F
            f"0x{normalized.lower()}",  # 0x6399c22f
        ]
        
        # Add spaced lowercase variant
        variants.append(' '.join([normalized[i:i+2] for i in range(0, len(normalized), 2)]).lower())
        
        # Remove duplicates while preserving order
        unique_variants = []
        for variant in variants:
            if variant not in unique_variants:
                unique_variants.append(variant)
        
        return unique_variants

def test_uid_normalizer():
    """Test the UID normalizer with various formats"""
    print("🧪 Testing RFID UID Normalizer")
    print("=" * 50)
    
    test_cases = [
        '63 99 C2 2F',  # Spaces
        '63:99:C2:2F',  # Colons
        '63-99-C2-2F',  # Dashes
        '6399C22F',     # No separators
        '6399c22f',     # Lowercase
        '0x6399C22F',   # Hex prefix
        '0x6399c22f',   # Hex prefix lowercase
        'A4 F5 5A 07',  # Your test card
        'A4F55A07',     # Your test card normalized
        '  63 99 C2 2F  ',  # With extra whitespace
    ]
    
    normalizer = RFIDUIDNormalizer()
    
    for test_uid in test_cases:
        normalized = normalizer.normalize_uid(test_uid)
        variants = normalizer.generate_uid_variants(test_uid)
        
        print(f"Input:      '{test_uid}'")
        print(f"Normalized: '{normalized}'")
        print(f"Variants:   {len(variants)} formats")
        print("-" * 30)
    
    print("\n✅ UID Normalizer test completed!")

# Integration functions for existing system

def normalize_uid_for_lookup(uid):
    """Simple function to normalize UID for database lookup"""
    return RFIDUIDNormalizer.normalize_uid(uid)

def enhanced_customer_lookup(db_manager, rfid_uid):
    """
    Enhanced customer lookup that tries multiple UID formats
    Use this instead of direct DynamoDB lookup
    """
    normalizer = RFIDUIDNormalizer()
    
    # Get all possible variants of the UID
    uid_variants = normalizer.generate_uid_variants(rfid_uid)
    
    logger.info(f"🔍 Searching for customer with UID variants: {uid_variants[:3]}...")
    
    # Try each variant until we find a match
    for variant_uid in uid_variants:
        try:
            customer = db_manager.get_customer_by_rfid(variant_uid)
            if customer['found']:
                logger.info(f"✅ Customer found with UID format: '{variant_uid}'")
                return customer
        except Exception as e:
            logger.debug(f"Error trying UID variant '{variant_uid}': {e}")
            continue
    
    # No customer found with any variant
    logger.warning(f"❌ No customer found for any UID variant of: {rfid_uid}")
    return {
        'found': False,
        'rfid_card_uid': rfid_uid,
        'reason': 'RFID not registered (tried multiple formats)',
        'variants_tried': len(uid_variants)
    }

def update_existing_uids_in_database(db_manager):
    """
    Utility function to normalize existing UIDs in database
    Run this once to clean up existing data
    """
    print("🔧 Normalizing existing UIDs in database...")
    
    try:
        # Get all customers
        customers = db_manager.get_all_customers()
        normalizer = RFIDUIDNormalizer()
        
        updated_count = 0
        
        for customer in customers:
            current_uid = customer.get('rfid_card_uid')
            if not current_uid:
                continue
            
            normalized_uid = normalizer.normalize_uid(current_uid)
            
            if normalized_uid and normalized_uid != current_uid:
                print(f"Normalizing: '{current_uid}' → '{normalized_uid}'")
                
                # In a real implementation, you'd update the customer record
                # customer['rfid_card_uid'] = normalized_uid
                # db_manager.update_customer(customer)
                
                updated_count += 1
        
        print(f"✅ Found {updated_count} UIDs that need normalization")
        print("   Run the actual update function to apply changes")
        
    except Exception as e:
        print(f"❌ Error normalizing UIDs: {e}")

if __name__ == "__main__":
    test_uid_normalizer()
