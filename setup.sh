#!/usr/bin/env bash
# Olist BI Setup Script - Cross-platform (Windows, macOS, Linux)
# This script sets up the project environment and starts the application

set -e  # Exit on any error

echo "=========================================="
echo "  Olist BI - Agentic BI Platform Setup"
echo "=========================================="
echo ""

# Detect OS
OS=$(uname -s)
echo "Detected OS: $OS"
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "Python: $PYTHON_VERSION"

# Check if Python version is >= 3.10
PYTHON_VERSION_NUM=$(echo $PYTHON_VERSION | grep -oP '\d+\.\d+' | head -1)
PYTHON_MAJOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "❌ Python 3.10 or higher is required"
    exit 1
fi
echo "✅ Python version check passed"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."

if [[ "$OS" == "Windows" ]] || [[ "$OS" == "MINGW"* ]] || [[ "$OS" == "CYGWIN"* ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # macOS/Linux
    source .venv/bin/activate
fi

echo "✅ Virtual environment activated"
echo ""

# Check if dependencies are installed
echo "Checking dependencies..."
if ! python -c "import olist_bi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -e ".[app,dev]"
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi
echo ""

# Check if warehouse exists
if [ ! -f "warehouse/olist.duckdb" ]; then
    echo "Warehouse not found. Generating synthetic data..."
    echo "This may take a few minutes..."
    echo ""
    
    # Generate synthetic data
    python -m olist_bi.cli synth
    
    # Build warehouse
    python -m olist_bi.cli etl
    
    echo ""
    echo "✅ Warehouse built successfully"
else
    echo "✅ Warehouse already exists"
fi
echo ""

# Check if Ollama is running
echo "Checking Ollama..."
if command -v ollama &> /dev/null; then
    if curl -s http://localhost:11434 > /dev/null 2>&1; then
        echo "✅ Ollama is running"
    else
        echo "⚠️  Ollama is installed but not running"
        echo "   Please start Ollama with: ollama serve"
        echo ""
    fi
else
    echo "⚠️  Ollama is not installed"
    echo "   The agent feature requires Ollama"
    echo "   Download from: https://ollama.com/download"
    echo ""
fi

# Run tests
echo "Running tests..."
pytest -q
echo ""

echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "To start the dashboard, run:"
echo "  make app"
echo ""
echo "Or manually:"
echo "  streamlit run src/olist_bi/app/streamlit_app.py"
echo ""
echo "The dashboard will be available at: http://localhost:8501"
echo ""
echo "Quick commands:"
echo "  make synth   - Generate synthetic data"
echo "  make etl     - Build warehouse"
echo "  make kpis    - Show headline KPIs"
echo "  make app     - Start dashboard"
echo "  make test    - Run tests"
echo ""
