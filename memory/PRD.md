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
- **Production-grade Decision UI with approval workflow**

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React + Tailwind CSS + Custom Components
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
│       └── role_mapper.py           # Column role detection
├── frontend/
│   └── src/
│       ├── App.js                   # Main app (DecisionIntelligenceApp)
│       └── components/
│           └── decision-ui/
│               ├── DecisionIntelligenceApp.jsx  # Main Decision UI
│               ├── Badges.jsx       # ImpactBadge, SeverityBadge, etc.
│               ├── GapCard.jsx      # Gap display components
│               ├── DecisionCard.jsx # Decision card with approve/reject
│               └── EvidenceDrawer.jsx # Gap evidence drawer
└── uploads/                         # Uploaded file storage
```

## What's Been Implemented

### January 22, 2026 - Decision Intelligence UI (COMPLETE)
**Feature:** Production-grade Decision UI with approval workflow

**Frontend Pages Built:**
1. **Dataset Overview Page** - Shows dataset info, detected sheets with inferred roles, entities
2. **Gaps & Risk Dashboard** - Gap table with severity filtering, total impact at risk
3. **Constraints View** - Constraints grouped by type (exception, dependency, blocking)
4. **Decision Center** - Decision cards with approve/reject buttons, scores
5. **Decision Ledger** - Immutable record of all decision actions

**Reusable Components:**
- `ImpactBadge` - Shows impact values with trend indicators
- `SeverityBadge` - Critical/Warning/Normal badges
- `ConstraintBadge` - Typed constraint badges
- `SheetRoleBadge` - Sheet role indicators
- `ConfidenceMeter` - Visual confidence score
- `StatCard` - Summary statistics card
- `GapCard` - Gap display card and table row
- `DecisionCard` - Full decision card with actions
- `EvidenceDrawer` - Slide-out gap evidence panel

**Backend APIs Added:**
- `GET /api/datasets` - List all datasets with analysis status
- `GET /api/intelligence/{id}/summary` - Dataset overview
- `GET /api/intelligence/{id}/gaps` - All gaps with breakdown
- `GET /api/intelligence/{id}/constraints` - Constraints by type
- `GET /api/intelligence/{id}/decisions` - Decisions with ledger status
- `POST /api/decisions/{id}/approve` - Approve decision
- `POST /api/decisions/{id}/reject` - Reject decision
- `GET /api/ledger` - Decision ledger entries

**Database Collections:**
- `decision_ledger_entries` - Immutable decision records

### January 22, 2026 - Decision Intelligence Engine (COMPLETE)
**Feature:** Industry-agnostic decision intelligence engine

**Core Ontology:** Entity, Fact, Plan, Actual, Gap, Constraint, Action, Decision

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

### December 22, 2025 - File Upload Bug Fix (COMPLETE)
**Issue:** Persistent "Body is disturbed or locked" / RequestBodyReadError
**Solution:** Read from SpooledTemporaryFile synchronously

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload and analyze dataset file |
| `/api/analyze-intelligence` | POST | Run Decision Intelligence Engine |
| `/api/datasets` | GET | List all datasets |
| `/api/intelligence/{id}` | GET | Get full analysis |
| `/api/intelligence/{id}/summary` | GET | Get dataset overview |
| `/api/intelligence/{id}/gaps` | GET | Get gaps breakdown |
| `/api/intelligence/{id}/constraints` | GET | Get constraints by type |
| `/api/intelligence/{id}/decisions` | GET | Get decisions with status |
| `/api/decisions/{id}/approve` | POST | Approve a decision |
| `/api/decisions/{id}/reject` | POST | Reject a decision |
| `/api/ledger` | GET | Get decision ledger |

## User Flow
```
Upload workbook → AI analyzes → Gaps & risks detected → 
Decisions generated → Human approves/rejects → Decision ledger created
```

## Design Principles (Enforced)
1. No industry-specific logic anywhere
2. No hardcoded sheet names
3. No assumptions like "sales", "revenue", "manufacturing"
4. All reasoning from structure, relationships, metrics, deltas
5. LLMs never receive raw Excel data - only structured intelligence outputs

## Prioritized Backlog

### P0 (Critical) - COMPLETE
- [x] Fix file upload "Body is disturbed or locked" error
- [x] Implement industry-agnostic Decision Intelligence Engine
- [x] Build Decision Intelligence UI
- [x] Implement approval/rejection workflow
- [x] Create decision ledger

### P1 (High Priority)
- [ ] Add decision edit functionality
- [ ] Add export ledger to CSV/PDF
- [ ] Add user authentication for decision tracking

### P2 (Medium Priority)
- [ ] Add data preview before analysis
- [ ] Implement file size warning for large uploads
- [ ] Add visualization for entity relationship graph
- [ ] Add decision impact tracking over time

### P3 (Low Priority/Future)
- [ ] Add drag-and-drop file upload
- [ ] Multi-file comparison analysis
- [ ] Real-time collaboration on decisions
- [ ] Email notifications for decision assignments
