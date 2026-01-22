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
│       ├── ingestion_engine.py      # Bulletproof file ingestion (bytes-only)
│       ├── dataset_registry.py      # Data structure for parsed datasets
│       ├── ingestion.py             # Legacy ingestion (disk-based)
│       ├── role_mapper.py           # Column role detection
│       └── schema_detector.py       # Schema detection
├── frontend/
│   └── src/App.js                   # Main React application
└── uploads/                         # Uploaded file storage
```

## What's Been Implemented

### December 22, 2025 - File Upload Bug Fix (COMPLETE)
**Issue:** Persistent "Body is disturbed or locked" / RequestBodyReadError during file uploads

**Root Cause:** The UploadFile async stream was being consumed by middleware or multiple read attempts before the endpoint could process it.

**Solution Implemented:**
1. **Backend Changes:**
   - Rewrote `ingestion_engine.py` to accept only raw bytes (never touches UploadFile)
   - Modified upload endpoint to read from `file.file` (SpooledTemporaryFile) synchronously
   - Added `sanitize_for_json()` utility to handle NaN/Inf values in responses
   - Removed async file.read() calls that could fail with body lock issues

2. **Key Code Pattern:**
   ```python
   # Capture bytes from underlying SpooledTemporaryFile (sync, bulletproof)
   spooled_file = file.file
   spooled_file.seek(0)
   file_bytes = spooled_file.read()
   
   # Process from bytes only
   registry = engine.ingest_from_bytes(file_bytes, filename, dataset_id)
   ```

3. **Files Modified:**
   - `/app/backend/server.py` - Upload endpoint rewritten
   - `/app/decision-ledger/core/ingestion_engine.py` - Bytes-only processing
   - `/app/decision-ledger/core/role_mapper.py` - NaN handling in sample values

**Verification:**
- CSV upload: SUCCESS
- JSON upload: SUCCESS
- XLSX multi-sheet (JAN V4.xlsx with 3518 rows, 7 sheets): SUCCESS
- Rapid consecutive uploads: SUCCESS

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload and analyze dataset file |
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

### P1 (High Priority)
- [ ] Unify ingestion systems (migrate legacy endpoints to new engine)
- [ ] Add file type validation error messages to UI
- [ ] Add upload progress indicator

### P2 (Medium Priority)
- [ ] Add data preview before analysis
- [ ] Implement file size warning for large uploads
- [ ] Add support for compressed files (.zip containing data files)

### P3 (Low Priority/Future)
- [ ] Add drag-and-drop file upload
- [ ] Export analysis results to PDF
- [ ] Multi-file comparison analysis
