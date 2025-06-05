import serial
import time
import mysql.connector
import json
from datetime import datetime
import logging

CONTROL_COMMANDS = {'BUZZER', 'LED', 'OPEN_LID', 'CLOSE_LID'}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("serial_handler.log"),
        logging.StreamHandler()
    ]
)

# Database configuration
DB_CONFIG = {
    'user': 'shifaz',
    'password': 'Shifaz1122@',
    'host': 'localhost',
    'database': 'automated_shopping_cart'
}

# Serial configuration
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

def connect_to_database():
    """Connect to the MySQL database and return the connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logging.info("Successfully connected to the database")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        exit(1)

def connect_to_arduino():
    """Connect to the Arduino via serial port and return the connection."""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        logging.info(f"Connected to Arduino on {SERIAL_PORT}")
        time.sleep(2)  # Allow time for Arduino to reset
        return ser
    except serial.SerialException as err:
        logging.error(f"Serial connection error: {err}")
        exit(1)

def process_card_scan(cursor, tag_id, serial_conn):
    """Process a card scan event and update the database."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Check if we're in control mode
    cursor.execute(
        "SELECT id FROM commands WHERE command_type = '_control_read_flag' AND status = 'pending' LIMIT 1"
    )
    control_flag = cursor.fetchone()
    
    if control_flag:
        # We're in control mode - handle differently
        logging.info(f"Processing card scan in CONTROL MODE for tag ID: {tag_id}")
        
        # Mark the control flag as complete
        cursor.execute(
            "UPDATE commands SET status = 'complete' WHERE id = %s",
            (control_flag[0],)
        )
        
        # Send READ command to Arduino directly
        logging.info("Sending READ command to Arduino (control mode)")
        serial_conn.write(b"READ\n")
        
        # Wait for Arduino to respond with DATA:
        max_attempts = 10
        data_received = False
        
        for _ in range(max_attempts):
            time.sleep(0.5)
            if serial_conn.in_waiting > 0:
                response = serial_conn.readline().decode('utf-8').strip()
                logging.info(f"Received from Arduino (control mode): {response}")
                
                if response.startswith("DATA:"):
                    data = response[5:].strip()
                    
                    # Store result in control_results table without normal processing
                    try:
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS control_results (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                tag_id VARCHAR(100),
                                data TEXT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                        cursor.execute(
                            "INSERT INTO control_results (tag_id, data) VALUES (%s, %s)",
                            (tag_id, data)
                        )
                        logging.info(f"Stored control read result: {data}")
                    except Exception as e:
                        logging.error(f"Error storing control result: {e}")
                    
                    data_received = True
                    break
                
                # If Arduino says "Place your card..." keep waiting
                if response == "Place your card...":
                    continue
                
                # If we get an error, log it
                if response.startswith("ERR:"):
                    logging.error(f"Arduino error in control mode: {response}")
                    break
        
        if not data_received:
            logging.warning(f"Failed to get product data for tag {tag_id} in control mode")
        
        # Exit early - don't proceed with normal cart flow
        return
    
    # REGULAR MODE - Normal card scan processing begins here
    logging.info(f"Processing card scan with tag ID: {tag_id} (regular mode)")
    
    # First, store the scanned tag in the database
    cursor.execute(
        "INSERT INTO scanned_items (tag_id, timestamp, product_id, is_validated) VALUES (%s, %s, %s, %s)",
        (tag_id, timestamp, None, False)
    )
    
    # Get the ID of the inserted record
    scanned_item_id = cursor.lastrowid
    
    # Immediately send READ command to Arduino
    logging.info("Sending READ command to Arduino")
    serial_conn.write(b"READ\n")
    
    # Wait for Arduino to respond with DATA:
    max_attempts = 10
    data_received = False
    
    for _ in range(max_attempts):
        time.sleep(0.5)
        if serial_conn.in_waiting > 0:
            response = serial_conn.readline().decode('utf-8').strip()
            logging.info(f"Received from Arduino: {response}")
            
            if response.startswith("DATA:"):
                data = response[5:].strip()
                process_tag_data(cursor, data, scanned_item_id, tag_id)
                
                # Also store this data in control_results for the control page
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS control_results (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            tag_id VARCHAR(100),
                            data TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cursor.execute(
                        "INSERT INTO control_results (tag_id, data) VALUES (%s, %s)",
                        (tag_id, data)
                    )
                except Exception as e:
                    logging.error(f"Error storing control result: {e}")
                
                data_received = True
                break
            
            # If Arduino says "Place your card..." keep waiting
            if response == "Place your card...":
                continue
            
            # If we get an error, log it
            if response.startswith("ERR:"):
                logging.error(f"Arduino error: {response}")
                break
    
    if not data_received:
        logging.warning(f"Failed to get product data for tag {tag_id}")

def process_tag_data(cursor, data, scanned_item_id, tag_id):
    """Process data read from RFID tag and update the database."""
    logging.info(f"Processing tag data: {data}")
    
    if data == "NoData#0":
        logging.info("No data stored on RFID tag")
        return
    
    try:
        # Parse the data - could be in format "product_name#price" or "product_name,price,is_grocery"
        if "#" in data:
            # Format: product_name#price
            parts = data.split('#')
            product_name = parts[0]
            price = float(parts[1]) if len(parts) > 1 else 0.0
            is_grocery = False  # Default to false if not specified
        else:
            # Format: product_name,price,is_grocery
            parts = data.split(',')
            product_name = parts[0]
            price = float(parts[1]) if len(parts) > 1 else 0.0
            is_grocery = bool(int(parts[2])) if len(parts) > 2 else False
        
        logging.info(f"Parsed product data: {product_name}, ${price}, Grocery: {is_grocery}")
        
        # Check if product exists in database
        cursor.execute(
            "SELECT id FROM product_data WHERE product_name = %s AND price = %s",
            (product_name, price)
        )
        product_row = cursor.fetchone()
        
        if product_row:
            product_id = product_row[0]
            logging.info(f"Found existing product: {product_name}, ID: {product_id}")
        else:
            # Insert the product into product_data
            cursor.execute(
                "INSERT INTO product_data (product_name, price, is_grocery) VALUES (%s, %s, %s)",
                (product_name, price, is_grocery)
            )
            product_id = cursor.lastrowid
            logging.info(f"Added new product: {product_name}, ID: {product_id}, Price: ${price}")
        
        # Update the scanned item with the product_id
        cursor.execute(
            "UPDATE scanned_items SET product_id = %s WHERE id = %s",
            (product_id, scanned_item_id)
        )
        logging.info(f"Updated scanned item {scanned_item_id} with product ID {product_id}")
        
        # Add 'open_lid' command (simulating lid opening as in the original design)
        cursor.execute(
            "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
            ('open_lid', json.dumps({'product_id': product_id}), 'pending', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
    except Exception as e:
        logging.error(f"Error processing RFID data: {e}")
        logging.exception("Exception details:")
def process_fraud_alert(cursor, reason):
    """Log fraud detection events to the database."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Map Arduino fraud messages to database ENUM values
    fraud_type_mapping = {
        'unscanned product placed': 'unscanned_item',
        'unscanned item': 'unscanned_item',
        'no placement': 'no_placement',
        'no placement detected': 'no_placement',
        'multiple items': 'multiple_items',
        'multiple items detected': 'multiple_items',
        'weight mismatch': 'weight_mismatch',
        'weight discrepancy': 'weight_mismatch'
    }
    
    # Convert reason to lowercase for matching
    reason_lower = reason.lower().strip()
    
    # Find the appropriate event_type
    event_type = fraud_type_mapping.get(reason_lower, 'unscanned_item')  # Default fallback
    
    try:
        # Insert into fraud_logs with the mapped event_type
        cursor.execute(
            "INSERT INTO fraud_logs (event_type, details, timestamp) VALUES (%s, %s, %s)",
            (event_type, reason, timestamp)  # reason goes in details, event_type is the ENUM
        )
        
        logging.warning(f"Fraud detected: {reason} -> mapped to event_type: {event_type}")
        
    except Exception as e:
        logging.error(f"Error logging fraud event: {e}")
        logging.error(f"Attempted to insert event_type: '{event_type}', original reason: '{reason}'")

def process_weight_data(cursor, weight):
    """Process weight data from load cell and update the database."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Always record the weight in the weight_readings table (create if it doesn't exist)
    try:
        # Check if weight_readings table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'weight_readings'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            # Create the table if it doesn't exist
            cursor.execute("""
                CREATE TABLE weight_readings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    weight DECIMAL(10, 2) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            logging.info("Created weight_readings table")
        
        # Store the weight reading
        cursor.execute(
            "INSERT INTO weight_readings (weight, timestamp, processed) VALUES (%s, %s, %s)",
            (weight, timestamp, False)
        )
        logging.info(f"Recorded weight reading: {weight}g")
    except Exception as e:
        logging.error(f"Error recording weight reading: {e}")
    
    # Try to find a grocery item that needs weighing (for the original RFID flow)
    try:
        cursor.execute("""
            SELECT s.id 
            FROM scanned_items s
            JOIN product_data p ON s.product_id = p.id
            WHERE s.weight IS NULL AND p.is_grocery = TRUE AND s.is_validated = FALSE
            ORDER BY s.timestamp DESC 
            LIMIT 1
        """)
        item = cursor.fetchone()
        
        if item:
            item_id = item[0]
            cursor.execute(
                "UPDATE scanned_items SET weight = %s WHERE id = %s",
                (weight, item_id)
            )
            logging.info(f"Updated weight for item ID {item_id}: {weight}g")
        else:
            logging.info(f"Weight reading ({weight}g) stored in weight_readings table")
    except Exception as e:
        logging.error(f"Error processing weight for scanned items: {e}")

def check_commands(cursor, ser):
    """Check for pending commands in the database and send them to Arduino."""
    cursor.execute(
        "SELECT id, command_type, parameters FROM commands WHERE status = 'pending' ORDER BY timestamp ASC LIMIT 5"
    )
    commands = cursor.fetchall()
    
    for cmd_id, cmd_type, parameters in commands:
        # Enhanced logging for debugging
        logging.info(f"Processing command ID: {cmd_id}, Type: '{cmd_type}', Parameters: {parameters}")
        
        # Skip empty commands with enhanced debugging
        if not cmd_type or not isinstance(cmd_type, str) or cmd_type.strip() == '':
            cursor.execute(
                "DELETE FROM commands WHERE id = %s",
                (cmd_id,)
            )
            logging.warning(f"Deleted empty command with ID {cmd_id}, Type: {type(cmd_type)}")
            continue
            
        try:
            # Parse parameters safely
            try:
                params = json.loads(parameters) if parameters and parameters.strip() else {}
            except json.JSONDecodeError:
                params = {}
                logging.warning(f"Could not parse parameters for command {cmd_type}, using empty dict")
                
            is_control = params.get('control_mode', False)
            
            logging.info(f"Processing command: {cmd_type}, control mode: {is_control}")
            
            # Handle special control commands with better logging
            if cmd_type in ['BUZZER', 'LED', 'OPEN_LID', 'CLOSE_LID']:
                # These are direct Arduino commands
                command_string = f"{cmd_type}\n"
                ser.write(command_string.encode())
                logging.info(f"★★★ Sent direct command to Arduino: {cmd_type} ★★★")
                
                # Wait for a response
                time.sleep(1)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8').strip()
                    logging.info(f"Arduino response to {cmd_type}: {response}")
                else:
                    logging.warning(f"No response from Arduino for command: {cmd_type}")
            
            elif cmd_type == '_control_read_flag':
                # This is just a flag, no need to send to Arduino
                logging.info("Processed control read flag")
                
            elif cmd_type == 'write_tag':
                # Get the data from parameters
                data_params = params.get('data', '')
                
                # Check if it's in the format "product_name,price,is_grocery"
                if ',' in data_params:
                    parts = data_params.split(',')
                    if len(parts) >= 2:
                        product_name = parts[0]
                        price = parts[1]
                        # Format to product_name#price for Arduino
                        data = f"{product_name}#{price}"
                    else:
                        data = data_params
                else:
                    data = data_params
                
                ser.write(f"WRITE:{data}\n".encode())
                logging.info(f"Sent WRITE command: {data}")
                
                # Wait for Arduino to respond
                time.sleep(1)
                response = ""
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8').strip()
                    logging.info(f"Arduino response: {response}")
                
                if "OK:Write successful" in response:
                    logging.info("Tag write successful")
                else:
                    logging.warning(f"Tag write may have failed or no response: {response}")
                
            elif cmd_type == 'reset_tag':
                ser.write(b"RESET\n")
                logging.info("Sent RESET command")
                
                # Wait for Arduino to respond
                time.sleep(1)
                response = ""
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8').strip()
                    logging.info(f"Arduino response: {response}")
                
                if "OK:Write successful" in response:  # Reset also returns this
                    logging.info("Tag reset successful")
                else:
                    logging.warning(f"Tag reset may have failed or no response: {response}")
            
            elif cmd_type == 'READC':
                # This is a control-only read command that won't trigger normal flow
                logging.info("Sending READC command to Arduino (control-only read)")
                ser.write(b"READ\n")  # We still send READ to Arduino
                
                # Wait for Arduino to respond with DATA:
                data_received = False
                read_data = None
                tag_id = params.get('tag_id', 'unknown')
                
                for _ in range(10):  # Try up to 10 times
                    time.sleep(0.5)
                    if ser.in_waiting > 0:
                        response = ser.readline().decode('utf-8').strip()
                        logging.info(f"Control-only read response: {response}")
                        
                        if response.startswith("DATA:"):
                            read_data = response[5:].strip()
                            # Store in control_results table only
                            try:
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS control_results (
                                        id INT AUTO_INCREMENT PRIMARY KEY,
                                        tag_id VARCHAR(100),
                                        data TEXT,
                                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                                    )
                                """)
                                cursor.execute(
                                    "INSERT INTO control_results (tag_id, data) VALUES (%s, %s)",
                                    (tag_id, read_data)
                                )
                                logging.info(f"Stored control-only read result: {read_data}")
                                data_received = True
                                break
                            except Exception as e:
                                logging.error(f"Error storing control result: {e}")
                
                        # Log result
                        if not data_received:
                            logging.warning(f"Failed to get data for control-only read")
                
            elif cmd_type == 'read_tag':
                # Check if this is for control mode
                if is_control:
                    logging.info("Processing read_tag command for CONTROL MODE")
                    # Set a flag to indicate control mode for next card read
                    cursor.execute(
                        "INSERT INTO commands (command_type, parameters, status, timestamp) VALUES (%s, %s, %s, %s)",
                        ('_control_read_flag', '{}', 'pending', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    logging.info("★★★ Set control flag for next RFID read ★★★")
                
                # Don't send READ command here - it will be sent when a card is detected
                logging.info(f"Read tag command registered (control mode: {is_control})")
                
            elif cmd_type == 'weigh_item':
                is_control = params.get('control_mode', False)
                
                # Send the weigh command to Arduino
                ser.write(b"w\n")
                logging.info(f"Sent weigh_item command (control mode: {is_control})")
                
                # Wait for Arduino to respond with Weight:
                time.sleep(1)
                
            elif cmd_type == 'tare':
                ser.write(b"t\n")
                logging.info("Sent tare command")
                
                # Wait for Arduino to respond
                time.sleep(1)
                
            elif cmd_type == 'open_lid':
                # For regular cart operations, this is simulated
                # But for control page, send actual command to Arduino
                if is_control:
                    ser.write(b"OPEN_LID\n")
                    logging.info("Sent OPEN_LID command to Arduino")
                else:
                    logging.info(f"Simulating open lid command (no actual command sent to Arduino)")
            
            # Mark command as completed
            cursor.execute(
                "UPDATE commands SET status = 'complete' WHERE id = %s",
                (cmd_id,)
            )
            
        except Exception as e:
            logging.error(f"Error sending command {cmd_type} to Arduino: {e}")
            logging.exception("Exception details:")
            # Mark command as failed
            cursor.execute(
                "UPDATE commands SET status = 'failed' WHERE id = %s",
                (cmd_id,)
            )

def main():
    # Connect to database and Arduino
    db_conn = connect_to_database()
    serial_conn = connect_to_arduino()
    
    # Track control mode state
    control_mode_active = False
    control_timeout = 0
    
    try:
        cursor = db_conn.cursor()
        
        logging.info("Serial handler started. Listening for Arduino data...")
        
        while True:
            # First, check for control_mode flags
            try:
                cursor.execute(
                    "SELECT id FROM commands WHERE command_type = '_control_read_flag' AND status = 'pending' LIMIT 1"
                )
                control_flag = cursor.fetchone()
                if control_flag:
                    control_mode_active = True
                    control_timeout = time.time() + 30  # 30 seconds timeout
                    cursor.execute(
                        "UPDATE commands SET status = 'complete' WHERE id = %s",
                        (control_flag[0],)
                    )
                    logging.info("★★★ Control mode ACTIVATED for next RFID read ★★★")
            except Exception as e:
                logging.error(f"Error checking control mode: {e}")
            
            # Reset control mode if timeout is exceeded
            if control_mode_active and time.time() > control_timeout:
                control_mode_active = False
                logging.info("Control mode DEACTIVATED due to timeout")
            
            # Process pending commands
            check_commands(cursor, serial_conn)
            db_conn.commit()
            
            # Check if there's data available from Arduino
            if serial_conn.in_waiting > 0:
                line = serial_conn.readline().decode('utf-8').strip()
                
                if line:
                    logging.info(f"Received from Arduino: {line}")
                    
                    if line.startswith("CARD:"):
                        tag_id = line[5:].strip()
                        
                        # Check if we're in control mode
                        if control_mode_active:
                            logging.info(f"★★★ Processing CONTROL RFID scan for tag: {tag_id} ★★★")
                            
                            # Direct READ command for control mode
                            serial_conn.write(b"READ\n")
                            logging.info("Sent READ command for control mode")
                            
                            # Wait for response
                            read_data = None
                            for _ in range(10):  # Try up to 10 times
                                time.sleep(0.5)
                                if serial_conn.in_waiting > 0:
                                    response = serial_conn.readline().decode('utf-8').strip()
                                    logging.info(f"Control read response: {response}")
                                    
                                    if response.startswith("DATA:"):
                                        read_data = response[5:].strip()
                                        break
                            
                            # Store in control_results table only
                            if read_data:
                                # Create table if it doesn't exist
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS control_results (
                                        id INT AUTO_INCREMENT PRIMARY KEY,
                                        tag_id VARCHAR(100),
                                        data TEXT,
                                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                                    )
                                """)
                                
                                # Store the data
                                cursor.execute(
                                    "INSERT INTO control_results (tag_id, data) VALUES (%s, %s)",
                                    (tag_id, read_data)
                                )
                                db_conn.commit()
                                logging.info(f"✓✓✓ Stored control read result: {read_data}")
                            
                            # Reset control mode after successful read
                            control_mode_active = False
                            logging.info("Control mode DEACTIVATED after read")
                        else:
                            # Normal shopping cart flow
                            process_card_scan(cursor, tag_id, serial_conn)
                            db_conn.commit()
                    elif line.startswith("FRAUD:"):
                        reason = line[6:].strip()
                        process_fraud_alert(cursor, reason)
                        db_conn.commit()
                    elif line.startswith("Weight:"):
                        try:
                            # Extract the weight value
                            weight_parts = line.split(':')
                            if len(weight_parts) > 1:
                                weight_str = weight_parts[1].strip()
                                weight = float(weight_str)
                                process_weight_data(cursor, weight)
                                db_conn.commit()
                            else:
                                logging.warning(f"Invalid weight format: {line}")
                        except ValueError as e:
                            logging.error(f"Invalid weight format: {e}")
                    elif line.startswith("DATA:"):
                        # This is handled directly in process_card_scan when we send READ command
                        # But we'll still log it for debugging
                        logging.info(f"Received DATA outside of processing: {line}")
                    elif line.startswith("OK:") or line.startswith("ERR:"):
                        # Log Arduino responses to commands
                        logging.info(f"Arduino response: {line}")
            
            # Sleep to avoid overloading the CPU
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logging.info("Serial handler stopped by user")
    except Exception as e:
        logging.error(f"Error in serial handler: {e}")
        logging.exception("Exception details:")
    finally:
        if serial_conn.is_open:
            serial_conn.close()
        cursor.close()
        db_conn.close()
        logging.info("Connections closed")

if __name__ == "__main__":
    main()