-- =====================================================
-- SMART CART - MariaDB Compatible Database (Raspberry Pi)
-- =====================================================
-- Purpose: TEMPORARY operational data only - ALL persistent data in cloud
-- Platform: Raspberry Pi 4 + Arduino Uno + MariaDB
-- Hardware: RC522 RFID, HX711 Load Cell, HC-SR04, 7" Touch Display
-- Data Flow: Pi ↔ Cloud API ↔ DynamoDB (Real-time)
-- =====================================================

-- Database configuration
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";
SET NAMES utf8mb4;

-- Create temporary cache database
CREATE DATABASE IF NOT EXISTS smart_cart_temp_cache 
CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE smart_cart_temp_cache;

-- =====================================================
-- SECTION 1: LEGACY COMPATIBILITY TABLES (MINIMAL)
-- =====================================================
-- Keep for backward compatibility with existing cart code

-- Customers table (legacy - points to cloud)
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_visit DATETIME DEFAULT CURRENT_TIMESTAMP,
    cloud_customer_id VARCHAR(50),
    
    INDEX idx_cloud_customer_id (cloud_customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Legacy compatibility - Real data in cloud';

-- Shopping sessions table (legacy - points to cloud)
CREATE TABLE shopping_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME NULL,
    total_amount DECIMAL(10, 2) DEFAULT 0.00,
    fraud_alerts INT DEFAULT 0,
    status ENUM('active', 'completed', 'abandoned') DEFAULT 'active',
    cloud_session_id VARCHAR(50),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_cloud_session_id (cloud_session_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Legacy compatibility - Real data in cloud';

-- Product data table (legacy - points to cloud)
CREATE TABLE product_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cloud_product_id VARCHAR(50),
    
    INDEX idx_cloud_product_id (cloud_product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Legacy compatibility - Real data in cloud';

-- =====================================================
-- SECTION 2: TEMPORARY CACHE TABLES (ESSENTIAL ONLY)
-- =====================================================

-- Active session cache (expires in 4 hours max)
CREATE TABLE temp_active_sessions (
    session_token VARCHAR(64) PRIMARY KEY,
    cart_identifier VARCHAR(20) NOT NULL DEFAULT 'cart-001',
    
    -- Links to cloud
    cloud_session_id VARCHAR(50) NOT NULL,
    cloud_customer_id VARCHAR(50) NOT NULL,
    
    -- Cached customer info for UI (expires quickly)
    customer_name VARCHAR(100),
    customer_type ENUM('REGULAR', 'VIP', 'EMPLOYEE', 'ADMIN') DEFAULT 'REGULAR',
    discount_percentage DECIMAL(5,2) DEFAULT 0.00,
    
    -- Session state
    items_in_cart INT DEFAULT 0,
    running_total DECIMAL(10,2) DEFAULT 0.00,
    fraud_alerts INT DEFAULT 0,
    checkout_completed BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_cart_identifier (cart_identifier),
    INDEX idx_expires_at (expires_at),
    INDEX idx_cloud_session (cloud_session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Temporary session cache - expires automatically';

-- Sensor readings buffer (deleted after cloud sync)
CREATE TABLE temp_sensor_readings (
    reading_id INT AUTO_INCREMENT PRIMARY KEY,
    session_token VARCHAR(64),
    
    -- Sensor data (simplified - no JSON)
    sensor_type ENUM('RFID', 'WEIGHT', 'ULTRASONIC', 'SYSTEM') NOT NULL,
    sensor_value DECIMAL(10,4),
    sensor_unit VARCHAR(20), -- grams, cm, etc.
    
    -- Additional readings for multi-sensor events
    weight_reading DECIMAL(8,2), -- grams
    distance_reading DECIMAL(6,2), -- cm
    rfid_tag VARCHAR(50),
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    cloud_synced BOOLEAN DEFAULT FALSE,
    processing_time_ms INT,
    
    -- Timestamps
    reading_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 10 MINUTE),
    
    FOREIGN KEY (session_token) REFERENCES temp_active_sessions(session_token) ON DELETE CASCADE,
    
    INDEX idx_session_token (session_token),
    INDEX idx_processed (processed),
    INDEX idx_expires_at (expires_at),
    INDEX idx_sensor_type (sensor_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Temporary sensor buffer - deleted after cloud sync';

-- API response cache (5 minutes max)
CREATE TABLE temp_api_cache (
    cache_key VARCHAR(100) PRIMARY KEY, -- RFID UID or product ID
    cache_type ENUM('CUSTOMER', 'PRODUCT') NOT NULL,
    
    -- Cached response data (simplified)
    response_status VARCHAR(20), -- success, error, not_found
    customer_name VARCHAR(100),
    customer_type VARCHAR(20),
    product_name VARCHAR(100),
    product_price DECIMAL(10,2),
    product_weight DECIMAL(8,2),
    discount_percentage DECIMAL(5,2),
    
    -- Cache metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 5 MINUTE),
    
    INDEX idx_cache_type (cache_type),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Short-lived API response cache';

-- Cart operations queue (for cloud processing)
CREATE TABLE temp_cart_operations (
    operation_id INT AUTO_INCREMENT PRIMARY KEY,
    session_token VARCHAR(64) NOT NULL,
    operation_type ENUM('ADD_ITEM', 'REMOVE_ITEM', 'VALIDATE_WEIGHT', 
                       'FRAUD_DETECTED', 'CHECKOUT') NOT NULL,
    
    -- Operation data (simplified - no JSON)
    product_rfid VARCHAR(50),
    product_name VARCHAR(100),
    expected_weight DECIMAL(8,2),
    actual_weight DECIMAL(8,2),
    fraud_type VARCHAR(50),
    
    -- Processing status
    status ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 1 HOUR),
    processed_at TIMESTAMP NULL,
    
    FOREIGN KEY (session_token) REFERENCES temp_active_sessions(session_token) ON DELETE CASCADE,
    
    INDEX idx_session_token (session_token),
    INDEX idx_status (status),
    INDEX idx_operation_type (operation_type),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Queued operations for cloud processing';

-- Cart hardware status (current state only)
CREATE TABLE temp_cart_status (
    cart_identifier VARCHAR(20) PRIMARY KEY DEFAULT 'cart-001',
    
    -- Hardware status (boolean flags)
    arduino_connected BOOLEAN DEFAULT FALSE,
    rfid_reader_status BOOLEAN DEFAULT FALSE,
    weight_sensor_status BOOLEAN DEFAULT FALSE,
    ultrasonic_status BOOLEAN DEFAULT FALSE,
    display_status BOOLEAN DEFAULT FALSE,
    wifi_connected BOOLEAN DEFAULT FALSE,
    cloud_api_status BOOLEAN DEFAULT FALSE,
    
    -- System metrics (simplified)
    cpu_usage DECIMAL(5,2) DEFAULT 0.00,
    memory_usage DECIMAL(5,2) DEFAULT 0.00,
    temperature DECIMAL(4,1) DEFAULT 0.0,
    
    -- Operational counters
    active_session_token VARCHAR(64),
    total_operations_today INT DEFAULT 0,
    error_count_today INT DEFAULT 0,
    
    -- Status metadata
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_cloud_ping TIMESTAMP,
    status_expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 5 MINUTE),
    
    FOREIGN KEY (active_session_token) REFERENCES temp_active_sessions(session_token) ON DELETE SET NULL,
    
    INDEX idx_status_expires (status_expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Current cart hardware status';

-- =====================================================
-- SECTION 3: SYSTEM CONFIGURATION
-- =====================================================

-- System configuration (operational parameters only)
CREATE TABLE temp_system_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'System configuration - operational settings only';

-- Insert default configuration
INSERT INTO temp_system_config (config_key, config_value, description) VALUES
('cloud_api_endpoint', 'https://api.iotstore.com/v1', 'Cloud API base URL'),
('api_timeout_ms', '5000', 'API call timeout in milliseconds'),
('cache_duration_minutes', '5', 'How long to cache API responses'),
('max_session_duration_hours', '4', 'Maximum session length'),
('sensor_reading_interval_ms', '500', 'How often to read sensors'),
('fraud_weight_tolerance_percent', '15', 'Weight variance tolerance for fraud detection'),
('auto_cleanup_interval_minutes', '5', 'How often to cleanup expired data');

-- =====================================================
-- SECTION 4: AUTOMATIC CLEANUP SYSTEM
-- =====================================================

-- Auto-cleanup expired data every 5 minutes
DELIMITER //
CREATE EVENT IF NOT EXISTS cleanup_expired_data
ON SCHEDULE EVERY 5 MINUTE
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    -- Delete expired session tokens
    DELETE FROM temp_active_sessions WHERE expires_at < NOW();
    
    -- Delete old sensor readings
    DELETE FROM temp_sensor_readings WHERE expires_at < NOW();
    
    -- Delete expired API cache
    DELETE FROM temp_api_cache WHERE expires_at < NOW();
    
    -- Delete old cart operations
    DELETE FROM temp_cart_operations WHERE expires_at < NOW();
    
    -- Reset cart status if expired
    UPDATE temp_cart_status 
    SET active_session_token = NULL 
    WHERE status_expires_at < NOW();
    
    -- Reset daily counters at midnight
    IF TIME(NOW()) BETWEEN '00:00:00' AND '00:05:00' THEN
        UPDATE temp_cart_status SET 
            total_operations_today = 0,
            error_count_today = 0;
    END IF;
    
END//
DELIMITER ;

-- =====================================================
-- SECTION 5: SIMPLE STORED PROCEDURES
-- =====================================================

DELIMITER //

-- Start new session (simplified)
CREATE PROCEDURE StartCartSession(
    IN p_cart_id VARCHAR(20),
    IN p_customer_id VARCHAR(50),
    IN p_customer_name VARCHAR(100),
    OUT p_session_token VARCHAR(64)
)
BEGIN
    -- Generate session token
    SET p_session_token = CONCAT('cart_', p_cart_id, '_', UNIX_TIMESTAMP(), '_', CONNECTION_ID());
    
    -- Create temporary session
    INSERT INTO temp_active_sessions (
        session_token,
        cart_identifier,
        cloud_session_id,
        cloud_customer_id,
        customer_name,
        expires_at
    ) VALUES (
        p_session_token,
        p_cart_id,
        CONCAT('cloud_sess_', UNIX_TIMESTAMP()),
        p_customer_id,
        p_customer_name,
        DATE_ADD(NOW(), INTERVAL 4 HOUR)
    );
    
    -- Update cart status
    UPDATE temp_cart_status 
    SET active_session_token = p_session_token,
        last_heartbeat = NOW()
    WHERE cart_identifier = p_cart_id;
    
END//

-- Add sensor reading (simplified)
CREATE PROCEDURE AddSensorReading(
    IN p_session_token VARCHAR(64),
    IN p_sensor_type VARCHAR(20),
    IN p_sensor_value DECIMAL(10,4),
    IN p_rfid_tag VARCHAR(50),
    IN p_weight DECIMAL(8,2)
)
BEGIN
    INSERT INTO temp_sensor_readings (
        session_token,
        sensor_type,
        sensor_value,
        rfid_tag,
        weight_reading
    ) VALUES (
        p_session_token,
        p_sensor_type,
        p_sensor_value,
        p_rfid_tag,
        p_weight
    );
    
    -- Update session activity
    UPDATE temp_active_sessions 
    SET last_activity = NOW()
    WHERE session_token = p_session_token;
    
END//

DELIMITER ;

-- =====================================================
-- INITIALIZATION
-- =====================================================

-- Initialize cart status
INSERT INTO temp_cart_status (cart_identifier) VALUES ('cart-001')
ON DUPLICATE KEY UPDATE last_heartbeat = NOW();

-- =====================================================
-- OPTIMIZED INDEXES
-- =====================================================

-- Performance indexes for frequent operations
CREATE INDEX idx_session_expires ON temp_active_sessions(expires_at, session_token);
CREATE INDEX idx_operations_pending ON temp_cart_operations(status, created_at);

-- =====================================================
-- SCHEMA COMPLETE FOR SMART CART (MariaDB Compatible)
-- =====================================================
-- Removed Features:
-- ❌ Complex JSON columns (replaced with simple columns)
-- ❌ Redundant debugging tables (arduino_comm, api_calls)
-- ❌ Over-engineered triggers
-- ❌ Fractional seconds in DATETIME
-- 
-- Key Features:
-- ✅ MariaDB compatible (no JSON dependencies)
-- ✅ Simple, clean table structure
-- ✅ Essential temporary caching only
-- ✅ Automatic cleanup every 5 minutes
-- ✅ Legacy table compatibility
-- ✅ Real-time cloud integration ready
-- ✅ Optimized for performance
-- =====================================================
