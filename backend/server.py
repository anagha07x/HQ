import sys
sys.path.append('/app/decision-ledger')

from fastapi import FastAPI, APIRouter, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import math
from core.ingestion_engine import DataIngestionEngine
from core.dataset_registry import DatasetRegistry
from core.ingestion import DataIngestion  # Keep for analysis endpoints that load from disk
from core.schema_detector import SchemaDetector
from core.role_mapper import ColumnRoleMapper
from core.decision_engine import DecisionIntelligenceEngine
from core.vocabulary_adapter import IndustryVocabularyAdapter
from core.decision_explainer import DecisionExplainer
from core.decision_grouper import DecisionGroupingEngine
from models.baseline_model import BaselineModel
from models.roi_curve import ROICurve
from models.scenario_simulator import ScenarioSimulator
from ai.dataset_analyzer import DatasetAnalyzer
from ai.reasoning_agent import ReasoningAgent


def sanitize_for_json(obj: Any) -> Any:
    """Recursively sanitize data for JSON serialization.
    
    Converts NaN, Inf, -Inf to None to ensure JSON compliance.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.floating, np.integer)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif pd.isna(obj):
        return None
    else:
        return obj


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Decision Ledger endpoints
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ForecastRequest(BaseModel):
    dataset_id: str
    horizon: int = 30

class SimulateRequest(BaseModel):
    dataset_id: str
    current_spend: float
    proposed_spend: float

class RoleMappingRequest(BaseModel):
    dataset_id: str
    role_mapping: List[Dict[str, str]]  # [{"name": "spend", "role": "ACTION"}, ...]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    dataset_id: Optional[str] = None

@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Decision Ledger"}

@api_router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload dataset (CSV, XLSX, JSON) for analysis.
    
    BULLETPROOF implementation:
    - Captures bytes from SpooledTemporaryFile directly
    - Never calls file.read() on the async stream
    - Processes entirely from captured bytes
    - Immune to "Body is disturbed or locked" errors
    """
    try:
        # Generate dataset ID
        dataset_id = str(uuid.uuid4())
        filename = file.filename or "unknown"
        
        # CRITICAL: Capture bytes from the underlying SpooledTemporaryFile
        # This bypasses any async stream issues completely
        spooled_file = file.file  # This is a SpooledTemporaryFile
        spooled_file.seek(0)  # Ensure we're at the start
        file_bytes = spooled_file.read()  # Sync read from SpooledTemporaryFile
        
        # Validate we got data
        if not file_bytes:
            return {"status": "error", "message": "Empty file received"}
        
        logger.info(f"Captured {len(file_bytes)} bytes from {filename}")
        
        # Process using the bulletproof ingestion engine
        engine = DataIngestionEngine()
        registry = engine.ingest_from_bytes(file_bytes, filename, dataset_id)
        
        # Get primary dataset for role detection
        primary_df = registry.get_primary_dataset()
        primary_sheet = registry.list_datasets()[0]
        
        # Detect column roles
        role_mapper = ColumnRoleMapper()
        column_roles = role_mapper.detect_roles(primary_df)
        
        # Create uploads directory and save file for later analysis
        upload_dir = Path("/app/decision-ledger/data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file to disk using captured bytes
        file_path = upload_dir / filename
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Sanitize column_roles for JSON serialization (handles NaN, Inf)
        safe_column_roles = sanitize_for_json(column_roles)
        safe_metadata = sanitize_for_json(registry.metadata)
        
        # Store metadata in database
        file_doc = {
            "id": dataset_id,
            "filename": safe_metadata['filename'],
            "file_path": str(file_path),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "file_type": registry.source_type,
            "total_sheets": safe_metadata['total_sheets'],
            "sheet_names": safe_metadata['sheet_names'],
            "primary_sheet": primary_sheet,
            "size": safe_metadata['file_size_bytes'],
            "rows": safe_metadata['total_rows'],
            "columns": safe_metadata['total_columns'],
            "column_roles": safe_column_roles,
            "role_mapping_confirmed": False,
            "ingestion_metadata": safe_metadata
        }
        await db.datasets.insert_one(file_doc)
        
        logger.info(
            f"Dataset uploaded: {dataset_id}, "
            f"type: {registry.source_type}, "
            f"sheets: {len(registry.datasets)}"
        )
        
        # Return sanitized response
        return sanitize_for_json({
            "status": "success",
            "message": f"{registry.source_type.upper()} file '{filename}' uploaded and analyzed successfully",
            "dataset_id": dataset_id,
            "file_type": registry.source_type,
            "sheets": safe_metadata['sheet_names'],
            "primary_sheet": primary_sheet,
            "rows": safe_metadata['total_rows'],
            "column_roles": safe_column_roles
        })
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Failed to process file: {str(e)}"}


@api_router.post("/analyze-intelligence")
async def analyze_intelligence(request: ForecastRequest):
    """Run Decision Intelligence Engine on uploaded dataset.
    
    Industry-agnostic analysis that:
    - Infers sheet roles from structure
    - Detects entities across sheets
    - Builds entity relationship graph
    - Identifies plan-actual gaps
    - Extracts constraints from text
    - Generates decision candidates
    
    No domain-specific logic - pure structural analysis.
    """
    try:
        # Get dataset metadata from database
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        file_path = dataset.get("file_path")
        if not file_path:
            return {"status": "error", "message": "Dataset file path not found"}
        
        # Load data using universal ingestion
        ingestion = DataIngestion()
        ingestion_result = await ingestion.ingest_file(file_path)
        datasets = ingestion_result['dataframes']
        
        logger.info(f"Running Decision Intelligence Engine on {len(datasets)} sheets")
        
        # Run the Decision Intelligence Engine
        engine = DecisionIntelligenceEngine()
        result = engine.analyze(datasets, request.dataset_id)
        
        # Convert to dict for response
        result_dict = engine.to_dict(result)
        
        # Sanitize for JSON
        safe_result = sanitize_for_json(result_dict)
        
        # Store analysis in database
        analysis_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "analysis_type": "decision_intelligence",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "results": safe_result
        }
        await db.intelligence_analyses.insert_one(analysis_doc)
        
        logger.info(
            f"Decision Intelligence complete: "
            f"{result.entity_count} entities, "
            f"{result.gap_count} gaps, "
            f"{result.decision_count} decisions"
        )
        
        return {
            "status": "success",
            "analysis_id": analysis_doc["id"],
            "summary": {
                "sheet_count": result.sheet_count,
                "entity_count": result.entity_count,
                "gap_count": result.gap_count,
                "critical_gaps": result.critical_gaps,
                "constraint_count": result.constraint_count,
                "blocking_constraints": result.blocking_constraints,
                "decision_count": result.decision_count,
                "top_decision_summary": result.top_decision_summary
            },
            "sheet_roles": safe_result.get("sheet_roles", {}),
            "entities": safe_result.get("entities", [])[:10],  # Top 10
            "gaps": safe_result.get("gaps", [])[:20],  # Top 20
            "constraints": safe_result.get("constraints", [])[:10],  # Top 10
            "decisions": safe_result.get("decisions", []),
            "processing_notes": safe_result.get("processing_notes", [])
        }
        
    except Exception as e:
        logger.error(f"Decision Intelligence error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.get("/intelligence/{dataset_id}")
async def get_intelligence_analysis(dataset_id: str):
    """Get the latest Decision Intelligence analysis for a dataset."""
    try:
        analysis = await db.intelligence_analyses.find_one(
            {"dataset_id": dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not analysis:
            return {
                "status": "error",
                "message": "No analysis found. Run /api/analyze-intelligence first."
            }
        
        return {
            "status": "success",
            **sanitize_for_json(analysis)
        }
        
    except Exception as e:
        logger.error(f"Get intelligence error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================================
# DECISION INTELLIGENCE PLATFORM - NEW API ENDPOINTS
# ============================================================

class DecisionAction(BaseModel):
    """Request model for decision approval/rejection."""
    user_id: Optional[str] = "system"
    notes: Optional[str] = ""


@api_router.get("/intelligence/{dataset_id}/summary")
async def get_intelligence_summary(dataset_id: str):
    """Get dataset overview with sheets, entities, and summary stats."""
    try:
        # Get dataset info
        dataset = await db.datasets.find_one({"id": dataset_id}, {"_id": 0})
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        # Get analysis
        analysis = await db.intelligence_analyses.find_one(
            {"dataset_id": dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not analysis:
            return {"status": "error", "message": "No analysis found. Run analyze-intelligence first."}
        
        results = analysis.get("results", {})
        
        # Build summary response
        return sanitize_for_json({
            "status": "success",
            "dataset": {
                "id": dataset_id,
                "filename": dataset.get("filename", "Unknown"),
                "uploaded_at": dataset.get("uploaded_at"),
                "file_type": dataset.get("file_type"),
                "total_rows": dataset.get("rows", 0),
                "total_columns": dataset.get("columns", 0)
            },
            "analysis": {
                "analyzed_at": results.get("analyzed_at"),
                "sheet_count": results.get("sheet_count", 0),
                "entity_count": results.get("entity_count", 0),
                "gap_count": results.get("gap_count", 0),
                "critical_gaps": results.get("critical_gaps", 0),
                "constraint_count": results.get("constraint_count", 0),
                "blocking_constraints": results.get("blocking_constraints", 0),
                "decision_count": results.get("decision_count", 0)
            },
            "sheets": [
                {
                    "name": name,
                    "role": role,
                    "profile": results.get("sheet_profiles", {}).get(name, {})
                }
                for name, role in results.get("sheet_roles", {}).items()
            ],
            "entities": results.get("entities", []),
            "entity_graph": results.get("entity_graph", {}),
            "top_decision_summary": results.get("top_decision_summary", "")
        })
        
    except Exception as e:
        logger.error(f"Get summary error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.get("/intelligence/{dataset_id}/gaps")
async def get_intelligence_gaps(dataset_id: str):
    """Get all gaps with severity breakdown and impact analysis."""
    try:
        analysis = await db.intelligence_analyses.find_one(
            {"dataset_id": dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not analysis:
            return {"status": "error", "message": "No analysis found"}
        
        results = analysis.get("results", {})
        gaps = results.get("gaps", [])
        
        # Calculate severity breakdown
        critical = [g for g in gaps if g.get("severity") == "critical"]
        warning = [g for g in gaps if g.get("severity") == "warning"]
        normal = [g for g in gaps if g.get("severity") == "normal"]
        
        # Calculate total impact
        total_impact = sum(abs(g.get("absolute_gap", 0) or 0) for g in gaps)
        critical_impact = sum(abs(g.get("absolute_gap", 0) or 0) for g in critical)
        
        # Group gaps by entity
        entity_gaps = {}
        for gap in gaps:
            entity_id = gap.get("entity_id", "unknown")
            if entity_id not in entity_gaps:
                entity_gaps[entity_id] = []
            entity_gaps[entity_id].append(gap)
        
        return sanitize_for_json({
            "status": "success",
            "summary": {
                "total_gaps": len(gaps),
                "critical_count": len(critical),
                "warning_count": len(warning),
                "normal_count": len(normal),
                "total_impact": total_impact,
                "critical_impact": critical_impact
            },
            "gaps": gaps,
            "gaps_by_entity": entity_gaps,
            "plans": results.get("plans", []),
            "actuals": results.get("actuals", [])
        })
        
    except Exception as e:
        logger.error(f"Get gaps error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.get("/intelligence/{dataset_id}/constraints")
async def get_intelligence_constraints(dataset_id: str):
    """Get all constraints grouped by type."""
    try:
        analysis = await db.intelligence_analyses.find_one(
            {"dataset_id": dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not analysis:
            return {"status": "error", "message": "No analysis found"}
        
        results = analysis.get("results", {})
        constraints = results.get("constraints", [])
        
        # Group by constraint type
        grouped = {}
        for c in constraints:
            ctype = c.get("constraint_type", "other")
            if ctype not in grouped:
                grouped[ctype] = []
            grouped[ctype].append(c)
        
        # Calculate blocking count
        blocking_types = {"blocking", "deadline", "dependency"}
        blocking = [c for c in constraints if c.get("constraint_type") in blocking_types]
        
        return sanitize_for_json({
            "status": "success",
            "summary": {
                "total_constraints": len(constraints),
                "blocking_count": len(blocking),
                "type_breakdown": {k: len(v) for k, v in grouped.items()}
            },
            "constraints": constraints,
            "constraints_by_type": grouped
        })
        
    except Exception as e:
        logger.error(f"Get constraints error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.get("/intelligence/{dataset_id}/decisions")
async def get_intelligence_decisions(dataset_id: str):
    """Get all decision candidates with their evidence."""
    try:
        analysis = await db.intelligence_analyses.find_one(
            {"dataset_id": dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not analysis:
            return {"status": "error", "message": "No analysis found"}
        
        results = analysis.get("results", {})
        decisions = results.get("decisions", [])
        
        # Enrich decisions with status from ledger
        enriched_decisions = []
        for d in decisions:
            decision_id = d.get("id")
            
            # Check if decision has been acted upon
            ledger_entry = await db.decision_ledger_entries.find_one(
                {"decision_id": decision_id},
                {"_id": 0}
            )
            
            enriched = {**d}
            if ledger_entry:
                enriched["ledger_status"] = ledger_entry.get("status", "pending")
                enriched["acted_at"] = ledger_entry.get("acted_at")
                enriched["acted_by"] = ledger_entry.get("acted_by")
            else:
                enriched["ledger_status"] = "pending"
            
            enriched_decisions.append(enriched)
        
        # Group by status
        pending = [d for d in enriched_decisions if d.get("ledger_status") == "pending"]
        approved = [d for d in enriched_decisions if d.get("ledger_status") == "approved"]
        rejected = [d for d in enriched_decisions if d.get("ledger_status") == "rejected"]
        
        return sanitize_for_json({
            "status": "success",
            "summary": {
                "total_decisions": len(decisions),
                "pending_count": len(pending),
                "approved_count": len(approved),
                "rejected_count": len(rejected)
            },
            "decisions": enriched_decisions,
            "decisions_by_status": {
                "pending": pending,
                "approved": approved,
                "rejected": rejected
            }
        })
        
    except Exception as e:
        logger.error(f"Get decisions error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.post("/decisions/{decision_id}/approve")
async def approve_decision(decision_id: str, action: DecisionAction):
    """Approve a decision and record in ledger."""
    try:
        # Find the decision in any analysis
        analysis = await db.intelligence_analyses.find_one(
            {"results.decisions.id": decision_id},
            {"_id": 0}
        )
        
        if not analysis:
            return {"status": "error", "message": "Decision not found"}
        
        # Find the specific decision
        decisions = analysis.get("results", {}).get("decisions", [])
        decision = next((d for d in decisions if d.get("id") == decision_id), None)
        
        if not decision:
            return {"status": "error", "message": "Decision not found in analysis"}
        
        # Check if already acted upon
        existing = await db.decision_ledger_entries.find_one({"decision_id": decision_id})
        if existing:
            return {
                "status": "error",
                "message": f"Decision already {existing.get('status', 'processed')}"
            }
        
        # Create ledger entry
        ledger_entry = {
            "id": str(uuid.uuid4()),
            "decision_id": decision_id,
            "dataset_id": analysis.get("dataset_id"),
            "analysis_id": analysis.get("id"),
            "decision_type": decision.get("decision_type"),
            "summary": decision.get("summary"),
            "reasoning": decision.get("reasoning"),
            "evidence": decision,
            "expected_impact": decision.get("impact_score"),
            "confidence": decision.get("confidence_score"),
            "status": "approved",
            "acted_by": action.user_id,
            "acted_at": datetime.now(timezone.utc).isoformat(),
            "notes": action.notes,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.decision_ledger_entries.insert_one(ledger_entry)
        
        logger.info(f"Decision {decision_id} approved by {action.user_id}")
        
        return sanitize_for_json({
            "status": "success",
            "message": "Decision approved and recorded in ledger",
            "ledger_entry": {k: v for k, v in ledger_entry.items() if k != "_id"}
        })
        
    except Exception as e:
        logger.error(f"Approve decision error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.post("/decisions/{decision_id}/reject")
async def reject_decision(decision_id: str, action: DecisionAction):
    """Reject a decision and record in ledger."""
    try:
        # Find the decision
        analysis = await db.intelligence_analyses.find_one(
            {"results.decisions.id": decision_id},
            {"_id": 0}
        )
        
        if not analysis:
            return {"status": "error", "message": "Decision not found"}
        
        decisions = analysis.get("results", {}).get("decisions", [])
        decision = next((d for d in decisions if d.get("id") == decision_id), None)
        
        if not decision:
            return {"status": "error", "message": "Decision not found in analysis"}
        
        # Check if already acted upon
        existing = await db.decision_ledger_entries.find_one({"decision_id": decision_id})
        if existing:
            return {
                "status": "error",
                "message": f"Decision already {existing.get('status', 'processed')}"
            }
        
        # Create ledger entry
        ledger_entry = {
            "id": str(uuid.uuid4()),
            "decision_id": decision_id,
            "dataset_id": analysis.get("dataset_id"),
            "analysis_id": analysis.get("id"),
            "decision_type": decision.get("decision_type"),
            "summary": decision.get("summary"),
            "reasoning": decision.get("reasoning"),
            "evidence": decision,
            "expected_impact": decision.get("impact_score"),
            "confidence": decision.get("confidence_score"),
            "status": "rejected",
            "acted_by": action.user_id,
            "acted_at": datetime.now(timezone.utc).isoformat(),
            "notes": action.notes,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.decision_ledger_entries.insert_one(ledger_entry)
        
        logger.info(f"Decision {decision_id} rejected by {action.user_id}")
        
        return sanitize_for_json({
            "status": "success",
            "message": "Decision rejected and recorded in ledger",
            "ledger_entry": {k: v for k, v in ledger_entry.items() if k != "_id"}
        })
        
    except Exception as e:
        logger.error(f"Reject decision error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.get("/ledger")
async def get_decision_ledger(dataset_id: Optional[str] = None):
    """Get the decision ledger, optionally filtered by dataset."""
    try:
        query = {}
        if dataset_id:
            query["dataset_id"] = dataset_id
        
        entries = await db.decision_ledger_entries.find(
            query,
            {"_id": 0}
        ).sort("acted_at", -1).to_list(1000)
        
        # Group by status
        approved = [e for e in entries if e.get("status") == "approved"]
        rejected = [e for e in entries if e.get("status") == "rejected"]
        
        return sanitize_for_json({
            "status": "success",
            "summary": {
                "total_entries": len(entries),
                "approved_count": len(approved),
                "rejected_count": len(rejected)
            },
            "entries": entries,
            "entries_by_status": {
                "approved": approved,
                "rejected": rejected
            }
        })
        
    except Exception as e:
        logger.error(f"Get ledger error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.get("/datasets")
async def get_datasets():
    """Get all uploaded datasets with their analysis status."""
    try:
        datasets = await db.datasets.find({}, {"_id": 0}).sort("uploaded_at", -1).to_list(100)
        
        # Enrich with analysis status
        enriched = []
        for d in datasets:
            analysis = await db.intelligence_analyses.find_one(
                {"dataset_id": d.get("id")},
                {"_id": 0, "id": 1, "created_at": 1}
            )
            
            enriched.append({
                **d,
                "has_analysis": analysis is not None,
                "analysis_id": analysis.get("id") if analysis else None,
                "analyzed_at": analysis.get("created_at") if analysis else None
            })
        
        return sanitize_for_json({
            "status": "success",
            "datasets": enriched
        })
        
    except Exception as e:
        logger.error(f"Get datasets error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@api_router.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint - READ ONLY from analysis outputs (Step 7: Chat layer)."""
    try:
        # Build context from stored analyses
        context = {}
        
        if request.dataset_id:
            # Get dataset analysis
            dataset_analysis = await db.dataset_analyses.find_one(
                {"dataset_id": request.dataset_id},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            
            if dataset_analysis:
                context["dataset_analysis"] = dataset_analysis.get("results", {})
            
            # Get forecast
            forecast = await db.forecasts.find_one(
                {"dataset_id": request.dataset_id},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            
            if forecast:
                context["forecast"] = forecast.get("results", {})
            
            # Get ROI analysis
            roi = await db.roi_analyses.find_one(
                {"dataset_id": request.dataset_id},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            
            if roi:
                context["roi"] = roi.get("results", {})
            
            # Get decision ledger
            decision = await db.decision_ledger.find_one(
                {"dataset_id": request.dataset_id},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            
            if decision:
                context["decision_ledger"] = decision
        
        if not context:
            return {
                "status": "error",
                "message": "No analysis available. Please upload data and run analysis first."
            }
        
        # Get response from reasoning agent (READ ONLY)
        emergent_key = os.getenv("EMERGENT_LLM_KEY")
        reasoning = ReasoningAgent(api_key=emergent_key)
        
        response_text = await reasoning.chat_response(
            user_message=request.message,
            context=context,
            session_id=request.session_id
        )
        
        # Store chat exchange
        chat_doc = {
            "session_id": request.session_id,
            "dataset_id": request.dataset_id,
            "user_message": request.message,
            "bot_response": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages.insert_one(chat_doc)
        
        return {
            "status": "success",
            "response": response_text,
            "session_id": request.session_id,
            "timestamp": chat_doc["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/forecast")
async def generate_forecast(request: ForecastRequest):
    """Generate forecast for uploaded dataset."""
    try:
        # Get dataset from database
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        # Check if role mapping is confirmed
        if not dataset.get("role_mapping_confirmed", False):
            return {
                "status": "error",
                "message": "Please confirm column role mapping first"
            }
        
        file_path = dataset["file_path"]
        role_mapping = dataset.get("role_mapping", [])
        
        # Extract ACTION and OUTCOME columns from role mapping
        action_col = None
        outcome_col = None
        
        for col_map in role_mapping:
            if col_map["role"] == "ACTION":
                action_col = col_map["name"]
                break
        
        for col_map in role_mapping:
            if col_map["role"] == "OUTCOME":
                outcome_col = col_map["name"]
                break
        
        if not action_col or not outcome_col:
            return {
                "status": "error",
                "message": "Required ACTION and OUTCOME columns not found in role mapping"
            }
        
        # Load data using universal ingestion
        ingestion = DataIngestion()
        ingestion_result = await ingestion.ingest_file(file_path)
        primary_sheet = dataset.get("primary_sheet", ingestion_result['sheets'][0])
        df = ingestion_result['dataframes'][primary_sheet]
        
        # Get TIME column if present
        time_col = None
        for col_map in role_mapping:
            if col_map["role"] == "TIME":
                time_col = col_map["name"]
                break
        
        # Convert date column if detected
        if time_col:
            df[time_col] = pd.to_datetime(df[time_col])
            df = df.sort_values(by=time_col)
        
        # Train baseline model
        baseline_model = BaselineModel()
        results = baseline_model.train_spend_revenue_model(df, action_col, outcome_col)
        
        # Store forecast in database
        forecast_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "model_type": "baseline_regression",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action_column": action_col,
            "outcome_column": outcome_col,
            "results": results
        }
        await db.forecasts.insert_one(forecast_doc)
        
        return {
            "status": "success",
            "forecast_id": forecast_doc["id"],
            **results
        }
        
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/decision")
async def log_decision(decision: dict):
    """Log a decision to the ledger."""
    decision_doc = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        **decision
    }
    await db.decisions.insert_one(decision_doc)
    return {"status": "success", "decision_id": decision_doc["id"]}

@api_router.get("/decisions")
async def get_decisions():
    """Retrieve all logged decisions."""
    decisions = await db.decisions.find({}, {"_id": 0}).to_list(100)
    return {"status": "success", "decisions": decisions}

@api_router.post("/roi-curve")
async def generate_roi_curve(request: ForecastRequest):
    """Generate ROI efficiency curve for dataset."""
    try:
        # Get dataset from database
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        # Check if role mapping is confirmed
        if not dataset.get("role_mapping_confirmed", False):
            return {
                "status": "error",
                "message": "Please confirm column role mapping first"
            }
        
        file_path = dataset["file_path"]
        role_mapping = dataset.get("role_mapping", [])
        
        # Extract ACTION and OUTCOME columns from role mapping
        action_col = None
        outcome_col = None
        
        for col_map in role_mapping:
            if col_map["role"] == "ACTION":
                action_col = col_map["name"]
                break
        
        for col_map in role_mapping:
            if col_map["role"] == "OUTCOME":
                outcome_col = col_map["name"]
                break
        
        if not action_col or not outcome_col:
            return {
                "status": "error",
                "message": "Required ACTION and OUTCOME columns not found in role mapping"
            }
        
        # Load data using universal ingestion
        ingestion = DataIngestion()
        ingestion_result = await ingestion.ingest_file(file_path)
        primary_sheet = dataset.get("primary_sheet", ingestion_result['sheets'][0])
        df = ingestion_result['dataframes'][primary_sheet]
        
        # Fit ROI curve models
        roi_curve = ROICurve()
        results = roi_curve.fit_roi_models(df, action_col, outcome_col)
        
        # Store ROI analysis in database
        roi_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "analysis_type": "roi_curve",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action_column": action_col,
            "outcome_column": outcome_col,
            "results": results
        }
        await db.roi_analyses.insert_one(roi_doc)
        
        return {
            "status": "success",
            "analysis_id": roi_doc["id"],
            **results
        }
        
    except Exception as e:
        logger.error(f"ROI curve error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/simulate-scenario")
async def simulate_scenario(request: SimulateRequest):
    """Simulate what-if scenario with different spend levels."""
    try:
        # Get dataset from database
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        # Get ROI analysis for this dataset
        roi_analysis = await db.roi_analyses.find_one(
            {"dataset_id": request.dataset_id}, 
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not roi_analysis:
            return {
                "status": "error",
                "message": "ROI analysis not found. Please generate ROI curve first."
            }
        
        # Initialize simulator with ROI model
        simulator = ScenarioSimulator()
        simulator.set_roi_model(
            roi_analysis["results"]["best_fit"],
            roi_analysis["results"]["parameters"]
        )
        
        # Run simulation
        results = simulator.simulate_what_if(
            request.current_spend,
            request.proposed_spend
        )
        
        # Store simulation in database
        simulation_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "simulation_type": "what_if",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "current_spend": request.current_spend,
                "proposed_spend": request.proposed_spend
            },
            "results": results
        }
        await db.simulations.insert_one(simulation_doc)
        
        return {
            "status": "success",
            "simulation_id": simulation_doc["id"],
            **results
        }
        
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/confirm-role-mapping")
async def confirm_role_mapping(request: RoleMappingRequest):
    """Confirm and save column role mapping for dataset."""
    try:
        # Get dataset
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        # Validate role mapping
        role_mapper = ColumnRoleMapper()
        validation = role_mapper.validate_role_mapping(request.role_mapping)
        
        if not validation["valid"]:
            return {
                "status": "error",
                "message": "Invalid role mapping",
                "errors": validation["errors"]
            }
        
        # Update dataset with confirmed mapping
        await db.datasets.update_one(
            {"id": request.dataset_id},
            {"$set": {
                "role_mapping": request.role_mapping,
                "role_mapping_confirmed": True,
                "role_validation": validation,
                "mapping_confirmed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "status": "success",
            "message": "Role mapping confirmed and saved",
            "validation": validation
        }
        
    except Exception as e:
        logger.error(f"Role mapping error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/analyze-dataset")
async def analyze_dataset(request: ForecastRequest):
    """Run structured dataset analysis pipeline (Step 2 of reasoning flow)."""
    try:
        # Get dataset
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        if not dataset.get("role_mapping_confirmed", False):
            return {
                "status": "error",
                "message": "Please confirm column role mapping first"
            }
        
        # Load data using universal ingestion
        ingestion = DataIngestion()
        ingestion_result = await ingestion.ingest_file(dataset["file_path"])
        
        # Get primary dataframe
        primary_sheet = dataset.get("primary_sheet", ingestion_result['sheets'][0])
        df = ingestion_result['dataframes'][primary_sheet]
        
        # Run analysis pipeline
        emergent_key = os.getenv("EMERGENT_LLM_KEY")
        analyzer = DatasetAnalyzer(api_key=emergent_key)
        
        analysis = await analyzer.analyze_dataset(
            df=df,
            role_mapping=dataset.get("role_mapping", []),
            dataset_id=request.dataset_id
        )
        
        # Add file type context
        analysis['file_info'] = {
            'file_type': ingestion_result['file_type'],
            'sheets': ingestion_result['sheets'],
            'primary_sheet': primary_sheet
        }
        
        # Store analysis
        analysis_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "analysis_type": "structured_pipeline",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "results": analysis
        }
        await db.dataset_analyses.insert_one(analysis_doc)
        
        return {
            "status": "success",
            "analysis_id": analysis_doc["id"],
            **analysis
        }
        
    except Exception as e:
        logger.error(f"Dataset analysis error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/explain-results")
async def explain_results(request: ForecastRequest):
    """Generate business explanations for all model outputs (Step 6: Explainability)."""
    try:
        # Get dataset and analysis
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        # Get stored analysis
        dataset_analysis = await db.dataset_analyses.find_one(
            {"dataset_id": request.dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if not dataset_analysis:
            return {
                "status": "error",
                "message": "Please run dataset analysis first (/api/analyze-dataset)"
            }
        
        # Get model outputs
        forecast = await db.forecasts.find_one(
            {"dataset_id": request.dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        roi_analysis = await db.roi_analyses.find_one(
            {"dataset_id": request.dataset_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        # Initialize reasoning agent
        emergent_key = os.getenv("EMERGENT_LLM_KEY")
        reasoning = ReasoningAgent(api_key=emergent_key)
        
        explanations = {}
        
        # Explain forecast
        if forecast:
            explanations["forecast"] = await reasoning.explain_forecast_results(
                forecast.get("results", {}),
                dataset_analysis.get("results", {})
            )
        
        # Explain ROI
        if roi_analysis:
            explanations["roi"] = await reasoning.explain_roi_analysis(
                roi_analysis.get("results", {}),
                dataset_analysis.get("results", {})
            )
        
        # Generate decision summary
        all_outputs = {
            "dataset_analysis": dataset_analysis.get("results", {}),
            "forecast": forecast.get("results", {}) if forecast else None,
            "roi": roi_analysis.get("results", {}) if roi_analysis else None
        }
        
        decision_summary = await reasoning.generate_decision_summary(
            request.dataset_id,
            all_outputs
        )
        
        # Store in decision ledger
        ledger_entry = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision_summary,
            "explanations": explanations
        }
        await db.decision_ledger.insert_one(ledger_entry)
        
        return {
            "status": "success",
            "ledger_id": ledger_entry["id"],
            "explanations": explanations,
            "decision_summary": decision_summary
        }
        
    except Exception as e:
        logger.error(f"Explanation error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()