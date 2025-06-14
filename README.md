Based on your project details, here's a comprehensive README.md for your GitHub repository:


# IoT-Powered Automated Convenience Store
![IoT-Store-AWS-Architecture drawio (1)](https://github.com/user-attachments/assets/4562f781-735c-43ab-8b30-cd4c168f78f5)


A fully automated retail solution using IoT devices, cloud computing, and AI to enable unmanned shopping experiences.

## Key Features
- **Smart Cart System**: RFID-based item scanning with fraud detection
- **Door Access Control**: Secure entry/exit with session validation
- **AI-Powered Smart Shelves**: Dynamic discounts based on customer behavior
- **Cloud Infrastructure**: AWS serverless architecture with Terraform deployment
- **Session-Centric Analytics**: Complete customer journey tracking

## System Components
### Hardware Nodes
1. **Door Access System** (`door_access_smart_store`)
   - RFID authentication
   - Infrared security sensors
   - Servo-controlled locking mechanism

2. **Smart Cart** (`rfid_project`)
   - Product scanning with MFRC522 RFID
   - Ultrasonic fraud detection
   - Real-time bill calculation

3. **Smart Shelf** (`Smart_Shell_discount/sketch_jun5a`)
   - Customer recognition
   - AI-powered discount displays
   - Servo-activated product presentation

### Cloud Infrastructure (`terraform`)
- **AWS Services**:
  - DynamoDB (17 session-centric tables)
  - Lambda functions (session processing)
  - IoT Core (MQTT communication)
  - EC2 (Admin dashboard)
- **Terraform Deployment**:
  ```bash
  terraform init
  terraform apply
  ```

## Repository Structure
```
├── Smart_Shell_discount/        # Smart shelf node code
│   └── sketch_jun5a             # ESP32 implementation
├── door_access_smart_store/     # Door system code
├── rfid_project/                # Smart cart implementation
├── terraform/                   # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── web_interface/               # Flask admin dashboard
├── database_schemas/            # Database designs
│   ├── clouddb.json             # DynamoDB schema
│   ├── cart.sql                 # Smart cart schema
│   └── door.sql                 # Door system schema
├── .env.example                 # Environment template
├── .gitignore
└── README.md
```

## Setup Instructions
1. **Hardware Setup**:
   - Follow wiring diagrams in `/documentation`
   - Flash Arduino/Raspberry Pi with provided sketches

2. **Cloud Deployment**:
   ```bash
   cd terraform
   terraform init
   terraform apply -var="aws_region=your-region"
   ```

3. **Environment Configuration**:
   - Create `.env` file from `.env.example`
   - Add AWS credentials and MQTT endpoints

4. **Run Edge Devices**:
   ```bash
   # Smart Cart
   python rfid_project/app.py
  
   # Door System
   python door_access_smart_store/door_app.py
   ```

## Usage Flow
1. Customer scans RFID tag at entrance
2. System assigns smart cart
3. Items automatically scan when placed in cart
4. AI shelf displays personalized discounts
5. Automated checkout via web interface
6. Exit validation with payment confirmation

## Documentation
- [Presentation Video](https://youtu.be/E5queSSUAzU)

## Contributors
- Shifaz Ahamed Rifan Deen (Smart Cart & Cloud Infrastructure)
- Munich Awad Elsheikhidris Abdelrahman (Database & AI Analytics)
- Brian Christopher Johan (Door System & Security)

## Important Notes
⚠️ **Cloud Configuration**: Actual AWS setup may differ from Terraform files due to live modifications  
⚠️ **Database Schemas**: SQL files represent initial designs - final DynamoDB structure differs  
⚠️ **Hardware**: Calibration required for sensors (reference docs for IR/ultrasonic tuning)

> "This system represents a paradigm shift in retail technology, combining IoT edge devices with cloud intelligence to create truly autonomous shopping experiences." - Team Reflection
