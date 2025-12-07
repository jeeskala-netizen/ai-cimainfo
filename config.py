# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Keys
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") # المفتاح الجديد
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # احتياطي

# Settings
BASE_URL = os.getenv("BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = os.getenv("IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = 10
