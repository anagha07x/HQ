"""Configuration settings for Decision Ledger."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""
    
    # Database
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "decision_ledger")
    
    # LLM
    EMERGENT_LLM_KEY: str = os.getenv("EMERGENT_LLM_KEY", "")
    
    # File upload
    UPLOAD_DIR: str = "data/uploads"
    PROCESSED_DIR: str = "data/processed"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Model settings
    FORECAST_HORIZON: int = 30  # days
    CONFIDENCE_INTERVAL: float = 0.95
    

settings = Settings()
