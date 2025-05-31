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

int irThreshold = 300; // Adjust based on IR sensor readings
const int servoOpen = 90;
const int servoClosed = 0;

enum SystemState {
  IDLE,
  REGISTER_MODE,
  MONITOR_MODE
};

SystemState currentState = IDLE;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  doorServo.attach(SERVO_PIN);
  doorServo.write(servoClosed);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("System Ready");
  lcd.setCursor(0, 1);
  lcd.print("Select Mode...");
  delay(2000);
  showMainMenu();
}

void loop() {
  if (Serial.available()) {
    char input = Serial.read();
    switch (input) {
      case '1':
        currentState = REGISTER_MODE;
        Serial.println("\n-- Registration Mode --");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Registering...");
        break;
      case '2':
        currentState = MONITOR_MODE;
        Serial.println("\n-- Monitor Mode --");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Scan your card");
        break;
      case '3':
        calibrateIRSensor();
        showMainMenu();
        break;
      default:
        Serial.println("Invalid input.");
        showMainMenu();
        break;
    }
  }

  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;

  String uidStr = getUID(mfrc522.uid.uidByte);

  if (currentState == REGISTER_MODE) {
    Serial.print("Enter name for UID ");
    Serial.print(uidStr);
    Serial.print(": ");
    while (!Serial.available());
    String name = Serial.readStringUntil('\n');
    name.trim();
    saveToEEPROM(uidStr, name);
    Serial.println("Registered!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Tag registered:");
    lcd.setCursor(0, 1);
    lcd.print(name);
    delay(2000);
    showMainMenu();
    currentState = IDLE;
  } else if (currentState == MONITOR_MODE) {
    String name = readFromEEPROM(uidStr);
    if (name != "") {
      Serial.println("Access granted: " + name);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Welcome,");
      lcd.setCursor(0, 1);
      lcd.print(name);
      openDoor();
      detectMovement();
    } else {
      Serial.println("Access denied: Unknown tag");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Access Denied");
      delay(2000);
    }
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Scan your card");
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}


void showMainMenu() {
  Serial.println("\n===== MAIN MENU =====");
  Serial.println("1. Register New Tag");
  Serial.println("2. Monitor Tags");
  Serial.println("3. Calibrate IR Sensor");
  Serial.print("Select mode (1/2/3): ");
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
  doorServo.write(servoOpen);
  delay(2000);
  doorServo.write(servoClosed);
}

void detectMovement() {
  unsigned long start = millis();
  bool movementDetected = false;
  while (millis() - start < 5000) {
    int irValue = analogRead(IR_SENSOR_PIN);
    if (irValue < irThreshold) {
      movementDetected = true;
      Serial.println("Movement detected!");
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
    Serial.println("No movement detected.");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("No Movement!");
    lcd.setCursor(0, 1);
    lcd.print("Scan Again");
    delay(2000);
  }
}

void calibrateIRSensor() {
  const int samples = 50;
  int sum = 0;
  Serial.println("\n-- IR Sensor Calibration --");
  Serial.println("Measuring 50 samples...");

  for (int i = 0; i < samples; i++) {
    int value = analogRead(IR_SENSOR_PIN);
    sum += value;
    Serial.print("Sample ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.println(value);
    delay(100);
  }

  int avg = sum / samples;
  int suggestedThreshold = avg - 30;

  Serial.println("\nAverage IR reading: " + String(avg));
  Serial.println("Suggested threshold: " + String(suggestedThreshold));
  Serial.println("Enter custom threshold or press Enter to use suggested:");

  String input = "";
  while (input == "") {
    if (Serial.available()) {
      input = Serial.readStringUntil('\n');
      input.trim();
    }
  }

  if (input.length() > 0) {
    irThreshold = input.toInt();
    Serial.println("New IR threshold set to: " + String(irThreshold));
  } else {
    irThreshold = suggestedThreshold;
    Serial.println("Using suggested threshold: " + String(irThreshold));
  }

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("IR Calibrated!");
  delay(2000);
}

