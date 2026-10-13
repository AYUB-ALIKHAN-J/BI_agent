#!/usr/bin/env bash
# Start Olist BI Dashboard
# This script starts the Streamlit dashboard

set -e

echo "Starting Olist BI Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # macOS/Linux
    source .venv/bin/activate
fi

# Check if warehouse exists
if [ ! -f "warehouse/olist.duckdb" ]; then
    echo "⚠️  Warehouse not found. Run 'make synth' and 'make etl' first."
    echo ""
fi

# Start the dashboard
echo "Starting Streamlit dashboard..."
echo "Open http://localhost:8501 in your browser"
echo ""
export PYTHONWARNINGS="ignore::DeprecationWarning"
streamlit run src/olist_bi/app/streamlit_app.py
