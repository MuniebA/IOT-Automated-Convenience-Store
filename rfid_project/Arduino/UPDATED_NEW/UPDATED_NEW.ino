#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN         9
#define SS_PIN          10
#define BUZZER_PIN      6
#define LED_PIN         3
#define TRIG_PIN        7
#define ECHO_PIN        8

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

bool tagScanned = false;
bool objectPlaced = false;
bool fraudDetected = false;
bool cooldownActive = false;

unsigned long scanTimer = 0;
unsigned long placementCooldownStart = 0;

const unsigned long PLACE_TIMEOUT = 10000;
const unsigned long PLACEMENT_COOLDOWN = 3000;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  SPI.begin();
  mfrc522.PCD_Init();

  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println("System Ready. Awaiting command or RFID scan...");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    processCommand(cmd);
  }

  long distance = getDistance();

  if (distance < 15) {
    if (!tagScanned) {
      signalFraud("Unscanned product placed");
    } else if (!objectPlaced) {
      objectPlaced = true;
      cooldownActive = true;
      placementCooldownStart = millis();
      Serial.println("Item placed correctly.");
    } else if (!cooldownActive) {
      signalFraud("Multiple items placed after one scan");
    }
    delay(500);
  }

  if (cooldownActive && millis() - placementCooldownStart >= PLACEMENT_COOLDOWN) {
    cooldownActive = false;
    Serial.println("Cooldown over. Monitoring resumed.");
  }

  if (tagScanned && !objectPlaced && millis() - scanTimer > PLACE_TIMEOUT) {
    signalFraud("No item placed after scan");
  }

  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
  String uid = readUID();
  Serial.println("CARD:" + uid);  // This line will now trigger the Python handler
  tagScanned = true;
  objectPlaced = false;
  fraudDetected = false;
  cooldownActive = false;
  scanTimer = millis();
  blinkOnce();
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  delay(500);
}
}

// ---------- RFID Functions ----------

String readUID() {
  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void readCard() {
  if (!waitForCard()) return;

  byte block = 8;
  byte buffer[18];
  byte size = sizeof(buffer);

  if (!authenticate(block)) return;

  MFRC522::StatusCode status = mfrc522.MIFARE_Read(block, buffer, &size);
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

  endRFID();
  blinkOnce();
}

void writeCard(String data) {
  if (!waitForCard()) return;
  if (data.length() > 16) {
    Serial.println("ERR:Data too long");
    return;
  }

  byte block = 8;
  byte buffer[16];
  for (byte i = 0; i < 16; i++) {
    buffer[i] = i < data.length() ? data[i] : 0;
  }

  if (!authenticate(block)) return;

  MFRC522::StatusCode status = mfrc522.MIFARE_Write(block, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.println("ERR:Write failed");
    return;
  }

  Serial.println("OK:Write successful");
  endRFID();
  blinkOnce();
}

void resetCard() {
  writeCard("");
}

bool waitForCard() {
  Serial.println("Place your card...");
  unsigned long timeout = 10000;
  unsigned long start = millis();

  while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    if (millis() - start > timeout) {
      Serial.println("ERR:Timeout");
      return false;
    }
    delay(100);
  }
  return true;
}

bool authenticate(byte block) {
  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.println("ERR:Auth failed");
    return false;
  }
  return true;
}

void endRFID() {
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

// ---------- Fraud / Utility Functions ----------

long getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  return pulseIn(ECHO_PIN, HIGH) * 0.034 / 2;
}

void signalFraud(String reason) {
  Serial.println("FRAUD: " + reason);
  fraudDetected = true;
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }

  tagScanned = false;
  objectPlaced = false;
  cooldownActive = false;
  scanTimer = 0;
}

void blinkOnce() {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
}

// ---------- Serial Command Interface ----------

void processCommand(String cmd) {
  if (cmd == "READ") {
    readCard();
  } else if (cmd.startsWith("WRITE:")) {
    String data = cmd.substring(6);
    writeCard(data);
  } else if (cmd == "RESET") {
    resetCard();
  } else if (cmd == "STATUS") {
    Serial.println("OK:System ready");
  } else {
    Serial.println("ERR:Unknown command");
  }
}
