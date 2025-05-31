@echo off
echo [DEBUG] Checking all required files...
echo.

echo [CHECK] main.tf:
if exist "main.tf" (
    echo   ✓ Found
) else (
    echo   ✗ Missing
)

echo [CHECK] terraform.tfvars:
if exist "terraform.tfvars" (
    echo   ✓ Found
) else (
    echo   ✗ Missing
)

echo [CHECK] lambda_session_processor.py:
if exist "lambda_session_processor.py" (
    echo   ✓ Found
) else (
    echo   ✗ Missing
)

echo [CHECK] admin_ui_bootstrap.sh:
if exist "admin_ui_bootstrap.sh" (
    echo   ✓ Found
) else (
    echo   ✗ Missing
)

echo [CHECK] admin_ui_setup_full.sh:
if exist "admin_ui_setup_full.sh" (
    echo   ✓ Found
) else (
    echo   ✗ Missing
)

echo [CHECK] .env in parent directory:
if exist "..\.env" (
    echo   ✓ Found
) else (
    echo   ✗ Missing
)

echo.
echo [DEBUG] File check complete!
pause