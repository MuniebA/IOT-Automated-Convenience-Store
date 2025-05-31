import os

class Config:
    # Database Configuration
    DB_HOST = 'localhost'
    DB_USER = 'root'  # Default XAMPP MySQL user
    DB_PASSWORD = ''  # Default XAMPP MySQL password (empty)
    DB_NAME = 'smart_store_db'
    
    # Serial Configuration
    ARDUINO_PORT = 'COM4'  # Your Arduino port
    ARDUINO_BAUDRATE = 9600
    
    # Flask Configuration
    SECRET_KEY = 'your-secret-key-here'
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000

# Raspberry Pi Configuration (for later deployment)
class RaspberryPiConfig(Config):
    ARDUINO_PORT = '/dev/ttyUSB0'  # or /dev/ttyACM0
    DEBUG = False