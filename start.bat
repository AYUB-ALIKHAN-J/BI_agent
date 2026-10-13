@echo off
:: Start Olist BI Dashboard
:: This script starts the Streamlit dashboard

echo Starting Olist BI Dashboard...
echo.

:: Check if virtual environment exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Check if warehouse exists
if not exist "warehouse\olist.duckdb" (
    echo WARNING: Warehouse not found. Run 'make synth' and 'make etl' first.
    echo.
)

:: Start the dashboard
echo Starting Streamlit dashboard...
echo Open http://localhost:8501 in your browser
echo.
set PYTHONWARNINGS=ignore::DeprecationWarning
streamlit run src/olist_bi/app/streamlit_app.py
