# Olist BI - Setup Guide

This guide will help you set up and run the Olist BI platform on Windows, macOS, or Linux.

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.10 or higher**
   - Download from: https://www.python.org/downloads/
   - Verify installation: `python --version` or `python3 --version`

2. **Git** (for cloning the repository)
   - Download from: https://git-scm.com/

3. **Ollama** (required for the AI agent feature)
   - Download from: https://ollama.com/download
   - This is needed for the LLM analyst agent to work
   - After installation, run: `ollama serve`

## Quick Start (Recommended)

### For All Platforms

We've created an automated setup script that works on Windows, macOS, and Linux.

#### Windows
1. Double-click `setup.bat` in File Explorer, or
2. Run in Command Prompt or PowerShell:
   ```cmd
   setup.bat
   ```

#### macOS/Linux
1. Make the script executable:
   ```bash
   chmod +x setup.sh
   ```
2. Run the script:
   ```bash
   ./setup.sh
   ```

The script will:
- Create a virtual environment
- Install all dependencies
- Generate synthetic test data
- Build the data warehouse
- Run tests

### Manual Setup (Alternative)

If you prefer to set up manually:

#### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd olist-agentic-bi
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -e ".[app,dev]"
```

#### 4. Generate Data and Build Warehouse
```bash
# Generate synthetic data (for testing)
python -m olist_bi.cli synth

# Build the warehouse
python -m olist_bi.cli etl
```

#### 5. Run Tests
```bash
pytest
```

#### 6. Start the Dashboard
```bash
make app
# or
streamlit run src/olist_bi/app/streamlit_app.py
```

The dashboard will be available at: http://localhost:8501

## Using Real Olist Data (Optional)

The project includes synthetic data by default. If you want to use real Olist data:

1. Download the dataset from Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. Extract all CSV files into `data/raw/` folder
3. Run the ETL pipeline:
   ```bash
   make etl
   ```

**Note:** The CSV files are included in the repository, so you don't need to download them separately unless you want the latest data.

## Starting Ollama (for AI Agent)

The AI agent feature requires Ollama to be running:

### Windows
```cmd
ollama serve
```

### macOS/Linux
```bash
ollama serve
```

Or if you installed via Homebrew (macOS):
```bash
brew services start ollama
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make app` | Start the Streamlit dashboard |
| `make synth` | Generate synthetic test data |
| `make etl` | Build the data warehouse |
| `make kpis` | Show headline KPIs in terminal |
| `make test` | Run the test suite |
| `make lint` | Check code quality |
| `make fmt` | Format code automatically |

## Troubleshooting

### Python not found
- Add Python to your system PATH
- Restart your terminal after installation

### Virtual environment issues
- Delete the `.venv` folder and run the setup script again
- Ensure you have sufficient disk space

### Ollama connection errors
- Make sure Ollama is running: `ollama serve`
- Check if Ollama is accessible: http://localhost:11434
- The default model `llama3.1` will be downloaded automatically on first use

### Port 8501 already in use
- Kill the existing process or use a different port:
  ```bash
  streamlit run src/olist_bi/app/streamlit_app.py --server.port 8502
  ```

### Warehouse not found
- Run `make synth` to generate test data
- Then run `make etl` to build the warehouse

### Data not loading
- Ensure CSV files are in `data/raw/` folder
- Run `make etl` to rebuild the warehouse

## Project Structure

```
olist-agentic-bi/
├── src/olist_bi/
│   ├── etl/              # Data extraction and transformation
│   ├── warehouse/        # Database connection and KPIs
│   ├── analytics/        # Forecasting, segmentation, basket analysis
│   ├── agent/            # AI agent with LLM tools
│   └── app/              # Streamlit dashboard
├── tests/                # Test suite
├── data/                 # Raw data (CSV files included in repo)
├── warehouse/            # DuckDB warehouse (generated)
├── setup.sh              # Linux/macOS setup script
├── setup.bat             # Windows setup script
├── start.sh              # Linux/macOS start script
├── start.bat             # Windows start script
├── Makefile              # Convenience commands
└── pyproject.toml        # Project dependencies
```

## Next Steps

After setup is complete:

1. Open http://localhost:8501 in your browser
2. Explore the dashboard tabs:
   - **Overview**: Key metrics and KPIs
   - **Delivery & CX**: Delivery performance and customer experience
   - **Drill-down**: Detailed analysis by category, state, time
   - **Forecast**: Demand forecasting
   - **Segments**: Customer segmentation (RFM)
   - **Basket**: Market basket analysis
   - **Chat**: AI analyst agent (requires Ollama)

3. Try asking the AI agent questions like:
   - "What is the total revenue?"
   - "How have sales changed over time?"
   - "Which categories are performing best?"

## Need Help?

If you encounter any issues:
1. Check the troubleshooting section above
2. Run `make test` to verify the setup
3. Ensure Ollama is running for agent features
4. Check that all dependencies are installed correctly
