@echo off
REM ============================================================================
REM DEPLOY.BAT - Windows Deployment Script for IoT Store Infrastructure
REM ============================================================================
REM This script loads environment variables from .env file and deploys Terraform
REM Run this script instead of terraform commands directly
REM ============================================================================

echo [INFO] Starting IoT Store Infrastructure Deployment...
echo.

REM Check if terraform is installed
terraform version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Terraform is not installed or not in PATH
    echo [INFO] Please install Terraform first: https://www.terraform.io/downloads
    echo [INFO] Or run: choco install terraform
    pause
    exit /b 1
)

REM Check if .env file exists in parent directory
if not exist "..\.env" (
    echo [ERROR] .env file not found in parent directory
    echo [INFO] Please create .env file with your AWS credentials
    echo [INFO] Required variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, ACCOUNT_ID
    pause
    exit /b 1
)

REM Load environment variables from .env file
echo [INFO] Loading environment variables from .env file...

for /f "usebackq tokens=1,2 delims==" %%a in ("..\.env") do (
    REM Skip empty lines and comments
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

REM Set Terraform variables from environment
set TF_VAR_aws_access_key_id=%AWS_ACCESS_KEY_ID%
set TF_VAR_aws_secret_access_key=%AWS_SECRET_ACCESS_KEY%
set TF_VAR_aws_region=%AWS_REGION%
set TF_VAR_aws_account_id=%ACCOUNT_ID%

REM Validate required variables
if "%AWS_ACCESS_KEY_ID%"=="" (
    echo [ERROR] AWS_ACCESS_KEY_ID not found in .env file
    pause
    exit /b 1
)

if "%AWS_SECRET_ACCESS_KEY%"=="" (
    echo [ERROR] AWS_SECRET_ACCESS_KEY not found in .env file
    pause
    exit /b 1
)

if "%AWS_REGION%"=="" (
    echo [ERROR] AWS_REGION not found in .env file
    pause
    exit /b 1
)

if "%ACCOUNT_ID%"=="" (
    echo [ERROR] ACCOUNT_ID not found in .env file
    echo [INFO] You can get your Account ID from AWS Console or using AWS CLI
    pause
    exit /b 1
)

echo [INFO] Environment variables loaded successfully
echo [INFO] AWS Region: %AWS_REGION%
echo [INFO] Account ID: %ACCOUNT_ID%
echo [INFO] Project: iot-convenience-store
echo.

REM Check if all required files exist
echo [INFO] Checking required files...
if not exist "main.tf" (
    echo [ERROR] main.tf not found in current directory
    pause
    exit /b 1
)

if not exist "terraform.tfvars" (
    echo [ERROR] terraform.tfvars not found in current directory
    echo [INFO] Please create terraform.tfvars file
    pause
    exit /b 1
)

if not exist "lambda_session_processor.py" (
    echo [ERROR] lambda_session_processor.py not found in current directory
    pause
    exit /b 1
)

if not exist "admin_ui_setup.sh" (
    echo [ERROR] admin_ui_setup.sh not found in current directory
    pause
    exit /b 1
)

echo [INFO] All required files found
echo.

REM Initialize Terraform if needed
if not exist ".terraform" (
    echo [INFO] Initializing Terraform...
    terraform init
    if %errorlevel% neq 0 (
        echo [ERROR] Terraform initialization failed
        pause
        exit /b 1
    )
    echo [INFO] Terraform initialized successfully
    echo.
)

REM Validate Terraform configuration
echo [INFO] Validating Terraform configuration...
terraform validate
if %errorlevel% neq 0 (
    echo [ERROR] Terraform configuration validation failed
    pause
    exit /b 1
)

echo [INFO] Terraform configuration is valid
echo.

REM Run terraform plan
echo [INFO] Creating deployment plan...
terraform plan -out=tfplan
if %errorlevel% neq 0 (
    echo [ERROR] Terraform plan failed
    pause
    exit /b 1
)

echo.
echo [INFO] Deployment plan created successfully
echo [INFO] The following resources will be created:
echo   - 9 DynamoDB tables (customers, products, sessions, etc.)
echo   - 1 EC2 instance for Admin UI (t3.micro)
echo   - 3 IoT Core things (smart cart, door, shelf)
echo   - IAM roles and policies for secure access
echo   - Lambda function for session processing
echo   - Security groups and networking
echo   - IoT certificates and MQTT policies
echo.

REM Ask for confirmation
set /p confirm="Do you want to proceed with deployment? (y/N): "
if /i not "%confirm%"=="y" (
    echo [INFO] Deployment cancelled by user
    pause
    exit /b 0
)

REM Apply terraform
echo.
echo [INFO] Deploying infrastructure... (this may take 5-10 minutes)
echo [INFO] Please wait while AWS resources are being created...
terraform apply tfplan
if %errorlevel% neq 0 (
    echo [ERROR] Terraform deployment failed
    echo [INFO] Check the error messages above for details
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Infrastructure deployed successfully!
echo.

REM Wait a moment for outputs to be available
echo [INFO] Getting deployment information...
timeout /t 3 /nobreak >nul

REM Get outputs
echo.
echo ============================================================================
echo                    DEPLOYMENT SUCCESSFUL - ACCESS INFORMATION
echo ============================================================================
echo.

REM Admin UI URL
echo [INFO] Admin UI URL: 
for /f "delims=" %%i in ('terraform output -raw admin_ui_url 2^>nul') do set admin_url=%%i
if not "%admin_url%"=="" (
    echo %admin_url%
) else (
    echo [WARNING] Could not retrieve Admin UI URL. Check terraform outputs manually.
)

echo.

REM Admin UI IP
echo [INFO] Admin UI IP Address: 
for /f "delims=" %%i in ('terraform output -raw admin_ui_ip 2^>nul') do set admin_ip=%%i
if not "%admin_ip%"=="" (
    echo %admin_ip%
) else (
    echo [WARNING] Could not retrieve Admin UI IP. Check terraform outputs manually.
)

echo.

REM DynamoDB Tables
echo [INFO] Created DynamoDB Tables:
terraform output dynamodb_tables 2>nul

echo.

REM IoT Information
echo [INFO] IoT Core Setup:
terraform output iot_endpoints 2>nul

echo.
echo ============================================================================
echo                              NEXT STEPS
echo ============================================================================
echo.
echo [1] Admin UI Access:
echo     - URL: %admin_url%
echo     - Wait 2-3 minutes for complete startup
echo     - Login and test all features
echo.
echo [2] Verify Services:
echo     - Check EC2 instance is running in AWS Console
echo     - Verify DynamoDB tables are created
echo     - Test IoT Core MQTT topics
echo.
echo [3] Development:
echo     - Your edge devices can now connect to IoT Core
echo     - Use the DynamoDB tables for data storage
echo     - Admin UI is ready for monitoring
echo.
echo [4] Cleanup (when needed):
echo     - Run: terraform destroy
echo     - This will remove ALL AWS resources
echo.
echo ============================================================================

REM Final success message
echo.
echo [SUCCESS] Your IoT Convenience Store System is now live!
echo [INFO] Check the Admin UI URL above to access your dashboard
echo.

pause