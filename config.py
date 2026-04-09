"""Configuration module for AI Agent"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Centralized configuration"""
    
    # OpenRouter Settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    MODEL = os.getenv("MODEL", "openai/gpt-4o-mini")  # Cheap & fast
    
    # Database
    DB_DIR = Path("./data")
    DB_PATH = DB_DIR / "knowledge_base.db"
    
    # Logging
    LOG_DIR = Path("./logs")
    LOG_FILE = LOG_DIR / "agent.log"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Agent Settings
    MAX_TOOL_ROUNDS = 5        # Prevent infinite loops
    TEMPERATURE = 0.1          # Low temp for deterministic tool calls
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("❌ OPENROUTER_API_KEY not set in .env")
        return True
