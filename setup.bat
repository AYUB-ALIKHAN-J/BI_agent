@echo off
:: Olist BI Setup Script - Windows
:: This script sets up the project environment and starts the application

echo ==========================================
echo   Olist BI - Agentic BI Platform Setup
echo ==========================================
echo.

:: Check Python version
echo Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

:: Check Python version (must be >= 3.10)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

echo Python version: %PYTHON_VERSION%

if %PYTHON_MAJOR% lss 3 (
    echo ERROR: Python 3.10 or higher is required
    pause
    exit /b 1
)

if %PYTHON_MAJOR% equ 3 if %PYTHON_MINOR% lss 10 (
    echo ERROR: Python 3.10 or higher is required
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Checking dependencies...
python -c "import olist_bi" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    python -m pip install --upgrade pip
    pip install -e ".[app,dev]"
    echo Dependencies installed
) else (
    echo Dependencies already installed
)

echo.
echo Checking warehouse...
if not exist "warehouse\olist.duckdb" (
    echo Warehouse not found. Generating synthetic data...
    echo This may take a few minutes...
    echo.
    
    python -m olist_bi.cli synth
    python -m olist_bi.cli etl
    
    echo.
    echo Warehouse built successfully
) else (
    echo Warehouse already exists
)

echo.
echo Running tests...
pytest -q
if %errorlevel% neq 0 (
    echo WARNING: Some tests failed
)

echo.
echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo To start the dashboard, run:
echo   make app
echo.
echo Or manually:
echo   streamlit run src/olist_bi/app/streamlit_app.py
echo.
echo The dashboard will be available at: http://localhost:8501
echo.
echo Quick commands:
echo   make synth   - Generate synthetic data
echo   make etl     - Build warehouse
echo   make kpis    - Show headline KPIs
echo   make app     - Start dashboard
echo   make test    - Run tests
echo.
pause
