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
from core.ingestion import DataIngestion
from core.schema_detector import SchemaDetector
from core.role_mapper import ColumnRoleMapper
from models.baseline_model import BaselineModel
from models.roi_curve import ROICurve
from models.scenario_simulator import ScenarioSimulator


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

@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Decision Ledger"}

@api_router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload CSV dataset for analysis."""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("/app/decision-ledger/data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / file.filename
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Process CSV and detect roles
        ingestion = DataIngestion()
        role_mapper = ColumnRoleMapper()
        
        # Load CSV
        df = await ingestion.ingest_csv(str(file_path))
        
        # Detect column roles
        column_roles = role_mapper.detect_roles(df)
        
        # Store metadata in database
        file_doc = {
            "id": str(uuid.uuid4()),
            "filename": file.filename,
            "file_path": str(file_path),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size": len(content),
            "rows": len(df),
            "column_roles": column_roles,
            "role_mapping_confirmed": False
        }
        await db.datasets.insert_one(file_doc)
        
        # Return response
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded and analyzed successfully",
            "dataset_id": file_doc["id"],
            "rows": len(df),
            "column_roles": column_roles
        }
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@api_router.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint for decision reasoning."""
    # Placeholder implementation - just echo for now
    chat_response = {
        "status": "success",
        "response": f"Received your message: '{request.message}'. Full LLM integration coming soon!",
        "session_id": request.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Store chat message
    await db.chat_messages.insert_one({
        "session_id": request.session_id,
        "user_message": request.message,
        "bot_response": chat_response["response"],
        "timestamp": chat_response["timestamp"]
    })
    
    return chat_response

@api_router.post("/forecast")
async def generate_forecast(request: ForecastRequest):
    """Generate forecast for uploaded dataset."""
    try:
        # Get dataset from database
        dataset = await db.datasets.find_one({"id": request.dataset_id}, {"_id": 0})
        
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}
        
        file_path = dataset["file_path"]
        detected_schema = dataset["detected_schema"]
        
        # Check if we have required columns
        if not detected_schema.get("spend") or not detected_schema.get("revenue"):
            return {
                "status": "error",
                "message": "Required columns (spend and revenue) not detected in dataset"
            }
        
        # Load data
        ingestion = DataIngestion()
        df = await ingestion.ingest_csv(file_path)
        
        # Get column names
        date_col = detected_schema.get("date")
        spend_col = detected_schema["spend"]
        revenue_col = detected_schema["revenue"]
        
        # Convert date column if detected
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(by=date_col)
        
        # Train baseline model
        baseline_model = BaselineModel()
        results = baseline_model.train_spend_revenue_model(df, spend_col, revenue_col)
        
        # Store forecast in database
        forecast_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "model_type": "baseline_regression",
            "created_at": datetime.now(timezone.utc).isoformat(),
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
        
        file_path = dataset["file_path"]
        detected_schema = dataset["detected_schema"]
        
        # Check if we have required columns
        if not detected_schema.get("spend") or not detected_schema.get("revenue"):
            return {
                "status": "error",
                "message": "Required columns (spend and revenue) not detected in dataset"
            }
        
        # Load data
        ingestion = DataIngestion()
        df = await ingestion.ingest_csv(file_path)
        
        # Get column names
        spend_col = detected_schema["spend"]
        revenue_col = detected_schema["revenue"]
        
        # Fit ROI curve models
        roi_curve = ROICurve()
        results = roi_curve.fit_roi_models(df, spend_col, revenue_col)
        
        # Store ROI analysis in database
        roi_doc = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "analysis_type": "roi_curve",
            "created_at": datetime.now(timezone.utc).isoformat(),
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