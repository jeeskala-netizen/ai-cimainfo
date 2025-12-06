# config.py - إعدادات المشروع مع دعم Gemini API
import os
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

BASE_URL = os.getenv("BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = os.getenv("IMAGE_URL", "https://image.tmdb.org/t/p/w500")
BACKDROP_URL = os.getenv("BACKDROP_URL", "https://image.tmdb.org/t/p/original")

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ar-SA")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))

if not TMDB_API_KEY:
    print("⚠️ CRITICAL: TMDB_API_KEY is missing!")
if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY is missing. AI features will be disabled or fallback will be used.")
if not GROQ_API_KEY:
    print("ℹ️ GROQ_API_KEY not found (optional).")
