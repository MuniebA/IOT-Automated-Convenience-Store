#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <EEPROM.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define RST_PIN 9
#define SS_PIN 10
#define SERVO_PIN 6
#define IR_SENSOR_PIN A0

MFRC522 mfrc522(SS_PIN, RST_PIN);
Servo doorServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);

unsigned long lastCardScanTime = 0;
bool waitingForResponse = false;
String lastScannedUID = "";

int irThreshold = 300;
const int servoOpen = 90;
const int servoClosed = 0;

enum SystemState {
  MONITOR_MODE,
  REGISTER_MODE,
  MANUAL_OPEN
};

SystemState currentState = MONITOR_MODE;
String pendingUserUID = "";
String pendingUserName = "";

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  doorServo.attach(SERVO_PIN);
  doorServo.write(servoClosed);
  lcd.init();
  lcd.backlight();
  
  // Initialize in monitor mode
  lcd.setCursor(0, 0);
  lcd.print("Smart Store");
  lcd.setCursor(0, 1);
  lcd.print("System Ready");
  
  // Send ready signal to web interface
  Serial.println("STATUS:SYSTEM_READY");
  delay(2000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Scan your card");
  currentState = MONITOR_MODE;
}

void loop() {
  // Check for commands from web interface
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processWebCommand(command);
  }

  // Handle RFID card detection
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uidStr = getUID(mfrc522.uid.uidByte);
    handleRFIDCard(uidStr);
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
}

void processWebCommand(String command) {
  Serial.println("RECEIVED:" + command);
  
  if (command == "MONITOR_MODE") {
    currentState = MONITOR_MODE;
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Scan your card");
    Serial.println("STATUS:MONITOR_MODE_ACTIVE");
    
  } else if (command == "REGISTER_MODE") {
    currentState = REGISTER_MODE;
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Registration");
    lcd.setCursor(0, 1);
    lcd.print("Scan new card");
    Serial.println("STATUS:REGISTER_MODE_ACTIVE");
    
  } else if (command == "MANUAL_OPEN") {
    Serial.println("ACCESS:MANUAL_OVERRIDE:Admin");
    openDoor();
    detectMovement();
    
  } else if (command == "CALIBRATE_IR") {
    calibrateIRSensor();
    
  } else if (command.startsWith("ADD_USER:")) {
    // Format: ADD_USER:UID:Name
    int firstColon = command.indexOf(':', 9);
    if (firstColon > 0) {
      pendingUserUID = command.substring(9, firstColon);
      pendingUserName = command.substring(firstColon + 1);
      
      // Switch to registration mode for this specific user
      currentState = REGISTER_MODE;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Register:");
      lcd.setCursor(0, 1);
      lcd.print(pendingUserName);
      Serial.println("STATUS:WAITING_FOR_CARD:" + pendingUserName);
    }
    
  } else if (command == "GET_STATUS") {
    reportSystemStatus();
    
  } else {
    Serial.println("ERROR:UNKNOWN_COMMAND:" + command);
  }
}

void handleRFIDCard(String uidStr) {
  if (currentState == REGISTER_MODE) {
    // Registration mode - keep existing logic
    if (pendingUserName != "") {
      // Register the specific pending user
      saveToEEPROM(uidStr, pendingUserName);
      Serial.println("REGISTERED:" + uidStr + ":" + pendingUserName);
      
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Registered:");
      lcd.setCursor(0, 1);
      lcd.print(pendingUserName);
      delay(2000);
      
      // Clear pending user and return to monitor mode
      pendingUserUID = "";
      pendingUserName = "";
      currentState = MONITOR_MODE;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Scan your card");
      
    } else {
      // General registration mode - get name from EEPROM or register as unknown
      Serial.println("CARD_SCANNED:" + uidStr);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Card: " + uidStr);
      lcd.setCursor(0, 1);
      lcd.print("Waiting for name");
    }
    
  } else if (currentState == MONITOR_MODE) {
    // CHANGED: Instead of checking local EEPROM and granting access,
    // send CARD_SCANNED and let Python system decide
    Serial.println("CARD_SCANNED:" + uidStr);
    
    // Show processing message on LCD
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Processing...");
    lcd.setCursor(0, 1);
    lcd.print("Please wait");
    
    // NOTE: Door will open when Python sends "MANUAL_OPEN" command
    // after processing through MQTT/Cloud
  }
}

String getUID(byte* uid) {
  String uidStr = "";
  for (byte i = 0; i < 4; i++) {
    if (uid[i] < 0x10) uidStr += "0";
    uidStr += String(uid[i], HEX);
  }
  uidStr.toUpperCase();
  return uidStr;
}

void saveToEEPROM(String uidStr, String name) {
  int baseAddr = getEEPROMAddress(uidStr);
  for (int i = 0; i < 12; i++) {
    EEPROM.write(baseAddr + i, i < uidStr.length() ? uidStr[i] : 0);
  }
  for (int i = 0; i < 20; i++) {
    EEPROM.write(baseAddr + 12 + i, i < name.length() ? name[i] : 0);
  }
}

String readFromEEPROM(String uidStr) {
  for (int base = 0; base < EEPROM.length(); base += 32) {
    String storedUID = "";
    for (int i = 0; i < 12; i++) {
      char c = EEPROM.read(base + i);
      if (c == 0) break;
      storedUID += c;
    }
    if (storedUID == uidStr) {
      String name = "";
      for (int i = 0; i < 20; i++) {
        char c = EEPROM.read(base + 12 + i);
        if (c == 0) break;
        name += c;
      }
      return name;
    }
  }
  return "";
}

int getEEPROMAddress(String uidStr) {
  for (int base = 0; base < EEPROM.length(); base += 32) {
    String storedUID = "";
    for (int i = 0; i < 12; i++) {
      char c = EEPROM.read(base + i);
      if (c == 0) break;
      storedUID += c;
    }
    if (storedUID == uidStr || storedUID == "") {
      return base;
    }
  }
  return 0;
}

void openDoor() {
  Serial.println("STATUS:DOOR_OPENING");
  doorServo.write(servoOpen);
  delay(2000);
  doorServo.write(servoClosed);
  Serial.println("STATUS:DOOR_CLOSED");
}

void detectMovement() {
  Serial.println("STATUS:MONITORING_MOVEMENT");
  unsigned long start = millis();
  bool movementDetected = false;
  
  while (millis() - start < 5000) {
    int irValue = analogRead(IR_SENSOR_PIN);
    if (irValue < irThreshold) {
      movementDetected = true;
      Serial.println("MOVEMENT:DETECTED");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Movement");
      lcd.setCursor(0, 1);
      lcd.print("Confirmed");
      delay(2000);
      break;
    }
  }
  
  if (!movementDetected) {
    Serial.println("MOVEMENT:NONE_DETECTED");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("No Movement!");
    lcd.setCursor(0, 1);
    lcd.print("Security Alert");
    delay(2000);
  }
}

void calibrateIRSensor() {
  const int samples = 50;
  int sum = 0;
  Serial.println("STATUS:IR_CALIBRATION_START");

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Calibrating IR");
  lcd.setCursor(0, 1);
  lcd.print("Please wait...");

  for (int i = 0; i < samples; i++) {
    int value = analogRead(IR_SENSOR_PIN);
    sum += value;
    Serial.println("IR_SAMPLE:" + String(i + 1) + ":" + String(value));
    delay(100);
  }

  int avg = sum / samples;
  irThreshold = avg - 30;

  Serial.println("IR_CALIBRATION:COMPLETE:" + String(avg) + ":" + String(irThreshold));
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("IR Calibrated!");
  lcd.setCursor(0, 1);
  lcd.print("Threshold:" + String(irThreshold));
  delay(2000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Scan your card");
}

void reportSystemStatus() {
  Serial.println("STATUS:DOOR_STATE:" + String(currentState == MONITOR_MODE ? "READY" : "BUSY"));
  Serial.println("STATUS:IR_THRESHOLD:" + String(irThreshold));
  Serial.println("STATUS:MODE:" + String(currentState == MONITOR_MODE ? "MONITOR" : (currentState == REGISTER_MODE ? "REGISTER" : "MANUAL")));
}
