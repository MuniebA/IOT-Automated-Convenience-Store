-- =====================================================
-- DOOR ACCESS - MariaDB Compatible Database (Raspberry Pi)
-- =====================================================
-- Purpose: TEMPORARY operational data only - ALL persistent data in cloud
-- Platform: Raspberry Pi 4 + Arduino Uno + MariaDB
-- Hardware: RC522 RFID, SG90 Servo, IR Sensors, 16x2 LCD, LEDs, Buzzer
-- Data Flow: Pi ↔ Cloud API ↔ DynamoDB (Real-time)
-- =====================================================

-- Database configuration
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";
SET NAMES utf8mb4;

-- Create temporary cache database
CREATE DATABASE IF NOT EXISTS door_access_temp_cache 
CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE door_access_temp_cache;

-- =====================================================
-- SECTION 1: LEGACY COMPATIBILITY TABLE
-- =====================================================
-- Keep existing door_lock_table for backward compatibility

-- Door lock table (legacy - enhanced with cloud links)
CREATE TABLE door_lock_table (
    rfid_id VARCHAR(32) NOT NULL,
    rfid_name VARCHAR(100) NOT NULL,
    checkout_status TINYINT(1) NOT NULL DEFAULT 1,
    cloud_customer_id VARCHAR(50),
    last_cloud_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (rfid_id),
    INDEX idx_cloud_customer_id (cloud_customer_id),
    INDEX idx_checkout_status (checkout_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Legacy compatibility - Real access control data in cloud';

-- =====================================================
-- SECTION 2: TEMPORARY CACHE TABLES (ESSENTIAL ONLY)
-- =====================================================

-- RFID verification cache (2 minutes max)
CREATE TABLE temp_rfid_cache (
    rfid_card_uid VARCHAR(32) PRIMARY KEY,
    
    -- Cached cloud response (simplified - no JSON)
    customer_name VARCHAR(100),
    customer_type ENUM('REGULAR', 'VIP', 'EMPLOYEE', 'ADMIN') DEFAULT 'REGULAR',
    membership_status ENUM('ACTIVE', 'SUSPENDED', 'EXPIRED') DEFAULT 'ACTIVE',
    checkout_required BOOLEAN DEFAULT TRUE,
    access_granted BOOLEAN DEFAULT FALSE,
    
    -- Permissions (simplified)
    can_enter BOOLEAN DEFAULT TRUE,
    can_exit BOOLEAN DEFAULT TRUE,
    vip_access BOOLEAN DEFAULT FALSE,
    
    -- Cache metadata
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 2 MINUTE),
    cloud_verified BOOLEAN DEFAULT TRUE,
    
    INDEX idx_expires_at (expires_at),
    INDEX idx_membership_status (membership_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Ultra-short RFID cache for performance';

-- Access events (synced to cloud quickly - SINGLE DOOR SYSTEM)
CREATE TABLE temp_access_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    door_identifier VARCHAR(20) NOT NULL DEFAULT 'door-001',
    rfid_card_uid VARCHAR(32) NOT NULL,
    
    -- Event details (SINGLE DOOR - handles both entry and exit)
    event_type ENUM('ENTRY_ATTEMPT', 'ENTRY_SUCCESS', 'ENTRY_DENIED',
                   'EXIT_ATTEMPT', 'EXIT_SUCCESS', 'EXIT_DENIED') NOT NULL,
    access_granted BOOLEAN DEFAULT FALSE,
    deny_reason VARCHAR(100),
    customer_name VARCHAR(100),
    
    -- Hardware state during event
    servo_position_before INT DEFAULT 0,
    servo_position_after INT DEFAULT 0,
    door_open_duration INT DEFAULT 0, -- seconds
    
    -- Single safety sensor
    ir_sensor_triggered BOOLEAN DEFAULT FALSE,
    safety_override BOOLEAN DEFAULT FALSE,
    
    -- System context
    offline_mode BOOLEAN DEFAULT FALSE,
    emergency_override BOOLEAN DEFAULT FALSE,
    cloud_session_id VARCHAR(50),
    
    -- Sync management
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 30 MINUTE),
    cloud_synced BOOLEAN DEFAULT FALSE,
    sync_attempts INT DEFAULT 0,
    
    INDEX idx_door_identifier (door_identifier),
    INDEX idx_cloud_synced (cloud_synced),
    INDEX idx_expires_at (expires_at),
    INDEX idx_event_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Temporary access events - single door system';

-- Door hardware status (current state only - SINGLE DOOR SYSTEM)
CREATE TABLE temp_door_status (
    door_identifier VARCHAR(20) PRIMARY KEY DEFAULT 'door-001',
    
    -- Physical hardware state (SINGLE DOOR)
    servo_current_position INT DEFAULT 0, -- 0=locked, 90=unlocked
    servo_target_position INT DEFAULT 0,
    is_locked BOOLEAN DEFAULT TRUE,
    auto_lock_timer INT DEFAULT 0, -- seconds until auto-lock
    
    -- Safety system (SINGLE IR SENSOR)
    ir_sensor_active BOOLEAN DEFAULT FALSE, -- Single beam sensor for safety
    safety_beam_broken BOOLEAN DEFAULT FALSE,
    safety_lock_engaged BOOLEAN DEFAULT FALSE,
    door_override_active BOOLEAN DEFAULT FALSE,
    
    -- Hardware health (SINGLE DOOR COMPONENTS)
    arduino_connected BOOLEAN DEFAULT FALSE,
    servo_responsive BOOLEAN DEFAULT TRUE,
    ir_sensor_functional BOOLEAN DEFAULT TRUE,
    lcd_functional BOOLEAN DEFAULT TRUE,
    buzzer_functional BOOLEAN DEFAULT TRUE,
    led_red_functional BOOLEAN DEFAULT TRUE,
    led_green_functional BOOLEAN DEFAULT TRUE,
    rfid_reader_functional BOOLEAN DEFAULT TRUE,
    
    -- Network status
    wifi_connected BOOLEAN DEFAULT FALSE,
    cloud_api_status BOOLEAN DEFAULT FALSE,
    last_cloud_ping TIMESTAMP,
    
    -- Daily counters (reset at midnight)
    access_attempts_today INT DEFAULT 0,
    successful_entries_today INT DEFAULT 0,
    successful_exits_today INT DEFAULT 0,
    denied_attempts_today INT DEFAULT 0,
    
    -- Status metadata
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    error_count INT DEFAULT 0,
    last_error VARCHAR(255),
    
    INDEX idx_is_locked (is_locked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Current door operational status - single door system';

-- Safety events (temporary monitoring - SINGLE IR SENSOR)
CREATE TABLE temp_safety_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    door_identifier VARCHAR(20) NOT NULL DEFAULT 'door-001',
    
    event_type ENUM('BEAM_BROKEN', 'BEAM_RESTORED', 'SENSOR_MALFUNCTION',
                   'SAFETY_OVERRIDE', 'EMERGENCY_STOP') NOT NULL,
    
    -- Single sensor readings
    ir_sensor_reading BOOLEAN DEFAULT FALSE,
    beam_break_duration_ms INT DEFAULT 0,
    
    -- Response actions
    servo_action VARCHAR(100),
    safety_lock_triggered BOOLEAN DEFAULT FALSE,
    alert_sent BOOLEAN DEFAULT FALSE,
    
    -- Event context
    access_event_id INT, -- Link to access attempt if applicable
    resolved BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 1 HOUR),
    resolved_at TIMESTAMP NULL,
    
    FOREIGN KEY (access_event_id) REFERENCES temp_access_events(event_id) ON DELETE SET NULL,
    
    INDEX idx_door_identifier (door_identifier),
    INDEX idx_event_type (event_type),
    INDEX idx_resolved (resolved),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Temporary safety events - single IR sensor system';

-- Emergency events (critical - immediate cloud sync)
CREATE TABLE temp_emergency_events (
    emergency_id INT AUTO_INCREMENT PRIMARY KEY,
    door_identifier VARCHAR(20) NOT NULL DEFAULT 'door-001',
    
    emergency_type ENUM('FIRE', 'MEDICAL', 'SECURITY', 'POWER_FAILURE',
                       'SYSTEM_MALFUNCTION', 'MANUAL_OVERRIDE') NOT NULL,
    
    -- Emergency details
    triggered_by VARCHAR(100),
    authorization_code VARCHAR(50),
    override_reason TEXT,
    
    -- Actions taken
    doors_unlocked BOOLEAN DEFAULT TRUE,
    authorities_notified BOOLEAN DEFAULT FALSE,
    
    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    resolved_by VARCHAR(100),
    
    -- Sync management (critical priority)
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 10 MINUTE),
    cloud_synced BOOLEAN DEFAULT FALSE,
    sync_priority ENUM('HIGH', 'CRITICAL') DEFAULT 'CRITICAL',
    
    INDEX idx_emergency_type (emergency_type),
    INDEX idx_cloud_synced (cloud_synced),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Emergency events - immediate cloud sync required';

-- =====================================================
-- SECTION 3: SYSTEM CONFIGURATION
-- =====================================================

-- System configuration (operational parameters only)
CREATE TABLE temp_door_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Door system configuration';

-- Insert default configuration
INSERT INTO temp_door_config (config_key, config_value, description) VALUES
('cloud_api_endpoint', 'https://api.iotstore.com/v1/door', 'Cloud API endpoint for door access'),
('api_timeout_ms', '3000', 'API call timeout for access control'),
('rfid_cache_duration_minutes', '2', 'How long to cache RFID verification'),
('auto_lock_delay_seconds', '10', 'Delay before auto-lock after access'),
('ir_sensor_debounce_ms', '500', 'Single IR sensor debounce time'),
('emergency_unlock_duration_minutes', '15', 'How long emergency unlock lasts'),
('max_denied_attempts_per_hour', '10', 'Security threshold for denied attempts'),
('servo_unlock_angle', '90', 'Servo angle for unlocked position'),
('servo_lock_angle', '0', 'Servo angle for locked position'),
('led_success_duration_ms', '2000', 'Green LED duration for successful access'),
('led_error_duration_ms', '3000', 'Red LED duration for access denied'),
('buzzer_success_beeps', '2', 'Number of beeps for successful access'),
('buzzer_error_beeps', '3', 'Number of beeps for access denied'),
('lcd_message_duration_seconds', '5', 'How long to show messages on LCD');

-- =====================================================
-- SECTION 4: AUTOMATIC CLEANUP SYSTEM
-- =====================================================

-- Auto-cleanup expired data every 2 minutes
DELIMITER //
CREATE EVENT IF NOT EXISTS cleanup_expired_door_data
ON SCHEDULE EVERY 2 MINUTE
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    -- Delete expired RFID cache
    DELETE FROM temp_rfid_cache WHERE expires_at < NOW();
    
    -- Delete synced access events
    DELETE FROM temp_access_events 
    WHERE expires_at < NOW() AND cloud_synced = TRUE;
    
    -- Delete resolved safety events
    DELETE FROM temp_safety_events 
    WHERE expires_at < NOW() AND resolved = TRUE;
    
    -- Delete synced emergency events (keep critical ones longer)
    DELETE FROM temp_emergency_events 
    WHERE expires_at < NOW() AND cloud_synced = TRUE;
    
    -- Reset daily counters at midnight (SINGLE DOOR SYSTEM)
    IF TIME(NOW()) BETWEEN '00:00:00' AND '00:02:00' THEN
        UPDATE temp_door_status SET 
            access_attempts_today = 0,
            successful_entries_today = 0,
            successful_exits_today = 0,
            denied_attempts_today = 0;
    END IF;
    
END//
DELIMITER ;

-- =====================================================
-- SECTION 5: STORED PROCEDURES (SIMPLIFIED)
-- =====================================================

DELIMITER //

-- Process RFID access request
CREATE PROCEDURE ProcessAccessRequest(
    IN p_door_id VARCHAR(20),
    IN p_rfid_uid VARCHAR(32),
    IN p_request_type ENUM('ENTRY', 'EXIT'),
    OUT p_access_granted BOOLEAN,
    OUT p_deny_reason VARCHAR(100),
    OUT p_customer_name VARCHAR(100)
)
BEGIN
    DECLARE v_membership_status VARCHAR(20);
    DECLARE v_checkout_required BOOLEAN DEFAULT TRUE;
    
    -- Initialize outputs
    SET p_access_granted = FALSE;
    SET p_deny_reason = 'Unknown error';
    SET p_customer_name = 'Unknown';
    
    -- Check cache first
    SELECT customer_name, membership_status, checkout_required
    INTO p_customer_name, v_membership_status, v_checkout_required
    FROM temp_rfid_cache 
    WHERE rfid_card_uid = p_rfid_uid 
    AND expires_at > NOW()
    LIMIT 1;
    
    -- If not in cache, check legacy table (simulate cloud lookup)
    IF p_customer_name = 'Unknown' THEN
        SELECT rfid_name, checkout_status
        INTO p_customer_name, v_checkout_required
        FROM door_lock_table 
        WHERE rfid_id = p_rfid_uid;
        
        -- Cache the result
        IF p_customer_name IS NOT NULL THEN
            INSERT INTO temp_rfid_cache (
                rfid_card_uid,
                customer_name,
                membership_status,
                checkout_required,
                expires_at
            ) VALUES (
                p_rfid_uid,
                p_customer_name,
                'ACTIVE',
                v_checkout_required = 1,
                NOW() + INTERVAL 2 MINUTE
            ) ON DUPLICATE KEY UPDATE
                customer_name = VALUES(customer_name),
                checkout_required = VALUES(checkout_required),
                expires_at = VALUES(expires_at);
        END IF;
    END IF;
    
    -- Apply access control logic
    IF p_customer_name IS NULL OR p_customer_name = 'Unknown' THEN
        SET p_deny_reason = 'Card not recognized';
    ELSEIF v_membership_status = 'SUSPENDED' THEN
        SET p_deny_reason = 'Membership suspended';
    ELSEIF p_request_type = 'ENTRY' THEN
        SET p_access_granted = TRUE;
        SET p_deny_reason = NULL;
    ELSEIF p_request_type = 'EXIT' AND v_checkout_required = FALSE THEN
        SET p_access_granted = TRUE;
        SET p_deny_reason = NULL;
    ELSEIF p_request_type = 'EXIT' THEN
        SET p_deny_reason = 'Checkout required before exit';
    END IF;
    
    -- Log the access attempt
    INSERT INTO temp_access_events (
        door_identifier,
        rfid_card_uid,
        event_type,
        access_granted,
        deny_reason,
        customer_name,
        offline_mode
    ) VALUES (
        p_door_id,
        p_rfid_uid,
        CASE 
            WHEN p_request_type = 'ENTRY' AND p_access_granted THEN 'ENTRY_SUCCESS'
            WHEN p_request_type = 'ENTRY' THEN 'ENTRY_DENIED'
            WHEN p_request_type = 'EXIT' AND p_access_granted THEN 'EXIT_SUCCESS'
            ELSE 'EXIT_DENIED'
        END,
        p_access_granted,
        p_deny_reason,
        p_customer_name,
        FALSE
    );
    
END//

-- Control door servo
CREATE PROCEDURE ControlDoorServo(
    IN p_door_id VARCHAR(20),
    IN p_target_angle INT,
    IN p_reason VARCHAR(100)
)
BEGIN
    DECLARE v_current_angle INT DEFAULT 0;
    
    -- Get current position
    SELECT servo_current_position INTO v_current_angle
    FROM temp_door_status 
    WHERE door_identifier = p_door_id;
    
    -- Update door status
    UPDATE temp_door_status 
    SET 
        servo_target_position = p_target_angle,
        servo_current_position = p_target_angle,
        is_locked = CASE WHEN p_target_angle = 0 THEN TRUE ELSE FALSE END,
        last_heartbeat = NOW()
    WHERE door_identifier = p_door_id;
    
END//

-- Emergency unlock
CREATE PROCEDURE EmergencyUnlock(
    IN p_door_id VARCHAR(20),
    IN p_emergency_type VARCHAR(20),
    IN p_reason TEXT
)
BEGIN
    -- Unlock door immediately
    CALL ControlDoorServo(p_door_id, 90, 'EMERGENCY_UNLOCK');
    
    -- Log emergency event
    INSERT INTO temp_emergency_events (
        door_identifier,
        emergency_type,
        triggered_by,
        override_reason,
        doors_unlocked,
        sync_priority
    ) VALUES (
        p_door_id,
        p_emergency_type,
        'MANUAL_OVERRIDE',
        p_reason,
        TRUE,
        'CRITICAL'
    );
    
    -- Update door status
    UPDATE temp_door_status 
    SET door_override_active = TRUE
    WHERE door_identifier = p_door_id;
    
END//

DELIMITER ;

-- =====================================================
-- SECTION 6: INITIALIZATION
-- =====================================================

-- Initialize door system status
INSERT INTO temp_door_status (door_identifier) VALUES ('door-001')
ON DUPLICATE KEY UPDATE last_heartbeat = NOW();

-- Sample RFID cards for testing (legacy compatibility)
INSERT INTO door_lock_table (rfid_id, rfid_name, checkout_status) VALUES
('ABC123456789', 'John Doe (VIP)', 1),
('DEF987654321', 'Jane Smith (Regular)', 0),
('GHI555666777', 'Admin User', 1),
('JKL111222333', 'Employee Test', 1)
ON DUPLICATE KEY UPDATE last_cloud_sync = NOW();

-- =====================================================
-- OPTIMIZED INDEXES
-- =====================================================

-- Performance indexes for real-time operations
CREATE INDEX idx_rfid_cache_lookup ON temp_rfid_cache(rfid_card_uid, expires_at);
CREATE INDEX idx_access_sync_priority ON temp_access_events(cloud_synced, expires_at);

-- =====================================================
-- SCHEMA COMPLETE FOR DOOR ACCESS (MariaDB Compatible)
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
-- ✅ Essential access control only
-- ✅ Ultra-short RFID cache (2 minutes)
-- ✅ Automatic cleanup every 2 minutes
-- ✅ Emergency procedures with priority sync
-- ✅ Safety monitoring (IR sensors)
-- ✅ Legacy table compatibility maintained
-- ✅ Real-time cloud integration ready
-- =====================================================