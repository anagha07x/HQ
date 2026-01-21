# Decision Ledger

AI-powered decision tracking and forecasting system.

## Overview

Decision Ledger is a production-style Python application that combines:
- **Data ingestion & validation** from CSV files
- **Time series forecasting** using Prophet and statistical models
- **LLM-based reasoning** for decision analysis (Claude Sonnet 4.5)
- **Decision tracking** with outcome comparison
- **Scenario simulation** and what-if analysis

## Project Structure

```
decision-ledger/
├── app.py                 # Main FastAPI application
├── config/               # Configuration and prompts
├── data/                 # Data storage (uploads, processed, samples)
├── core/                 # Data processing modules
├── models/               # Forecasting models
├── ledger/               # Decision logging and tracking
├── ai/                   # LLM agents
├── database/             # MongoDB connection and models
├── services/             # Business logic services
├── utils/                # Utility functions
└── requirements.txt      # Python dependencies
```

## Technology Stack

- **Backend**: FastAPI
- **Database**: MongoDB
- **Data Processing**: pandas, numpy
- **Forecasting**: Prophet, statsmodels
- **LLM**: Claude Sonnet 4.5 (via Emergent LLM key)
- **Frontend**: React (in development)

## Setup

1. Install dependencies:
```bash
cd /app/decision-ledger
pip install -r requirements.txt
```

2. Configure environment variables (see backend/.env)

3. Run the application:
```bash
python app.py
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload` - Upload CSV dataset
- `POST /api/chat` - Chat with AI reasoning agent
- `POST /api/forecast` - Generate forecast
- `POST /api/decision` - Log a decision
- `GET /api/decisions` - Retrieve decisions

## Features (Planned)

### Core Modules

1. **Data Ingestion** (`core/`)
   - CSV upload and validation
   - Schema detection
   - Data preprocessing
   - Feature engineering

2. **Forecasting** (`models/`)
   - Prophet-based forecasting
   - Baseline models
   - ROI curve analysis
   - Scenario simulation

3. **Decision Ledger** (`ledger/`)
   - Decision logging
   - Outcome tracking
   - Performance metrics

4. **AI Reasoning** (`ai/`)
   - LLM-based analysis
   - Decision recommendations
   - Natural language explanations

5. **Services** (`services/`)
   - Forecast orchestration
   - Decision lifecycle management
   - Simulation engine

## Current Status

✅ Folder structure created
✅ Placeholder functions defined
⏳ Implementation in progress

## Next Steps

1. Implement core data ingestion logic
2. Build Prophet forecasting pipeline
3. Integrate Claude Sonnet 4.5 reasoning
4. Create React frontend
5. Add comprehensive testing

## Notes

- This is an MVP focusing on modular, production-ready code
- MongoDB is used for flexibility (can migrate to PostgreSQL later)
- All modules include type hints and docstrings
- Placeholder functions are ready for implementation
