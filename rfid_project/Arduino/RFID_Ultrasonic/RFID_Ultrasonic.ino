#include <SPI.h>
#include <MFRC522.h>
#include <HX711_ADC.h>
#include <Servo.h>

// RFID pins
#define SS_PIN 10
#define RST_PIN 9

// Other pins
#define BUZZER_PIN 6
#define LED_PIN 3
#define HX711_DOUT 4
#define HX711_SCK 5
#define SERVO_PIN A0
#define TRIG_PIN 7   // Ultrasonic trigger pin
#define ECHO_PIN 8   // Ultrasonic echo pin

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
HX711_ADC LoadCell(HX711_DOUT, HX711_SCK);
Servo lidServo;

const int OPEN_ANGLE = 90;   // Lid fully open position
const int CLOSED_ANGLE = 0;  // Lid closed position

// Timing constants
const long WEIGHT_INTERVAL = 1000;     // Send weight every second
const long PLACEMENT_TIMEOUT = 10000;  // 10 seconds to place item after scan
const long FRAUD_RESET_TIMEOUT = 15000; // Auto-reset fraud status after 15 seconds (increased from 8 seconds)
const long DEBOUNCE_TIME = 500;       // Time to wait between fraud checks (reduced from 1500ms)
unsigned long startupDelayEnd = 0;
const long STARTUP_DELAY = 5000;

// Thresholds
const int DISTANCE_THRESHOLD = 15;     // Distance in cm to detect an object
const float WEIGHT_THRESHOLD = 10.0;   // Minimum weight for item detection
const int DISTANCE_CHANGE_THRESHOLD = 5; // Minimum distance change to trigger detection

// State variables
boolean tagScanned = false;
boolean objectPlaced = false;
boolean fraudDetected = false;
String fraudType = "none";             // 'none', 'missing_item', 'unscanned_item', 'multiple_items'
long lastDistance = 100;               // Start with a high value (no object)
float lastWeight = 0;
String lastRFID = "";

// State for continuous detection
boolean resetPending = false;
boolean itemProcessComplete = false;

// Timing variables
unsigned long lastWeightSent = 0;
unsigned long lastRFIDScanTime = 0;
unsigned long lastObjectPlacedTime = 0;
unsigned long fraudDetectedTime = 0;
unsigned long lastFraudCheckTime = 0;
unsigned long debounceStartTime = 0;
unsigned long resetStartTime = 0;
boolean inDebounce = false;

// Debug variables
boolean debugEnabled = true;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Initialize RFID key
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }
  
  // Initialize other components
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  lidServo.attach(SERVO_PIN);
  lidServo.write(CLOSED_ANGLE);
  
  // Initialize load cell
  LoadCell.begin();
  LoadCell.start(2000, true);
  if (LoadCell.getTareTimeoutFlag()) {
    Serial.println("ERR:Load cell timeout");
    return;
  }
  LoadCell.setCalFactor(696.0);
  
  // Test buzzer and LED
  digitalWrite(BUZZER_PIN, HIGH);
  digitalWrite(LED_PIN, HIGH);
  delay(300);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_PIN, LOW);

  startupDelayEnd = millis() + STARTUP_DELAY;
  
  Serial.println("Smart Cart System Ready");
  printDebugInfo(getDistance());
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    processCommand(cmd);
  }
  
  // Update weight readings
  if (LoadCell.update()) {
    lastWeight = LoadCell.getData();
  }
  
  // Read ultrasonic sensor
  long currentDistance = getDistance();
  
  // Check for RFID card
  String rfid = readRFIDCard();
  if (rfid != "") {
    lastRFID = rfid;
    lastRFIDScanTime = millis();
    
    // Reset fraud flags when new tag is scanned
    fraudDetected = false;
    fraudType = "none";
    tagScanned = true;
    objectPlaced = false;
    itemProcessComplete = false;
    inDebounce = true;
    debounceStartTime = millis();
    
    signalSuccess();
    openLid();  // Open lid for product placement
    
    Serial.print("Product scanned: ");
    Serial.println(rfid);
    
    if (debugEnabled) {
      printDebugInfo(currentDistance);
    }
  }
  
  // Wait for debounce period after scanning before checking for fraud
  if (inDebounce && millis() - debounceStartTime > DEBOUNCE_TIME) {
    inDebounce = false;
  }
  
  // Only check for fraud if we're not in debounce period
  if (!inDebounce && millis() - lastFraudCheckTime > 300) {
    checkForFraud(currentDistance);
    lastFraudCheckTime = millis();
  }
  
  // Automatically close lid after successful placement
  if (tagScanned && objectPlaced && !itemProcessComplete && millis() - lastObjectPlacedTime > 2000) {
    closeLid();
    itemProcessComplete = true;
    
    // Reset state to allow scanning next item
    tagScanned = false;
    
    Serial.println("Item processing complete. Ready for next item.");
  }
  
  // Auto-reset fraud status after timeout
  if (fraudDetected && millis() - fraudDetectedTime > FRAUD_RESET_TIMEOUT) {
    resetSystemState();
    Serial.println("Fraud status auto-reset. System ready for next detection.");
  }
  
  // Send periodic data update
  if (millis() - lastWeightSent >= WEIGHT_INTERVAL) {
    sendDataUpdate(currentDistance);
    lastWeightSent = millis();
  }
  
  // Store current distance for next comparison
  lastDistance = currentDistance;
  
  // Small delay to avoid rapid polling
  delay(50);
}

void resetSystemState() {
  fraudDetected = false;
  fraudType = "none";
  tagScanned = false;
  objectPlaced = false;
  itemProcessComplete = false;
  resetPending = false;
}

void checkForFraud(long currentDistance) {
  // Skip fraud detection if already in fraud state
  if (fraudDetected) {
    return;
  }
  
  // Log changes in distance for debugging
  if (debugEnabled && abs(currentDistance - lastDistance) > 2) {
    Serial.print("Distance Change: ");
    Serial.print(currentDistance);
    Serial.print(" cm (last: ");
    Serial.print(lastDistance);
    Serial.print(", diff: ");
    Serial.print(lastDistance - currentDistance);
    Serial.println(" cm)");
  }
  
  // Scenario 1: Item scanned but not placed within timeout
  if (tagScanned && !objectPlaced && !itemProcessComplete) {
    if (millis() - lastRFIDScanTime > PLACEMENT_TIMEOUT) {
      Serial.println("FRAUD DETECTED: Item scanned but not placed within timeout");
      fraudDetected = true;
      fraudType = "missing_item";
      fraudDetectedTime = millis();
      Serial.println("FRAUD:Item scanned but not placed in cart");
      alertFraud();
      closeLid();  // Close lid after fraud timeout
    }
  }
  
  // Scenario 2: Item placed without scanning (unscanned item)
  // Only check if: not currently handling a scanned tag, not in debounce period, and no recent scan
  if (!tagScanned && !inDebounce) {
    // Check for significant distance change (object detected)
    // Calculate absolute difference in distance
    long distanceDiff = abs(lastDistance - currentDistance);
    
    // If there's a significant change (5cm or more) AND current distance is within detection range
    if (distanceDiff > 5 && currentDistance < 15) {
      // Make sure no recent RFID scan (over 2 seconds)
      if (millis() - lastRFIDScanTime > 2000 || lastRFIDScanTime == 0) {
        Serial.print("FRAUD DETECTED: Unscanned item - distance change of ");
        Serial.print(distanceDiff);
        Serial.println(" cm");
        fraudDetected = true;
        fraudType = "unscanned_item";
        fraudDetectedTime = millis();
        Serial.println("FRAUD:Unscanned item detected in cart");
        alertFraud();
      }
    }
  }
  
  // Scenario 3: Multiple items placed for single scan
  if (tagScanned && objectPlaced && !itemProcessComplete && !fraudDetected) {
    // If distance suddenly decreases significantly after object already placed
    long distanceDiff = lastDistance - currentDistance;
    if (distanceDiff > 5) {
      Serial.print("FRAUD DETECTED: Multiple items - additional distance decrease of ");
      Serial.print(distanceDiff);
      Serial.println(" cm");
      fraudDetected = true;
      fraudType = "multiple_items";
      fraudDetectedTime = millis();
      Serial.println("FRAUD:Multiple items detected for single scan");
      alertFraud();
    }
  }
  
  // Check for object placement (when expecting an item)
  if (tagScanned && !objectPlaced && !itemProcessComplete) {
    if (currentDistance < DISTANCE_THRESHOLD) {
      objectPlaced = true;
      lastObjectPlacedTime = millis();
      Serial.println("Item placed correctly");
      
      // Show weight of placed item
      Serial.print("Item weight: ");
      Serial.print(lastWeight);
      Serial.println(" g");
    }
  }
}

void printDebugInfo(long currentDistance) {
  Serial.println("-------- DEBUG INFO --------");
  Serial.print("Distance: ");
  Serial.print(currentDistance);
  Serial.print(" cm (last: ");
  Serial.print(lastDistance);
  Serial.println(" cm)");
  
  Serial.print("Weight: ");
  Serial.print(lastWeight);
  Serial.println(" g");
  
  Serial.print("Tag scanned: ");
  Serial.println(tagScanned ? "YES" : "NO");
  
  Serial.print("Object placed: ");
  Serial.println(objectPlaced ? "YES" : "NO");
  
  Serial.print("Item process complete: ");
  Serial.println(itemProcessComplete ? "YES" : "NO");
  
  Serial.print("Fraud detected: ");
  Serial.print(fraudDetected ? "YES" : "NO");
  if (fraudDetected) {
    Serial.print(" (Type: ");
    Serial.print(fraudType);
    Serial.println(")");
  } else {
    Serial.println();
  }
  
  if (tagScanned) {
    unsigned long timeSinceScan = millis() - lastRFIDScanTime;
    Serial.print("Time since scan: ");
    Serial.print(timeSinceScan / 1000.0);
    Serial.println(" seconds");
    
    unsigned long timeRemaining = (PLACEMENT_TIMEOUT > timeSinceScan) ? 
      (PLACEMENT_TIMEOUT - timeSinceScan) : 0;
    Serial.print("Placement time remaining: ");
    Serial.print(timeRemaining / 1000.0);
    Serial.println(" seconds");
  }
  
  Serial.println("----------------------------");
}

void alertFraud() {
  // Visual and audible alert
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    delay(200);
  }
}

long getDistance() {
  // Clear the trigger pin
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  
  // Set the trigger pin HIGH for 10 microseconds
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read the echo pin, convert to distance in cm
  long duration = pulseIn(ECHO_PIN, HIGH);
  long distance = duration * 0.034 / 2;
  
  // Cap the maximum distance to avoid extreme readings
  if (distance > 400) {
    distance = 400;
  }
  
  return distance;
}

void processCommand(String cmd) {
  if (cmd == "READ") {
    readCard();
  } 
  else if (cmd.startsWith("WRITE:")) {
    String dataToWrite = cmd.substring(6);
    writeCard(dataToWrite);
  } 
  else if (cmd == "RESET") {
    resetCard();
  }
  else if (cmd == "w") {
    Serial.println(lastWeight);
  }
  else if (cmd == "t") {
    LoadCell.tareNoDelay();
    Serial.println("OK:Tare complete");
  }
  else if (cmd == "o") {
    openLid();
  }
  else if (cmd == "c") {
    closeLid();
  }
  else if (cmd == "distance") {
    Serial.print("DISTANCE:");
    Serial.println(getDistance());
  }
  else if (cmd == "reset_fraud") {
    // Reset fraud detection state
    resetSystemState();
    Serial.println("OK:System state reset");
  }
  else if (cmd == "debug") {
    // Toggle debug mode
    debugEnabled = !debugEnabled;
    Serial.print("Debug mode ");
    Serial.println(debugEnabled ? "enabled" : "disabled");
    if (debugEnabled) {
      printDebugInfo(getDistance());
    }
  }
  else if (cmd == "status") {
    // Print current system status
    printDebugInfo(getDistance());
  }
  else if (cmd == "test_fraud") {
    // Simulate each fraud type for testing
    String fraudTypes[] = {"missing_item", "unscanned_item", "multiple_items"};
    static int fraudIndex = 0;
    
    fraudDetected = true;
    fraudType = fraudTypes[fraudIndex];
    fraudDetectedTime = millis();
    
    Serial.print("TEST FRAUD: Simulating ");
    Serial.println(fraudType);
    Serial.println("FRAUD:" + fraudType);  // This is the key message that triggers fraud alerts
    alertFraud();
    
    fraudIndex = (fraudIndex + 1) % 3; // Cycle through types
  }
  else {
    Serial.println("ERR:Unknown command");
  }
}

String readRFIDCard() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    return "";
  }
  
  String rfid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    rfid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    rfid += String(mfrc522.uid.uidByte[i], HEX);
  }
  rfid.toUpperCase();
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  
  return rfid;
}

void readCard() {
  Serial.println("Place your card...");
  
  while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(100);
  }
  
  byte block = 8;
  byte buffer[18];
  byte size = sizeof(buffer);
  
  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A,
    block,
    &key,
    &(mfrc522.uid)
  );
  
  if (status != MFRC522::STATUS_OK) {
    Serial.println("ERR:Auth failed");
    return;
  }
  
  status = mfrc522.MIFARE_Read(block, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    Serial.println("ERR:Read failed");
    return;
  }
  
  String data = "";
  for (byte i = 0; i < 16; i++) {
    if (buffer[i] == 0) break;
    data += (char)buffer[i];
  }
  
  Serial.print("DATA:");
  Serial.println(data.length() > 0 ? data : "NoData#0");
  
  // Trigger the same actions as a regular RFID scan
  lastRFID = mfrc522.uid.uidByte[0];
  lastRFIDScanTime = millis();
  fraudDetected = false;
  fraudType = "none";
  tagScanned = true;
  objectPlaced = false;
  itemProcessComplete = false;
  
  // Start debounce period
  inDebounce = true;
  debounceStartTime = millis();
  
  signalSuccess();
  openLid();
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void writeCard(String data) {
  Serial.println("Place your card...");
  
  while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(100);
  }
  
  byte block = 8;
  
  if (data.length() > 16) {
    Serial.println("ERR:Data too long");
    return;
  }
  
  byte buffer[16];
  for (byte i = 0; i < 16; i++) {
    buffer[i] = i < data.length() ? data[i] : 0;
  }
  
  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A,
    block,
    &key,
    &(mfrc522.uid)
  );
  
  if (status != MFRC522::STATUS_OK) {
    Serial.println("ERR:Auth failed");
    return;
  }
  
  status = mfrc522.MIFARE_Write(block, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.println("ERR:Write failed");
    return;
  }
  
  Serial.println("OK:Write successful");
  signalSuccess();
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void resetCard() {
  writeCard("");
}

void openLid() {
  lidServo.write(OPEN_ANGLE);
  Serial.println("OK:Lid opened");
}

void closeLid() {
  lidServo.write(CLOSED_ANGLE);
  Serial.println("OK:Lid closed");
}

void signalSuccess() {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
}

void sendDataUpdate(long currentDistance) {
  // Format: RFID,Weight,Distance,FraudStatus,FraudType
  Serial.print("DATA:");
  Serial.print(lastRFID);
  Serial.print(",");
  Serial.print(lastWeight);
  Serial.print(",");
  Serial.print(currentDistance);
  Serial.print(",");
  Serial.print(fraudDetected ? "1" : "0");
  Serial.print(",");
  Serial.println(fraudType);
}