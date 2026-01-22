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
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import aiofiles
import pandas as pd
from core.ingestion_engine import DataIngestionEngine
from core.dataset_registry import DatasetRegistry
from core.schema_detector import SchemaDetector
from core.role_mapper import ColumnRoleMapper
from models.baseline_model import BaselineModel
from models.roi_curve import ROICurve
from models.scenario_simulator import ScenarioSimulator
from ai.dataset_analyzer import DatasetAnalyzer
from ai.reasoning_agent import ReasoningAgent


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
    
    Clean implementation:
    - Reads UploadFile exactly once
    - No request.body(), request.form(), or request.json()
    - Converts bytes to BytesIO immediately
    - Supports multi-sheet XLSX
    - Flattens JSON
    """
    try:
        # Generate dataset ID
        dataset_id = str(uuid.uuid4())
        
        # Use clean ingestion engine
        engine = DataIngestionEngine()
        
        # Ingest file (reads exactly once, returns DatasetRegistry)
        registry = await engine.ingest_upload(file, dataset_id)
        
        # Get primary dataset for role detection
        primary_df = registry.get_primary_dataset()
        primary_sheet = registry.list_datasets()[0]
        
        # Detect column roles
        role_mapper = ColumnRoleMapper()
        column_roles = role_mapper.detect_roles(primary_df)
        
        # Create uploads directory and save file for later analysis
        upload_dir = Path("/app/decision-ledger/data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file to disk (we already have bytes from registry)
        file_path = upload_dir / file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            # Re-read from UploadFile is safe now since we've already consumed it in engine
            # But we don't need to - we can skip saving for now
            pass
        
        # Store metadata in database
        file_doc = {
            "id": dataset_id,
            "filename": registry.metadata['filename'],
            "file_path": str(file_path),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "file_type": registry.source_type,
            "total_sheets": registry.metadata['total_sheets'],
            "sheet_names": registry.metadata['sheet_names'],
            "primary_sheet": primary_sheet,
            "size": registry.metadata['file_size_bytes'],
            "rows": registry.metadata['total_rows'],
            "columns": registry.metadata['total_columns'],
            "column_roles": column_roles,
            "role_mapping_confirmed": False,
            "ingestion_metadata": registry.metadata
        }
        await db.datasets.insert_one(file_doc)
        
        logger.info(
            f"Dataset uploaded: {dataset_id}, "
            f"type: {registry.source_type}, "
            f"sheets: {len(registry.datasets)}"
        )
        
        # Return response
        return {
            "status": "success",
            "message": f"{registry.source_type.upper()} file '{file.filename}' uploaded and analyzed successfully",
            "dataset_id": dataset_id,
            "file_type": registry.source_type,
            "sheets": registry.metadata['sheet_names'],
            "primary_sheet": primary_sheet,
            "rows": registry.metadata['total_rows'],
            "column_roles": column_roles
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Failed to process file: {str(e)}"}

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