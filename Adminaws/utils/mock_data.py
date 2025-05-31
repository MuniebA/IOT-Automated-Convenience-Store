from datetime import datetime, timedelta
import random


def get_mock_customers():
    """Mock customer data for testing"""
    return [
        {
            'customer_id': 'cust_001',
            'customer_name': 'John Doe',
            'customer_type': 'VIP',
            'rfid_card_uid': 'ABC123456789',
            'total_spent': 1250.75,
            'total_visits': 45,
            'last_visit': '2024-05-30T14:30:00Z',
            'membership_status': 'ACTIVE'
        },
        {
            'customer_id': 'cust_002',
            'customer_name': 'Jane Smith',
            'customer_type': 'REGULAR',
            'rfid_card_uid': 'DEF987654321',
            'total_spent': 567.20,
            'total_visits': 23,
            'last_visit': '2024-05-29T16:45:00Z',
            'membership_status': 'ACTIVE'
        },
        {
            'customer_id': 'cust_003',
            'customer_name': 'Alice Johnson',
            'customer_type': 'EMPLOYEE',
            'rfid_card_uid': 'GHI555666777',
            'total_spent': 234.50,
            'total_visits': 12,
            'last_visit': '2024-05-28T09:15:00Z',
            'membership_status': 'ACTIVE'
        }
    ]


def get_mock_analytics():
    """Mock analytics data for dashboard"""
    return {
        'total_customers': 156,
        'active_sessions': 8,
        'total_sales_today': 2847.50,
        'fraud_alerts': 3,
        'daily_sales': [
            {'date': '2024-05-25', 'sales': 1200.50},
            {'date': '2024-05-26', 'sales': 1450.75},
            {'date': '2024-05-27', 'sales': 1680.25},
            {'date': '2024-05-28', 'sales': 1234.00},
            {'date': '2024-05-29', 'sales': 1890.30},
            {'date': '2024-05-30', 'sales': 2147.80},
            {'date': '2024-05-31', 'sales': 2847.50}
        ],
        'fraud_events': [
            {'type': 'unscanned_item', 'count': 12},
            {'type': 'weight_mismatch', 'count': 8},
            {'type': 'multiple_items', 'count': 5},
            {'type': 'no_placement', 'count': 15}
        ]
    }


def get_mock_stores():
    """Mock store data"""
    return [
        {
            'store_id': 'store_001',
            'store_name': 'Main Campus Store',
            'location': 'Building A, Floor 1',
            'status': 'ACTIVE',
            'devices': {
                'smart_carts': 3,
                'door_access': 1,
                'smart_shelves': 2
            },
            'daily_revenue': 2847.50,
            'customer_count': 89
        }
    ]


def get_mock_recent_transactions():
    """Mock recent transactions"""
    return [
        {
            'transaction_id': 'trans_001',
            'customer_name': 'John Doe',
            'amount': 45.67,
            'items': 5,
            'timestamp': '2024-05-31T15:30:00Z',
            'status': 'completed'
        },
        {
            'transaction_id': 'trans_002',
            'customer_name': 'Jane Smith',
            'amount': 23.45,
            'items': 3,
            'timestamp': '2024-05-31T15:25:00Z',
            'status': 'completed'
        },
        {
            'transaction_id': 'trans_003',
            'customer_name': 'Alice Johnson',
            'amount': 67.89,
            'items': 8,
            'timestamp': '2024-05-31T15:20:00Z',
            'status': 'completed'
        }
    ]
