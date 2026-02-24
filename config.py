"""
Configuration settings for the Roadside Assistance Agent
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Data paths
DATA_DIR = BASE_DIR / "data"
POLICY_COVERAGE_FILE = DATA_DIR / "policy_coverage.json"
GARAGES_FILE = DATA_DIR / "garages.json"
CASES_FILE = DATA_DIR / "cases.json"

# Prompt paths
PROMPTS_DIR = BASE_DIR / "prompts"
SYSTEM_INSTRUCTION_FILE = PROMPTS_DIR / "system_instruction.txt"

# Static files
STATIC_DIR = BASE_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"

# API Configuration
API_HOST = "127.0.0.1"
API_PORT = 8000
BACKEND_URL = f"http://{API_HOST}:{API_PORT}"

# Model Configuration
MODEL_NAME = "gemini-2.5-flash"
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Server Configuration
CORS_ORIGINS = ["*"]  # In production, specify exact origins
