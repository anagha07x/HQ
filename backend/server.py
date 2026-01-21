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
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import aiofiles
from core.ingestion import DataIngestion
from core.schema_detector import SchemaDetector


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
        
        # Process CSV and detect schema
        ingestion = DataIngestion()
        schema_detector = SchemaDetector()
        
        # Load CSV
        df = await ingestion.ingest_csv(str(file_path))
        
        # Detect schema
        schema = schema_detector.detect_schema(df)
        
        # Store metadata in database
        file_doc = {
            "id": str(uuid.uuid4()),
            "filename": file.filename,
            "file_path": str(file_path),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size": len(content),
            "rows": schema["rows"],
            "columns": schema["columns"],
            "detected_schema": {
                "date": schema["date_column"],
                "spend": schema["spend_column"],
                "revenue": schema["revenue_column"]
            }
        }
        await db.datasets.insert_one(file_doc)
        
        # Return response
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded and analyzed successfully",
            "dataset_id": file_doc["id"],
            "columns": schema["columns"],
            "detected_schema": {
                "date": schema["date_column"],
                "spend": schema["spend_column"],
                "revenue": schema["revenue_column"]
            },
            "rows": schema["rows"]
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
    # Placeholder implementation
    return {
        "status": "success",
        "message": "Forecast generation coming soon!",
        "dataset_id": request.dataset_id,
        "horizon": request.horizon
    }

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