import os
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env (يعمل فقط على جهازك المحلي)
load_dotenv()

# قراءة المفاتيح من متغيرات البيئة (الآمنة)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_URL = "https://image.tmdb.org/t/p/original"


if not TMDB_API_KEY or not GROQ_API_KEY:
    print("⚠️ تحذير: لم يتم العثور على مفاتيح API. تأكد من إعداد ملف .env أو Environment Variables.")
