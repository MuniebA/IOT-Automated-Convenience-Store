import json
import time
import logging
from datetime import datetime
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartCartMQTT:
    def __init__(self):
        self.endpoint = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com"
        self.client_id = "basicPubSub"  # or "smart-convenience-store-cart-001"
        self.thing_name = "iot-convenience-store-door-001-production"
        
        # Updated certificate paths to match your files
        self.root_ca = "./AmazonRootCA1.pem"
        self.certificate = "./iot-convenience-store-door-001-production.cert.pem"
        self.private_key = "./iot-convenience-store-door-001-production.private.key"
        
        # MQTT topic
        self.session_topic = f"store/cart/{self.thing_name}/session/complete"
        
        # MQTT client
        self.mqtt_client = None
        self.connected = False
    
    def connect(self):
        """Connect to AWS IoT Core"""
        try:
            logger.info("🔌 Connecting to AWS IoT Core...")
            
            # Create MQTT client
            self.mqtt_client = AWSIoTMQTTClient(self.client_id)
            self.mqtt_client.configureEndpoint(self.endpoint, 8883)
            self.mqtt_client.configureCredentials(self.root_ca, self.private_key, self.certificate)
            
            # Configure connection
            self.mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
            self.mqtt_client.configureOfflinePublishQueueing(-1)
            self.mqtt_client.configureDrainingFrequency(2)
            self.mqtt_client.configureConnectDisconnectTimeout(10)
            self.mqtt_client.configureMQTTOperationTimeout(5)
            
            # Connect
            if self.mqtt_client.connect():
                self.connected = True
                logger.info("✅ Connected to AWS IoT Core!")
                return True
            else:
                logger.error("❌ Failed to connect")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection error: {str(e)}")
            return False
    
    def publish_session_complete(self, session_data):
        """Publish session completion data"""
        if not self.connected:
            logger.error("❌ Not connected to IoT Core")
            return False
            
        try:
            # Add timestamp
            message = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "session_complete",
                "cart_id": self.thing_name,
                **session_data
            }
            
            # Publish message
            self.mqtt_client.publish(self.session_topic, json.dumps(message), 1)
            logger.info(f"📤 Published session completion: {session_data.get('session_id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Publish error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from AWS IoT Core"""
        if self.mqtt_client and self.connected:
            self.mqtt_client.disconnect()
            self.connected = False
            logger.info("✅ Disconnected from AWS IoT Core")

# Test function
def test_mqtt_connection():
    """Test MQTT connectivity"""
    mqtt = SmartCartMQTT()
    
    # Test connection
    if mqtt.connect():
        print("🎉 MQTT connection successful!")
        
        # Test message
        test_session = {
            "session_id": "test_session_123",
            "customer_name": "Test Customer",
            "total_amount": 25.50,
            "items": ["Apple", "Banana"],
            "fraud_events": []
        }
        
        if mqtt.publish_session_complete(test_session):
            print("🎉 Test message sent successfully!")
        
        mqtt.disconnect()
        return True
    else:
        print("❌ MQTT connection failed")
        return False

if __name__ == "__main__":
    test_mqtt_connection()