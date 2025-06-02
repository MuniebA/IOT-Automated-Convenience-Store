@echo off
echo [DEBUG] Starting IoT Store Infrastructure Deployment...
echo.

echo [DEBUG] Checking terraform installation...
terraform version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Terraform is not installed or not in PATH
    pause
    exit /b 1
)
echo [OK] Terraform is installed

echo [DEBUG] Checking .env file...
if not exist "..\.env" (
    echo [ERROR] .env file not found in parent directory
    pause
    exit /b 1
)
echo [OK] .env file found

echo [DEBUG] Loading environment variables...
for /f "usebackq tokens=1,2 delims==" %%a in ("..\.env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

set TF_VAR_aws_access_key_id=%AWS_ACCESS_KEY_ID%
set TF_VAR_aws_secret_access_key=%AWS_SECRET_ACCESS_KEY%
set TF_VAR_aws_region=%AWS_REGION%
set TF_VAR_aws_account_id=%ACCOUNT_ID%

echo [OK] Environment variables loaded:
echo   AWS_REGION: %AWS_REGION%
echo   ACCOUNT_ID: %ACCOUNT_ID%

echo [DEBUG] Validating required environment variables...
if "%AWS_ACCESS_KEY_ID%"=="" (
    echo [ERROR] AWS_ACCESS_KEY_ID not found in .env file
    pause
    exit /b 1
)
echo [OK] AWS_ACCESS_KEY_ID is set

if "%AWS_SECRET_ACCESS_KEY%"=="" (
    echo [ERROR] AWS_SECRET_ACCESS_KEY not found in .env file
    pause
    exit /b 1
)
echo [OK] AWS_SECRET_ACCESS_KEY is set

if "%AWS_REGION%"=="" (
    echo [ERROR] AWS_REGION not found in .env file
    pause
    exit /b 1
)
echo [OK] AWS_REGION is set

if "%ACCOUNT_ID%"=="" (
    echo [ERROR] ACCOUNT_ID not found in .env file
    pause
    exit /b 1
)
echo [OK] ACCOUNT_ID is set

echo [DEBUG] Checking required files...

echo [DEBUG] Checking main.tf...
if not exist "main.tf" (
    echo [ERROR] main.tf not found in current directory
    pause
    exit /b 1
)
echo [OK] main.tf exists

echo [DEBUG] Checking terraform.tfvars...
if not exist "terraform.tfvars" (
    echo [ERROR] terraform.tfvars not found in current directory
    pause
    exit /b 1
)
echo [OK] terraform.tfvars exists

echo [DEBUG] Checking lambda_session_processor.py...
if not exist "lambda_session_processor.py" (
    echo [ERROR] lambda_session_processor.py not found in current directory
    pause
    exit /b 1
)
echo [OK] lambda_session_processor.py exists

echo [DEBUG] Checking admin_ui_docker_setup.sh...
if not exist "admin_ui_docker_setup.sh" (
    echo [ERROR] admin_ui_docker_setup.sh not found in current directory
    pause
    exit /b 1
)
echo [OK] admin_ui_docker_setup.sh exists

echo [SUCCESS] All required files found!
echo.

echo [DEBUG] Initializing Terraform if needed...
if not exist ".terraform" (
    echo [INFO] Running terraform init...
    terraform init
    if %errorlevel% neq 0 (
        echo [ERROR] Terraform initialization failed
        pause
        exit /b 1
    )
    echo [OK] Terraform initialized successfully
) else (
    echo [OK] Terraform already initialized
)

echo [DEBUG] Validating Terraform configuration...
terraform validate
if %errorlevel% neq 0 (
    echo [ERROR] Terraform configuration validation failed
    pause
    exit /b 1
)
echo [OK] Terraform configuration is valid

echo [DEBUG] Creating deployment plan...
terraform plan -out=tfplan
if %errorlevel% neq 0 (
    echo [ERROR] Terraform plan failed
    pause
    exit /b 1
)

echo [SUCCESS] Deployment plan created successfully!
echo.
echo [INFO] Ready to deploy infrastructure
echo.

set /p confirm="Do you want to proceed with deployment? (y/N): "
if /i not "%confirm%"=="y" (
    echo [INFO] Deployment cancelled by user
    pause
    exit /b 0
)

echo [INFO] Deploying infrastructure...
terraform apply tfplan
if %errorlevel% neq 0 (
    echo [ERROR] Terraform deployment failed
    pause
    exit /b 1
)

echo [SUCCESS] Infrastructure deployed successfully!
echo.

echo [INFO] Getting deployment outputs...
terraform output admin_ui_url
terraform output admin_ui_ip
terraform output dynamodb_tables

echo.
echo [SUCCESS] Deployment complete! Check the URLs above.
pause