# config.py - إعدادات المشروع مع دعم Gemini API
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env محلي إن وُجد
load_dotenv()

# مفاتيح API
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # مفتاح Gemini الجديد
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.0")  # نموذج افتراضي قابل للتعديل

# (احتفظنا بالمفتاح القديم كخيار احتياطي إن رغبت)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# روابط TMDB
BASE_URL = os.getenv("BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = os.getenv("IMAGE_URL", "https://image.tmdb.org/t/p/w500")
BACKDROP_URL = os.getenv("BACKDROP_URL", "https://image.tmdb.org/t/p/original")

# إعدادات عامة قابلة للتعديل
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ar-SA")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))

# تحققات أمنية وتنبيهات مفيدة أثناء التطوير
if not TMDB_API_KEY:
    print("⚠️ CRITICAL: TMDB_API_KEY is missing!")
if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY is missing. AI features will be disabled or fallback will be used.")
if not GROQ_API_KEY:
    print("ℹ️ GROQ_API_KEY not found (optional).")
