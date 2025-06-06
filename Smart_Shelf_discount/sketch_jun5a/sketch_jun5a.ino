#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP32Servo.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "Galaxy A35 5G 8295";
const char* password = "....mmmm";

// AWS Configuration
const char* AWS_IOT_ENDPOINT = "a2amimoaybc420-ats.iot.us-east-1.amazonaws.com";
const char* CLIENT_ID = "iot-convenience-store-shelf-001-production";

// MQTT Topics - Enhanced AI System
const char* TOPIC_SHELF_STATUS = "store/shelf/shelf-001/status";
const char* TOPIC_SHELF_INTERACTIONS = "store/shelf/shelf-001/interactions";
const char* TOPIC_SHELF_COMMANDS = "store/shelf/shelf-001/commands";
const char* TOPIC_AI_ANALYTICS = "store/shelf/shelf-001/ai_analytics";
const char* TOPIC_BEHAVIOR_UPDATES = "store/ai/behavior_updates";

// Enhanced API Gateway Configuration
const char* API_GATEWAY_URL = "https://z43jryv2y3.execute-api.us-east-1.amazonaws.com/test/rfid";

// Certificate Strings (Keep your existing certificates)
static const char AWS_CERT_CA[] PROGMEM = R"EOF(-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv
b3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj
ca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM
9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw
IFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6
VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L
93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm
jgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC
AYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA
A4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI
U5PMCCjjmCXPI6T53iHTfIUJrU6adTrCC2qJeHZERxhlbI1Bjjt/msv0tadQ1wUs
N+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V8viTO96LXFvKWlJbYK8U90vv
o/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJcJmApzyMZFo6IQ6XU
5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeXeGADbkpy
rqXRfboQnoZsG4q5WTP468SQvvG5
-----END CERTIFICATE-----)EOF";

static const char AWS_CERT_CRT[] PROGMEM = R"EOF(-----BEGIN CERTIFICATE-----
MIIDWTCCAkGgAwIBAgIUbgLD9sAvBBPAoVtq/fxDRuL48cUwDQYJKoZIhvcNAQEL
BQAwTTFLMEkGA1UECwxCQW1hem9uIFdlYiBTZXJ2aWNlcyBPPUFtYXpvbi5jb20g
SW5jLiBMPVNlYXR0bGUgU1Q9V2FzaGluZ3RvbiBDPVVTMB4XDTI1MDYwMjE3MDcx
MVoXDTQ5MTIzMTIzNTk1OVowHjEcMBoGA1UEAwwTQVdTIElvVCBDZXJ0aWZpY2F0
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMj06FpU/FomgoH6SGh6
Up8yet6S4Bi84YQP5RmYN1jglBFwY6f0g0z4g2mnj7Xbi/q6pGKeY4/UjCmWNdou
0xMb4Y7IMN2rSY92XqmThcx08e809dvLizzPPhmOlilm/bcD580i9CUv/tojWnU3
FFcMEra7TIKsWfTLu+cefhasvmS0DNbhXhmx9DAFgdsP9lg0isPf7n/OOhY71iUV
ETbRhs25e53+C4RyenuJ57ze+4iSriZrzLLQnqmff3JPKGtgi6tj+eBXRGjfUkkL
qzwgUBgqxFroNFdwzMU3OKUaS2aV4vMB+1F6XHfvsj2v6Tkk2534GpWMYYYNAKfc
evMCAwEAAaNgMF4wHwYDVR0jBBgwFoAU5oRSgBdcNzFQlZtH1ufOrivduYAwHQYD
VR0OBBYEFIR4bRqClKK9yZfc1vyGMcV+hWHTMAwGA1UdEwEB/wQCMAAwDgYDVR0P
AQH/BAQDAgeAMA0GCSqGSIb3DQEBCwUAA4IBAQBZZHn6uj2m6If6KF0zlcEB+gqO
ZQ+HEd3VT3FS6aNR1HmdSVnvBe3MKMDCgB/yyhwXGcj8WsoklLZikehqLL/jR1cH
3UluqP7m9zLDLVY1p1Vcb509JAa6Y1qvxbwL4M2zJ8S8yrEBY8x5UJXxUFG7Ef1F
MLmfq1cwsAa3S/Was9brpPOnedkprZApDEIaTzYjuXht+yYdVArA3LqdjqykEX0J
st1RpQ9OR1K0aLbS+XVta1Y3ukVNd9sOewmH4GH512v9pYLPpu6LW+Jk6tJ3WFeO
iQrxHP0s0EWDRtsHbbEmMt1vKZSz8E7l3+mwnyhRNidF4BqDbvSz4IgevU14
-----END CERTIFICATE-----)EOF";

static const char AWS_CERT_PRIVATE[] PROGMEM = R"EOF(-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAyPToWlT8WiaCgfpIaHpSnzJ63pLgGLzhhA/lGZg3WOCUEXBj
p/SDTPiDaaePtduL+rqkYp5jj9SMKZY12i7TExvhjsgw3atJj3ZeqZOFzHTx7zT1
28uLPM8+GY6WKWb9twPnzSL0JS/+2iNadTcUVwwStrtMgqxZ9Mu75x5+Fqy+ZLQM
1uFeGbH0MAWB2w/2WDSKw9/uf846FjvWJRURNtGGzbl7nf4LhHJ6e4nnvN77iJKu
JmvMstCeqZ9/ck8oa2CLq2P54FdEaN9SSQurPCBQGCrEWug0V3DMxTc4pRpLZpXi
8wH7UXpcd++yPa/pOSTbnfgalYxhhg0Ap9x68wIDAQABAoIBAQCGeqY3NSI+7gBu
HOBx0lISKQTih6WhyFyeNMjazOtU9c0AspZuIgnv62p9vN1GFOri2h4BxP7ZlKJL
fjMBlE46PnE+TKeu3951PABzOL7UKPpyWp2g/eBqzEFBdxL0F/D3lYx80cRSUoEY
14nEYRyid/jaAhNcaxwz3lcbfmNgpf4gRqiYRROqGUHbExuLxOWzuLegrgQgwsg8
zVVbUJNL6PToDzeeRqsB5Ie9VAakTcgbQ4dPNjfSEcLWW5PhakyWvPAuQ5l0n6YL
f+u6WQh4WDhm0Og0adekvnMl7tzTUF4o6dZCYtKsXuK+wRyHjuRXAragHCzNyusl
5hg+ceKRAoGBAPpqj9eMdun/hqEQwShfJbDdoKWQteerYX89E5AVtuUs/BNkw7+J
bvbrU45tCBOMZf5NHoIZGtTA1iNXqARi6g6ZGRn+JMx/wQr9qjc130LCncwVc6Dr
y0LBpSV1jFhW9JM0HXrntHdQL+NdAqsZmQpYn9gN1KY19cdmgbI5yMz7AoGBAM1w
BKW+bOHVdegAqznJ/YOEr2pay2/OcrCK00KtMXSzyW7l1VihPomrrgci0+BFNCY1
cxJD1oo3fVzm7yxMqp2Q0vJWjIDvUPZrSJVAMmLr2wmd8mKpAvHWq0mEgV0gOy4S
KuTUWfLMhRDTmMLXpjzNn9l0cT8veWkpiTRDxLhpAoGBAOFoanIsDh4z1IvG+RfO
Da9Wz/Q4foU6z1gpMiLQaQGBrKYIXetbWncI/P2HR23RQz3VTVDuKCi6LAdEMAlC
wEzDosSy74zksm+iRkXMSFtfs4qxBJQlq6E7jdxaIyqhmyWmE6M+TkPX+kM+xdge
ApQ9kiR4zqGOkN4cd0JmoUlhAoGAdsuE1HcWLU0rXhos6UDlaQzsBrs0EpY1+eJ9
IXxXMd3Y6FjdEuBC8oclHhlEndZGvqV/whsaT1ihFHyx51L6Ah1B7kKgAtrgXW5S
TYQO3ub2BUyhYe3Ltx7kc6G80KYXsp9s0F//F4iulblWB61+AoEBI1TTO69vLKGJ
JoDdm6kCgYEAwYdefWH+x30/Mqrz2DHGRgnpqC5dW6y3eLx14apNWfKKtfcBDWL1
xtVKAZA0pLNLXsHehg3bsL2QXCNEGkNUHN3PnQTvrLY2PpZ1wy3HrXXFTDN8HhSP
7xFXph5FOrDLKQVgocB6HQNFmmL0/TV9YAatjDknxMicK6jw4/LnncE=
-----END RSA PRIVATE KEY-----)EOF";

// Define pins
#define SDA_PIN 21
#define SCL_PIN 22
#define SERVO_PIN 4
#define RST_PIN 25
#define SS_PIN 5

// Initialize components
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo shelfServo;
MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

// Enhanced AI Product Information
String currentProductId = "prod_001";
String productName = "Loading...";
float regularPrice = 0.0;
float vipPrice = 0.0;
String productCategory = "General";
bool productIsPremium = false;
int inventoryLevel = 0;

// Enhanced Customer Profile Structure
struct EnhancedCustomerProfile {
  String customerId;
  String customerName;
  String customerType;
  bool isVip;
  String clusterId;
  bool aiEnhanced;
  int standardDiscount;
  float totalSpent;
  int totalVisits;
  bool behaviorAnalysisAvailable;
  String priceSenitivity;
  String shoppingFrequency;
  float avgBasketSize;
};

// Enhanced AI Discount Recommendation
struct EnhancedAIDiscountRecommendation {
  String recommendationId;
  int discountPercentage;
  float confidence;
  String reason;
  String recommendationType;  // "personal", "group", "fallback"
  int expiresInMinutes;
  bool isValid;
  String pipelineVersion;
  String generatedAt;
  float originalPrice;
  float discountedPrice;
};

EnhancedCustomerProfile currentCustomer;
EnhancedAIDiscountRecommendation currentDiscount;

// Enhanced System States
bool isIdle = true;
bool isDisplaying = false;
bool behaviorAnalysisTriggered = false;
unsigned long displayStartTime = 0;
unsigned long interactionStartTime = 0;
const unsigned long DISPLAY_DURATION = 20000;  // Extended for enhanced system

// Network states
bool wifiConnected = false;
bool mqttConnected = false;
unsigned long lastWiFiCheck = 0;
unsigned long lastMqttCheck = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastBehaviorAnalysis = 0;

// Enhanced Intervals
const unsigned long WIFI_CHECK_INTERVAL = 30000;
const unsigned long MQTT_CHECK_INTERVAL = 60000;
const unsigned long HEARTBEAT_INTERVAL = 300000;
const unsigned long BEHAVIOR_ANALYSIS_INTERVAL = 3600000; // 1 hour

// Current interaction tracking
String currentCardUID = "";
bool purchaseDetected = false;
unsigned long purchaseDetectionTime = 0;

// Function prototypes
void initializeWiFi();
void initializeMQTT();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void monitorConnections();
void sendEnhancedHeartbeat();
void publishEnhancedStatus(const char* status);
void publishEnhancedAIAnalytics(const char* eventType);
void handleEnhancedRFID();
String getCardUID();
EnhancedCustomerProfile checkCardWithEnhancedCloud(String cardUID);
EnhancedAIDiscountRecommendation getEnhancedAIDiscountRecommendation(String customerId, String productId);
void triggerBehaviorAnalysis(String customerId);
void logEnhancedInteractionToCloud(String action, bool includePurchaseData = false);
void showAccessDenied(String cardUID);
void loadEnhancedProductFromCloud();
void activateEnhancedAIProduct(EnhancedCustomerProfile customer, EnhancedAIDiscountRecommendation discount);
void displayEnhancedAIProduct();
void displayEnhancedDiscountInfo();
void returnToEnhancedIdle();
void showEnhancedConnectionStatus();
void showEnhancedAISystemStatus();
void detectPurchaseInteraction();
void showBehaviorAnalysisStatus();

void setup() {
  Serial.begin(115200);
  Serial.println("🤖 ENHANCED AI-POWERED SMART SHELF v6.0 🤖");
  Serial.println("============================================");
  Serial.println("🧠 Features: Dynamic Discounts, Behavior Analysis, ML Pipeline, Customer Clustering");
  Serial.println("📊 Data Sources: Transactions, Sessions, Profiles, Clusters, Purchase Behavior");
  
  // Initialize hardware
  SPI.begin();
  rfid.PCD_Init();
  Wire.begin(SDA_PIN, SCL_PIN);
  lcd.init();
  lcd.noBacklight();
  shelfServo.attach(SERVO_PIN);
  shelfServo.write(0);
  
  // Initialize enhanced cloud connections
  initializeWiFi();
  if (wifiConnected) {
    initializeMQTT();
    loadEnhancedProductFromCloud();
  }
  
  showEnhancedAISystemStatus();
  Serial.println("🎯 ENHANCED AI SYSTEM READY - Full Data Pipeline Active!");
}

void loop() {
  monitorConnections();
  sendEnhancedHeartbeat();
  
  if (mqttConnected) {
    mqttClient.loop();
  }
  
  // Enhanced operation with full cloud integration
  if (wifiConnected && mqttConnected) {
    handleEnhancedRFID();
    detectPurchaseInteraction();
    
    // Periodic behavior analysis trigger
    if (millis() - lastBehaviorAnalysis > BEHAVIOR_ANALYSIS_INTERVAL && !currentCustomer.customerId.isEmpty()) {
      triggerBehaviorAnalysis(currentCustomer.customerId);
    }
    
    if (isDisplaying && (millis() - displayStartTime >= DISPLAY_DURATION)) {
      returnToEnhancedIdle();
    }
  } else {
    // Show enhanced connection error
    if (millis() % 5000 < 100) {
      showEnhancedConnectionStatus();
    }
  }
  
  delay(10);
}

void initializeWiFi() {
  Serial.println("🌐 Connecting to WiFi for Enhanced AI System...");
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("AI System v6.0");
  lcd.setCursor(0, 1);
  lcd.print("Connecting WiFi");
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println("\n✅ WiFi Connected to Enhanced AI Cloud!");
    Serial.println("IP: " + WiFi.localIP().toString());
    
    lcd.setCursor(0, 1);
    lcd.print("WiFi Connected  ");
    delay(2000);
  } else {
    wifiConnected = false;
    Serial.println("\n❌ WiFi Failed - Enhanced AI System cannot operate");
    lcd.setCursor(0, 1);
    lcd.print("WiFi Failed!    ");
    delay(3000);
  }
  
  lcd.clear();
  lcd.noBacklight();
}

void initializeMQTT() {
  Serial.println("☁️ Connecting to Enhanced AWS IoT Pipeline...");
  
  wifiClient.setCACert(AWS_CERT_CA);
  wifiClient.setCertificate(AWS_CERT_CRT);
  wifiClient.setPrivateKey(AWS_CERT_PRIVATE);
  
  mqttClient.setServer(AWS_IOT_ENDPOINT, 8883);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(1024);
  
  connectMQTT();
}

void connectMQTT() {
  if (!wifiConnected) return;
  
  Serial.println("🔌 Connecting to Enhanced AWS IoT Core...");
  
  if (mqttClient.connect(CLIENT_ID)) {
    Serial.println("✅ Enhanced AWS IoT Connected!");
    mqttConnected = true;
    
    // Subscribe to enhanced topics
    mqttClient.subscribe("store/shelf/shelf-001/commands");
    mqttClient.subscribe("store/ai/behavior_updates");
    
    publishEnhancedStatus("enhanced_ai_system_online");
    
  } else {
    Serial.println("❌ Enhanced AWS IoT Failed");
    Serial.print("Error code: ");
    Serial.println(mqttClient.state());
    mqttConnected = false;
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String payloadStr = "";
  for (int i = 0; i < length; i++) {
    payloadStr += (char)payload[i];
  }
  
  Serial.println("📥 Enhanced AWS Command: " + payloadStr);
  
  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, payloadStr) == DeserializationError::Ok) {
    if (doc["command"] == "update_enhanced_product") {
      productName = doc["product_name"].as<String>();
      regularPrice = doc["price"];
      vipPrice = doc["vip_price"];
      productCategory = doc["category"].as<String>();
      productIsPremium = doc["is_premium"];
      inventoryLevel = doc["inventory_level"];
      Serial.println("🤖 Enhanced Product updated from cloud");
      
    } else if (doc["command"] == "trigger_behavior_analysis") {
      String customerId = doc["customer_id"].as<String>();
      if (!customerId.isEmpty()) {
        triggerBehaviorAnalysis(customerId);
      }
      
    } else if (doc["command"] == "force_enhanced_discount") {
      currentDiscount.discountPercentage = doc["discount"];
      currentDiscount.reason = "admin_override_enhanced";
      currentDiscount.isValid = true;
      currentDiscount.recommendationType = "admin";
      Serial.println("👨‍💼 Enhanced admin discount override applied");
      
    } else if (doc["command"] == "update_customer_cluster") {
      String customerId = doc["customer_id"].as<String>();
      String newCluster = doc["cluster_id"].as<String>();
      if (currentCustomer.customerId == customerId) {
        currentCustomer.clusterId = newCluster;
        Serial.println("🔄 Customer cluster updated: " + newCluster);
      }
    }
  }
}

void monitorConnections() {
  // Enhanced WiFi monitoring
  if (millis() - lastWiFiCheck > WIFI_CHECK_INTERVAL) {
    lastWiFiCheck = millis();
    
    if (WiFi.status() != WL_CONNECTED) {
      wifiConnected = false;
      mqttConnected = false;
      Serial.println("❌ WiFi disconnected from Enhanced AI Cloud");
      WiFi.reconnect();
    } else if (!wifiConnected) {
      wifiConnected = true;
      Serial.println("✅ WiFi reconnected to Enhanced AI Cloud");
      initializeMQTT();
    }
  }
  
  // Enhanced MQTT monitoring
  if (wifiConnected && millis() - lastMqttCheck > MQTT_CHECK_INTERVAL) {
    lastMqttCheck = millis();
    
    if (!mqttClient.connected()) {
      mqttConnected = false;
      Serial.println("🔄 Reconnecting to Enhanced AWS IoT...");
      connectMQTT();
    }
  }
}

void sendEnhancedHeartbeat() {
  if (!mqttConnected || millis() - lastHeartbeat < HEARTBEAT_INTERVAL) return;
  
  lastHeartbeat = millis();
  
  StaticJsonDocument<400> doc;
  doc["shelf_id"] = "shelf-001";
  doc["status"] = "enhanced_ai_active";
  doc["uptime"] = millis();
  doc["product"] = productName;
  doc["regular_price"] = regularPrice;
  doc["inventory_level"] = inventoryLevel;
  doc["ai_features"] = true;
  doc["enhanced_pipeline"] = true;
  doc["customer_active"] = !isIdle;
  doc["current_discount"] = currentDiscount.isValid ? currentDiscount.discountPercentage : 0;
  doc["behavior_analysis_active"] = behaviorAnalysisTriggered;
  doc["pipeline_version"] = "enhanced_v6.0";
  doc["data_sources"] = "transactions,sessions,profiles,clusters,behavior";
  
  char buffer[400];
  serializeJson(doc, buffer);
  
  if (mqttClient.publish(TOPIC_SHELF_STATUS, buffer)) {
    Serial.println("💓 Enhanced AI Heartbeat sent");
  } else {
    Serial.println("❌ Enhanced Heartbeat failed");
  }
}

void publishEnhancedStatus(const char* status) {
  if (!mqttConnected) return;
  
  StaticJsonDocument<250> doc;
  doc["shelf_id"] = "shelf-001";
  doc["status"] = status;
  doc["timestamp"] = millis();
  doc["ai_enabled"] = true;
  doc["enhanced_pipeline"] = true;
  doc["version"] = "6.0";
  
  char buffer[250];
  serializeJson(doc, buffer);
  
  if (mqttClient.publish(TOPIC_SHELF_STATUS, buffer)) {
    Serial.println("📤 Enhanced Status published: " + String(status));
  } else {
    Serial.println("❌ Enhanced Status publish failed");
  }
}

void publishEnhancedAIAnalytics(const char* eventType) {
  if (!mqttConnected) return;
  
  StaticJsonDocument<500> doc;
  doc["shelf_id"] = "shelf-001";
  doc["event_type"] = eventType;
  doc["customer_id"] = currentCustomer.customerId;
  doc["customer_type"] = currentCustomer.customerType;
  doc["cluster_id"] = currentCustomer.clusterId;
  doc["ai_discount"] = currentDiscount.discountPercentage;
  doc["discount_confidence"] = currentDiscount.confidence;
  doc["discount_type"] = currentDiscount.recommendationType;
  doc["recommendation_id"] = currentDiscount.recommendationId;
  doc["product_id"] = currentProductId;
  doc["product_category"] = productCategory;
  doc["behavior_analysis_available"] = currentCustomer.behaviorAnalysisAvailable;
  doc["total_customer_spent"] = currentCustomer.totalSpent;
  doc["customer_visits"] = currentCustomer.totalVisits;
  doc["pipeline_version"] = "enhanced_v6.0";
  doc["timestamp"] = millis();
  
  char buffer[500];
  serializeJson(doc, buffer);
  
  mqttClient.publish(TOPIC_AI_ANALYTICS, buffer);
  Serial.println("🧠 Enhanced AI Analytics published: " + String(eventType));
}

void handleEnhancedRFID() {
  if (!isIdle || !wifiConnected || !mqttConnected) return;
  
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }
  
  currentCardUID = getCardUID();
  interactionStartTime = millis();
  
  Serial.println("🏷️ Enhanced AI RFID Scan: " + currentCardUID);
  
  // Show processing message
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Processing...");
  lcd.setCursor(0, 1);
  lcd.print("Please wait");
  
  // Enhanced customer lookup with behavior analysis
  currentCustomer = checkCardWithEnhancedCloud(currentCardUID);
  
  if (!currentCustomer.customerId.isEmpty()) {
    Serial.println("✅ Customer found: " + currentCustomer.customerName);
    
    // Show customer found message
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Welcome!");
    lcd.setCursor(0, 1);
    lcd.print(currentCustomer.customerName.substring(0, 16));
    delay(2000);
    
    // Get enhanced AI discount recommendation
    currentDiscount = getEnhancedAIDiscountRecommendation(currentCustomer.customerId, currentProductId);
    
    if (currentDiscount.isValid) {
      Serial.println("✅ AI discount generated successfully");
      activateEnhancedAIProduct(currentCustomer, currentDiscount);
      publishEnhancedAIAnalytics("enhanced_ai_discount_shown");
    } else {
      Serial.println("❌ Enhanced AI discount system failed, using fallback");
      // Create a basic fallback discount
      currentDiscount.discountPercentage = currentCustomer.standardDiscount;
      currentDiscount.recommendationType = "enhanced_fallback";
      currentDiscount.confidence = 0.3;
      currentDiscount.originalPrice = regularPrice;
      currentDiscount.discountedPrice = regularPrice * (100 - currentDiscount.discountPercentage) / 100;
      currentDiscount.isValid = true;
      activateEnhancedAIProduct(currentCustomer, currentDiscount);
    }
  } else {
    Serial.println("❌ Customer not found or access denied");
    showAccessDenied(currentCardUID);
  }
  
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

String getCardUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (i > 0) uid += " ";
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

EnhancedCustomerProfile checkCardWithEnhancedCloud(String cardUID) {
  Serial.println("🌐 Checking card with Enhanced AI Cloud...");
  
  EnhancedCustomerProfile profile;
  profile.customerId = "";
  
  if (!wifiConnected) {
    Serial.println("❌ No WiFi - cannot verify card with enhanced system");
    return profile;
  }
  
  HTTPClient http;
  http.begin(API_GATEWAY_URL);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<200> requestDoc;
  requestDoc["action"] = "lookup_customer";
  requestDoc["rfid_uid"] = cardUID;
  
  String requestBody;
  serializeJson(requestDoc, requestBody);
  
  Serial.println("📤 Enhanced Customer API Request: " + requestBody);
  
  int httpResponseCode = http.POST(requestBody);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("📥 Enhanced Customer API Response: " + response);
    
    StaticJsonDocument<1024> responseDoc;
    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      
      int statusCode = responseDoc["statusCode"];
      
      if (statusCode == 200) {
        String bodyString = responseDoc["body"].as<String>();
        
        StaticJsonDocument<512> bodyDoc;
        if (deserializeJson(bodyDoc, bodyString) == DeserializationError::Ok) {
          
          bool found = bodyDoc["found"];
          bool accessGranted = bodyDoc["access_granted"];
          
          if (found && accessGranted) {
            profile.customerId = bodyDoc["customer_id"].as<String>();
            profile.customerName = bodyDoc["customer_name"].as<String>();
            profile.customerType = bodyDoc["customer_type"].as<String>();
            profile.isVip = bodyDoc["is_vip"];
            profile.aiEnhanced = bodyDoc["ai_enhanced"];
            profile.clusterId = bodyDoc["cluster_id"].as<String>();
            profile.standardDiscount = bodyDoc["discount_percentage"];
            profile.behaviorAnalysisAvailable = bodyDoc["behavior_analysis_available"];
            profile.totalSpent = bodyDoc["total_spent"];
            profile.totalVisits = bodyDoc["total_visits"];
            
            Serial.println("✅ Enhanced Customer Found: " + profile.customerName);
            Serial.println("   Type: " + profile.customerType);
            Serial.println("   AI Enhanced: " + String(profile.aiEnhanced ? "Yes" : "No"));
            Serial.println("   Cluster: " + profile.clusterId);
            Serial.println("   Total Spent: $" + String(profile.totalSpent, 2));
            Serial.println("   Behavior Analysis: " + String(profile.behaviorAnalysisAvailable ? "Available" : "Needed"));
            
          } else {
            String message = bodyDoc["message"].as<String>();
            Serial.println("❌ Enhanced Access denied: " + message);
          }
        }
      } else {
        Serial.println("❌ Enhanced API Error - Status Code: " + String(statusCode));
      }
    }
  } else {
    Serial.println("❌ Enhanced HTTP Request failed: " + String(httpResponseCode));
  }
  
  http.end();
  return profile;
}

EnhancedAIDiscountRecommendation getEnhancedAIDiscountRecommendation(String customerId, String productId) {
  Serial.println("🤖 Getting Enhanced AI Discount Recommendation...");
  
  EnhancedAIDiscountRecommendation recommendation;
  recommendation.isValid = false;
  recommendation.discountPercentage = 0;
  recommendation.confidence = 0.0;
  recommendation.reason = "system_error";
  recommendation.recommendationType = "fallback";
  recommendation.originalPrice = 0.0;
  recommendation.discountedPrice = 0.0;
  
  if (!wifiConnected) {
    Serial.println("❌ No WiFi - cannot get AI discount");
    return recommendation;
  }
  
  HTTPClient http;
  http.begin(API_GATEWAY_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(15000);  // 15 second timeout
  http.setConnectTimeout(5000);  // 5 second connect timeout
  
  StaticJsonDocument<300> requestDoc;
  requestDoc["action"] = "get_ai_discount";
  requestDoc["customer_id"] = customerId;
  requestDoc["product_id"] = productId;
  
  String requestBody;
  serializeJson(requestDoc, requestBody);
  
  Serial.println("📤 Enhanced AI Discount API Request: " + requestBody);
  
  int httpResponseCode = http.POST(requestBody);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("📥 Enhanced AI Discount API Response: " + response);
    
    StaticJsonDocument<1024> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (error) {
      Serial.println("❌ JSON parsing failed: " + String(error.c_str()));
      http.end();
      return recommendation;
    }
    
    int statusCode = responseDoc["statusCode"];
    
    if (statusCode == 200) {
      String bodyString = responseDoc["body"].as<String>();
      
      StaticJsonDocument<1024> bodyDoc;
      DeserializationError bodyError = deserializeJson(bodyDoc, bodyString);
      
      if (bodyError) {
        Serial.println("❌ Body JSON parsing failed: " + String(bodyError.c_str()));
        http.end();
        return recommendation;
      }
      
      bool success = bodyDoc["success"];
      
      if (success) {
        auto discountRec = bodyDoc["discount_recommendation"];
        
        recommendation.recommendationId = discountRec["recommendation_id"].as<String>();
        recommendation.discountPercentage = discountRec["discount_percentage"];
        recommendation.confidence = discountRec["confidence"];
        recommendation.reason = discountRec["reason"].as<String>();
        recommendation.recommendationType = discountRec["recommendation_type"].as<String>();
        recommendation.expiresInMinutes = discountRec["expires_in_minutes"];
        recommendation.generatedAt = discountRec["generated_at"].as<String>();
        recommendation.pipelineVersion = bodyDoc["pipeline_version"].as<String>();
        
        // Handle prices safely
        recommendation.originalPrice = discountRec["original_price"] | 4.0;  // Default to 4.0 if missing
        recommendation.discountedPrice = discountRec["discounted_price"] | 3.6;  // Default to 3.6 if missing
        
        recommendation.isValid = true;
        
        Serial.println("🎯 Enhanced AI Discount Generated:");
        Serial.printf("   Discount: %d%% (Confidence: %.2f)\n", 
                     recommendation.discountPercentage, recommendation.confidence);
        Serial.println("   Type: " + recommendation.recommendationType);
        Serial.println("   Reason: " + recommendation.reason);
        Serial.printf("   Price: $%.2f -> $%.2f\n", 
                     recommendation.originalPrice, recommendation.discountedPrice);
        Serial.println("   Pipeline: " + recommendation.pipelineVersion);
        
      } else {
        Serial.println("❌ Enhanced AI discount generation failed");
        // Check for fallback discount in response
        if (bodyDoc.containsKey("fallback_discount")) {
          auto fallback = bodyDoc["fallback_discount"];
          recommendation.discountPercentage = fallback["discount_percentage"] | 10;
          recommendation.confidence = fallback["confidence"] | 0.3;
          recommendation.reason = fallback["reason"].as<String>();
          recommendation.originalPrice = fallback["original_price"] | 4.0;
          recommendation.discountedPrice = fallback["discounted_price"] | 3.6;
          recommendation.recommendationType = "fallback";
          recommendation.isValid = true;
          Serial.println("Using fallback discount: " + String(recommendation.discountPercentage) + "%");
        }
      }
    } else {
      Serial.println("❌ API Error - Status Code: " + String(statusCode));
    }
  } else {
    Serial.println("❌ Enhanced AI Discount HTTP Request failed: " + String(httpResponseCode));
  }
  
  http.end();
  return recommendation;
}

void triggerBehaviorAnalysis(String customerId) {
  Serial.println("📊 Triggering Enhanced Behavior Analysis...");
  
  if (!wifiConnected || customerId.isEmpty()) return;
  
  showBehaviorAnalysisStatus();
  
  HTTPClient http;
  http.begin(API_GATEWAY_URL);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<200> requestDoc;
  requestDoc["action"] = "analyze_customer_behavior";
  requestDoc["customer_id"] = customerId;
  
  String requestBody;
  serializeJson(requestDoc, requestBody);
  
  Serial.println("📤 Behavior Analysis Request: " + requestBody);
  
  int httpResponseCode = http.POST(requestBody);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("📥 Behavior Analysis Response: " + response);
    
    StaticJsonDocument<1024> responseDoc;
    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      
      int statusCode = responseDoc["statusCode"];
      
      if (statusCode == 200) {
        String bodyString = responseDoc["body"].as<String>();
        
        StaticJsonDocument<512> bodyDoc;
        if (deserializeJson(bodyDoc, bodyString) == DeserializationError::Ok) {
          
          bool success = bodyDoc["success"];
          
          if (success) {
            behaviorAnalysisTriggered = true;
            lastBehaviorAnalysis = millis();
            currentCustomer.behaviorAnalysisAvailable = true;
            
            Serial.println("✅ Behavior analysis completed successfully");
            Serial.println("📊 Updated tables: customer_profiles, purchase_behavior, customers_production");
            
            // Publish behavior update to MQTT
            publishEnhancedAIAnalytics("behavior_analysis_completed");
            
          } else {
            Serial.println("❌ Behavior analysis failed - insufficient data");
          }
        }
      }
    }
  } else {
    Serial.println("❌ Behavior Analysis HTTP Request failed: " + String(httpResponseCode));
  }
  
  http.end();
}

void logEnhancedInteractionToCloud(String action, bool includePurchaseData) {
  Serial.println("📊 Logging enhanced interaction to AI system...");
  
  if (!wifiConnected) {
    Serial.println("❌ No WiFi - cannot log interaction");
    return;
  }
  
  HTTPClient http;
  http.begin(API_GATEWAY_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);  // 10 second timeout
  
  StaticJsonDocument<400> requestDoc;
  requestDoc["action"] = "log_interaction";
  requestDoc["customer_id"] = currentCustomer.customerId;
  requestDoc["product_id"] = currentProductId;
  requestDoc["recommendation_id"] = currentDiscount.recommendationId;
  requestDoc["discount_shown"] = currentDiscount.discountPercentage;
  requestDoc["action_taken"] = action;
  
  // Include purchase details if it's a purchase
  if (includePurchaseData && action == "purchased") {
    StaticJsonDocument<200> purchaseDetails;
    purchaseDetails["total_amount"] = currentDiscount.discountedPrice;
    purchaseDetails["quantity"] = 1;
    purchaseDetails["original_price"] = currentDiscount.originalPrice;
    purchaseDetails["discount_applied"] = currentDiscount.discountPercentage;
    
    requestDoc["purchase_details"] = purchaseDetails;
  }
  
  String requestBody;
  serializeJson(requestDoc, requestBody);
  
  Serial.println("📤 Enhanced Interaction Log: " + requestBody);
  
  int httpResponseCode = http.POST(requestBody);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("📥 Enhanced Interaction Response: " + response);
    
    StaticJsonDocument<512> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (error) {
      Serial.println("❌ Interaction response JSON parsing failed");
      http.end();
      return;
    }
    
    int statusCode = responseDoc["statusCode"];
    
    if (statusCode == 200) {
      String bodyString = responseDoc["body"].as<String>();
      
      StaticJsonDocument<256> bodyDoc;
      DeserializationError bodyError = deserializeJson(bodyDoc, bodyString);
      
      if (bodyError) {
        Serial.println("❌ Interaction body JSON parsing failed");
        http.end();
        return;
      }
      
      bool success = bodyDoc["success"];
      if (success) {
        Serial.println("✅ Enhanced interaction logged successfully");
      } else {
        Serial.println("⚠️ Interaction logging reported failure but continued");
      }
    } else {
      Serial.println("❌ Interaction logging failed with status: " + String(statusCode));
    }
  } else {
    Serial.println("❌ Failed to log enhanced interaction: " + String(httpResponseCode));
  }
  
  http.end();
}

void showAccessDenied(String cardUID) {
  publishEnhancedAIAnalytics("enhanced_access_denied");
  
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Access Denied");
  lcd.setCursor(0, 1);
  lcd.print("Enhanced AI: ???");
  delay(3000);
  lcd.clear();
  lcd.noBacklight();
}

void loadEnhancedProductFromCloud() {
  Serial.println("🌐 Loading product from Enhanced AWS API...");
  
  if (!wifiConnected) {
    Serial.println("❌ No WiFi - using default product for enhanced system");
    productName = "Premium Apple";
    regularPrice = 4.00;
    vipPrice = 2.00;
    productCategory = "Fresh_Fruits";
    productIsPremium = true;
    inventoryLevel = 50;
    return;
  }
  
  HTTPClient http;
  http.begin(API_GATEWAY_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);  // 10 second timeout
  
  StaticJsonDocument<200> requestDoc;
  requestDoc["action"] = "lookup_product";
  requestDoc["product_id"] = currentProductId;
  
  String requestBody;
  serializeJson(requestDoc, requestBody);
  
  Serial.println("📤 Enhanced Product API Request: " + requestBody);
  
  int httpResponseCode = http.POST(requestBody);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("📥 Enhanced Product API Response: " + response);
    
    StaticJsonDocument<1024> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (error) {
      Serial.println("❌ Product JSON parsing failed: " + String(error.c_str()));
      http.end();
      return;
    }
    
    int statusCode = responseDoc["statusCode"];
    
    if (statusCode == 200) {
      String bodyString = responseDoc["body"].as<String>();
      
      StaticJsonDocument<512> bodyDoc;
      DeserializationError bodyError = deserializeJson(bodyDoc, bodyString);
      
      if (bodyError) {
        Serial.println("❌ Product body JSON parsing failed");
        http.end();
        return;
      }
      
      bool found = bodyDoc["found"];
      
      if (found) {
        productName = bodyDoc["product_name"].as<String>();
        regularPrice = bodyDoc["regular_price"] | 4.0;  // Safe default
        vipPrice = bodyDoc["vip_price"] | 2.0;  // Safe default
        productCategory = bodyDoc["category"].as<String>();
        productIsPremium = bodyDoc["is_premium"] | false;
        inventoryLevel = bodyDoc["inventory_level"] | 50;
        
        Serial.println("📦 Enhanced Product loaded from cloud:");
        Serial.println("  Name: " + productName);
        Serial.printf("  Regular: $%.2f\n", regularPrice);
        Serial.printf("  VIP: $%.2f\n", vipPrice);
        Serial.println("  Category: " + productCategory);
        Serial.println("  Premium: " + String(productIsPremium ? "Yes" : "No"));
        Serial.println("  Inventory: " + String(inventoryLevel));
        
      } else {
        Serial.println("❌ Enhanced Product not found in cloud database");
        productName = "Product Not Found";
        regularPrice = 4.00;
        vipPrice = 2.00;
      }
    }
  } else {
    Serial.println("❌ Enhanced Product HTTP Request failed: " + String(httpResponseCode));
    productName = "Connection Error";
    regularPrice = 4.00;
    vipPrice = 2.00;
  }
  
  http.end();
}

void activateEnhancedAIProduct(EnhancedCustomerProfile customer, EnhancedAIDiscountRecommendation discount) {
  isIdle = false;
  isDisplaying = true;
  displayStartTime = millis();
  
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  
  // Show enhanced personalized greeting
  if (customer.aiEnhanced) {
    lcd.print("AI++: " + customer.customerName.substring(0, 10));
  } else {
    lcd.print(customer.isVip ? "VIP Customer!" : "Welcome!");
  }
  
  lcd.setCursor(0, 1);
  String discountInfo = discount.recommendationType.substring(0, 8) + " " + String(discount.discountPercentage) + "%";
  lcd.print(discountInfo);
  delay(3000);
  
  // Show behavior analysis status if available
  if (customer.behaviorAnalysisAvailable) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("AI: Analyzed");
    lcd.setCursor(0, 1);
    lcd.print("Visits:" + String(customer.totalVisits) + " $" + String(customer.totalSpent, 0));
    delay(2500);
  }
  
  Serial.println("🔄 Moving Enhanced AI shelf...");
  for (int pos = 0; pos <= 180; pos += 3) {
    shelfServo.write(pos);
    delay(25);
  }
  
  displayEnhancedAIProduct();
  
  // Log the enhanced discount as shown
  logEnhancedInteractionToCloud("shown");
  
  Serial.printf("⏰ Enhanced AI Product active for %d seconds\n", DISPLAY_DURATION/1000);
}

void displayEnhancedAIProduct() {
  lcd.clear();
  lcd.setCursor(0, 0);
  
  // Show product name with enhanced info
  String displayName = productName;
  if (displayName.length() > 14) {
    displayName = displayName.substring(0, 11) + "...";
  }
  if (productIsPremium) {
    displayName = "★" + displayName;
  }
  lcd.print(displayName);
  
  lcd.setCursor(0, 1);
  
  // Display price information properly
  if (currentDiscount.discountPercentage > 0 && currentDiscount.discountedPrice > 0) {
    // Show discount percentage and discounted price
    String priceDisplay = String(currentDiscount.discountPercentage) + "% $" + String(currentDiscount.discountedPrice, 2);
    lcd.print(priceDisplay);
  } else {
    // Show regular price
    String priceDisplay = "Price: $" + String(regularPrice, 2);
    lcd.print(priceDisplay);
  }
  
  // Enhanced AI indicators
  lcd.setCursor(15, 0);
  if (currentCustomer.aiEnhanced) {
    lcd.print("A");  // AI enhanced
  } else {
    lcd.print("R");  // Regular
  }
  
  lcd.setCursor(15, 1);
  if (currentDiscount.confidence > 0.8) {
    lcd.print("!");  // High confidence
  } else if (currentDiscount.confidence > 0.5) {
    lcd.print(".");  // Medium confidence
  } else {
    lcd.print("?");  // Low confidence
  }
}

void detectPurchaseInteraction() {
  // Simple purchase detection based on display time and user interaction
  // In a real system, this would integrate with payment systems or weight sensors
  
  if (isDisplaying && !purchaseDetected) {
    unsigned long displayTime = millis() - displayStartTime;
    
    // If customer stays engaged for more than 10 seconds, consider it interest
    if (displayTime > 10000 && displayTime < 15000) {
      // Check for any additional interaction (this could be button press, weight change, etc.)
      // For now, we'll use a simple time-based heuristic
      
      if (currentDiscount.confidence > 0.7 && currentCustomer.aiEnhanced) {
        // High confidence AI recommendation with enhanced customer - likely purchase
        purchaseDetected = true;
        purchaseDetectionTime = millis();
        
        Serial.println("🛒 Purchase detected based on AI confidence and engagement time");
        
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Purchase Detect.");
        lcd.setCursor(0, 1);
        lcd.print("Thank you!");
        delay(2000);
        
        // Log purchase interaction
        logEnhancedInteractionToCloud("purchased", true);
        publishEnhancedAIAnalytics("enhanced_purchase_detected");
      }
    }
  }
}

void returnToEnhancedIdle() {
  Serial.println("⏰ Returning to enhanced idle...");
  
  publishEnhancedAIAnalytics("enhanced_interaction_complete");
  
  // Determine interaction type based on various factors
  String interactionType = "ignored";
  if (purchaseDetected) {
    interactionType = "purchased";
  } else if (millis() - displayStartTime >= DISPLAY_DURATION - 2000) {
    // Customer stayed for most of the time
    interactionType = "engaged";
  }
  
  // Log final interaction if not already logged
  if (!purchaseDetected) {
    logEnhancedInteractionToCloud(interactionType);
  }
  
  lcd.clear();
  lcd.setCursor(0, 0);
  if (purchaseDetected) {
    lcd.print("Thank you!");
    lcd.setCursor(0, 1);
    if (currentDiscount.confidence > 0.8) {
      lcd.print("AI: Perfect!");
    } else {
      lcd.print("AI: Learning++");
    }
  } else {
    lcd.print("Come back soon!");
    lcd.setCursor(0, 1);
    lcd.print("AI: Improving..");
  }
  
  delay(3000);
  
  // Return servo to home position
  for (int pos = 180; pos >= 0; pos -= 3) {
    shelfServo.write(pos);
    delay(25);
  }
  
  lcd.clear();
  lcd.noBacklight();
  
  // Reset enhanced states
  isIdle = true;
  isDisplaying = false;
  purchaseDetected = false;
  currentCardUID = "";
  
  // Reset enhanced AI data
  currentCustomer.customerId = "";
  currentDiscount.isValid = false;
  behaviorAnalysisTriggered = false;
  
  Serial.println("💤 Enhanced AI System ready for next interaction");
}

void showEnhancedConnectionStatus() {
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Enhanced AI v6.0");
  lcd.setCursor(0, 1);
  
  if (mqttConnected) {
    lcd.print("AI: Connected++");
  } else if (wifiConnected) {
    lcd.print("WiFi: Connected");
  } else {
    lcd.print("Status: Offline");
  }
  
  delay(2000);
  
  if (!isDisplaying) {
    lcd.clear();
    lcd.noBacklight();
  }
}

void showEnhancedAISystemStatus() {
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Enhanced AI v6.0");
  lcd.setCursor(0, 1);
  lcd.print("ML Pipeline++");
  delay(3000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Features:");
  lcd.setCursor(0, 1);
  lcd.print("Smart Behavior");
  delay(2000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Data Sources:");
  lcd.setCursor(0, 1);
  lcd.print("All Tables++");
  delay(2000);
  
  lcd.clear();
  lcd.noBacklight();
}

void showBehaviorAnalysisStatus() {
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("AI: Analyzing...");
  lcd.setCursor(0, 1);
  lcd.print("Customer Data");
  delay(2000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Processing:");
  lcd.setCursor(0, 1);
  lcd.print("Transactions++");
  delay(1500);
  
  lcd.clear();
  lcd.noBacklight();
}