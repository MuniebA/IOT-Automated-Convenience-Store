import os

class Config:
    # Database Configuration for MariaDB
    DB_HOST = 'localhost'
    DB_USER = 'door_user'
    DB_PASSWORD = 'door_password_123'  # Use the password you set
    DB_NAME = 'door_access_temp_cache'
    
    # Serial Configuration
    ARDUINO_PORT = '/dev/ttyUSB0'  # or /dev/ttyUSB0 - check with ls /dev/tty*
    ARDUINO_BAUDRATE = 9600
    
    # Flask Configuration
    SECRET_KEY = 'your-secret-key-here-change-me'
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    
    # MQTT Configuration (will be added later)
    IOT_ENDPOINT = ''  # Will be filled from AWS Console
    CLIENT_ID = 'iot-convenience-store-door-001-production'
    
    # Certificate paths
    CA_CERT = 'certificates/AmazonRootCA1.pem'
    CERT_FILE = 'certificates/door-certificate.pem.crt'
    KEY_FILE = 'certificates/door-private.pem.key'

# Production configuration for when not debugging
class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'prod-secret-key'