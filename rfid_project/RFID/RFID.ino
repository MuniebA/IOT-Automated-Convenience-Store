#include <SPI.h>
#include <MFRC522.h>

// RFID pins
#define SS_PIN 10
#define RST_PIN 9

// Other pins
#define BUZZER_PIN 6
#define LED_PIN 3

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  
  Serial.println("Initializing RFID System...");
  
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Initialize RFID key
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }
  
  // Initialize other components
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  Serial.println("RFID System Ready");
  signalSuccess();  // Signal that we're ready
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    processCommand(cmd);
  }
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
  else if (cmd == "CARD_CHECK") {
    // New lightweight command to just check for a card without reading data
    checkForCard();
  }
  else if (cmd == "STATUS") {
    Serial.println("OK:System ready");
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
  
  unsigned long startTime = millis();
  unsigned long timeout = 10000; // 10 seconds timeout
  
  while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    if (millis() - startTime > timeout) {
      Serial.println("ERR:Card read timeout");
      return;
    }
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
    Serial.print("ERR:Auth failed (");
    Serial.print(status);
    Serial.println(")");
    return;
  }
  
  status = mfrc522.MIFARE_Read(block, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("ERR:Read failed (");
    Serial.print(status);
    Serial.println(")");
    return;
  }
  
  String data = "";
  for (byte i = 0; i < 16; i++) {
    if (buffer[i] == 0) break;
    data += (char)buffer[i];
  }
  
  Serial.print("DATA:");
  Serial.println(data.length() > 0 ? data : "NoData#0");
  
  signalSuccess();
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void writeCard(String data) {
  Serial.println("Place your card...");
  
  unsigned long startTime = millis();
  unsigned long timeout = 10000; // 10 seconds timeout
  
  while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    if (millis() - startTime > timeout) {
      Serial.println("ERR:Card write timeout");
      return;
    }
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
    Serial.print("ERR:Auth failed (");
    Serial.print(status);
    Serial.println(")");
    return;
  }
  
  status = mfrc522.MIFARE_Write(block, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("ERR:Write failed (");
    Serial.print(status);
    Serial.println(")");
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

void signalSuccess() {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
}

void checkForCard() {
  // Just check if a card is present
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String rfid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      rfid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      rfid += String(mfrc522.uid.uidByte[i], HEX);
    }
    rfid.toUpperCase();
    
    // Send back just a simple response with the card UID
    Serial.println("CARD:" + rfid);
    
    // Don't halt the card yet - keep it available for a full READ command
    
  } else {
    // No card present
    Serial.println("NO_CARD");
  }
}