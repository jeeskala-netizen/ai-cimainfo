import os
from dotenv import load_dotenv

# تحميل البيئة المحلية (Local)
load_dotenv()

# قراءة المفاتيح (مع التحقق)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# روابط النظام
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_URL = "https://image.tmdb.org/t/p/original"

# التحقق الأمني
if not TMDB_API_KEY:
    print("⚠️ CRITICAL: TMDB_API_KEY is missing!")
if not GROQ_API_KEY:
    print("⚠️ CRITICAL: GROQ_API_KEY is missing!")
