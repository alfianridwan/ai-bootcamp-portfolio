import os
import sys
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
DB_NAME = os.getenv("DB_NAME", "review_history.db")

if not GEMINI_API_KEY:
    print("Configuration Error: GEMINI_API_KEY environment variable is missing!")
    sys.exit(1)
