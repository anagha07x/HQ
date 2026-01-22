# ChanksHQ - Decision Intelligence Platform

## Original Problem Statement
Build a Decision Intelligence Platform that supports file upload (CSV, XLSX, XLS, JSON), data analysis, column role mapping, baseline forecasting, ROI curve analysis, and what-if scenario simulation.

## Core Requirements
- Single upload endpoint `/api/upload` accepting CSV, XLSX, XLS, JSON files
- Multi-sheet XLSX support
- Column role detection and mapping (TIME, ACTION, OUTCOME, METRIC, DIMENSION, IGNORE)
- Baseline forecast model (spend vs revenue regression)
- ROI efficiency curve analysis
- What-if scenario simulator
- Decision ledger for logging decisions
- Chat interface for querying analysis results
- **Industry-agnostic Decision Intelligence Engine**

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React
- **Database:** MongoDB
- **File Processing:** pandas, openpyxl, xlrd

## Architecture
```
/app/
├── backend/
│   └── server.py                    # FastAPI app with all endpoints
├── decision-ledger/
│   └── core/
│       ├── ontology.py              # Core ontology (Entity, Fact, Plan, Actual, Gap, Constraint, Action, Decision)
│       ├── decision_engine.py       # Main orchestrator
│       ├── sheet_classifier.py      # Structural sheet role inference
│       ├── entity_detector.py       # Cross-sheet entity detection
│       ├── relationship_graph.py    # Entity relationship graph
│       ├── gap_analyzer.py          # Plan vs Actual gap detection
│       ├── constraint_extractor.py  # Text-based constraint extraction
│       ├── decision_generator.py    # Decision candidate generation
│       ├── ingestion_engine.py      # Bulletproof file ingestion
│       ├── dataset_registry.py      # Data structure for parsed datasets
│       ├── ingestion.py             # Legacy ingestion (disk-based)
│       ├── role_mapper.py           # Column role detection
│       └── schema_detector.py       # Schema detection
├── frontend/
│   └── src/App.js                   # Main React application
└── uploads/                         # Uploaded file storage
```

## What's Been Implemented

### January 22, 2026 - Decision Intelligence Engine (COMPLETE)
**Feature:** Industry-agnostic decision intelligence that analyzes any enterprise workbook

**Core Ontology Implemented:**
- ENTITY: Detected things being tracked
- FACT: Recorded measurements
- PLAN: Target/planned values
- ACTUAL: Realized values
- GAP: Plan vs Actual deviations
- CONSTRAINT: Limitations from text fields
- ACTION: Proposed remediation steps
- DECISION: Candidates with evidence

**Processing Pipeline:**
1. ✅ Sheet role inference (structural, not name-based)
2. ✅ Data normalization (clean dataframes)
3. ✅ Entity detection across sheets
4. ✅ Entity relationship graph
5. ✅ Metric/dimension detection
6. ✅ Gap identification (plan vs actual)
7. ✅ Constraint extraction from text
8. ✅ Decision candidate generation
9. ✅ Decision ledger recording

**No Domain-Specific Logic:**
- No hardcoded keywords
- No industry-specific rules
- Pure structural and statistical analysis

**API Endpoints Added:**
- `POST /api/analyze-intelligence` - Run full analysis
- `GET /api/intelligence/{dataset_id}` - Get analysis results

### December 22, 2025 - File Upload Bug Fix (COMPLETE)
**Issue:** Persistent "Body is disturbed or locked" / RequestBodyReadError

**Solution:** 
- Read from SpooledTemporaryFile synchronously
- DataIngestionEngine accepts only raw bytes
- Added sanitize_for_json() for NaN/Inf handling

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload and analyze dataset file |
| `/api/analyze-intelligence` | POST | Run Decision Intelligence Engine |
| `/api/intelligence/{id}` | GET | Get intelligence analysis results |
| `/api/confirm-role-mapping` | POST | Confirm column role assignments |
| `/api/forecast` | POST | Generate baseline forecast |
| `/api/roi-curve` | POST | Generate ROI efficiency curve |
| `/api/simulate-scenario` | POST | Run what-if simulation |
| `/api/analyze-dataset` | POST | Run full dataset analysis |
| `/api/explain-results` | POST | Generate business explanations |
| `/api/chat` | POST | Chat with analysis results |
| `/api/decisions` | GET | Get logged decisions |
| `/api/decision` | POST | Log a new decision |
| `/api/health` | GET | Health check |

## Prioritized Backlog

### P0 (Critical) - COMPLETE
- [x] Fix file upload "Body is disturbed or locked" error
- [x] Implement industry-agnostic Decision Intelligence Engine

### P1 (High Priority)
- [ ] Add frontend UI for Decision Intelligence results
- [ ] Unify ingestion systems (migrate legacy endpoints to new engine)
- [ ] Add decision approval/rejection workflow

### P2 (Medium Priority)
- [ ] Add data preview before analysis
- [ ] Implement file size warning for large uploads
- [ ] Add visualization for entity relationship graph
- [ ] Export decision report to PDF

### P3 (Low Priority/Future)
- [ ] Add drag-and-drop file upload
- [ ] Multi-file comparison analysis
- [ ] Real-time collaboration on decisions
