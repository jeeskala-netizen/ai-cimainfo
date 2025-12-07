# Api.py - Exclusive OpenRouter Version (Clean & Stable)
import os
import logging
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict
import config

# --- 1. إعداد السجلات (Logging) ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- 2. تحميل المفاتيح (OpenRouter + TMDB فقط) ---
# محاولة القراءة من Render مباشرة، ثم من ملف config كاحتياط
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or getattr(config, "TMDB_API_KEY", None)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# التحقق من وجود المفتاح عند تشغيل السيرفر
if OPENROUTER_API_KEY:
    logger.info("✅ OpenRouter API Key is configured and ready.")
else:
    logger.error("❌ CRITICAL ERROR: OPENROUTER_API_KEY is missing in Render Environment Variables!")

# إعدادات TMDB
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"
REQUEST_TIMEOUT = 10

# --- 3. دالة الاتصال الموحدة (OpenRouter Only) ---

def _call_openrouter(messages: List[Dict], temperature: float = 0.7) -> str:
    """
    تقوم هذه الدالة بإرسال الطلبات حصرياً إلى OpenRouter.
    """
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY is missing. Please add it in Render settings."

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://ai-cimainfo.onrender.com", # مطلوب من OpenRouter
        "X-Title": "CimaBot",
        "Content-Type": "application/json"
    }

    # نستخدم موديل Gemini Flash عبر OpenRouter لأنه سريع ويدعم العربية بطلاقة
    # الموديل: google/gemini-flash-1.5
    payload = {
        "model": "google/gemini-flash-1.5",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 800
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        
        if resp.status_code == 200:
            data = resp.json()
            # استخراج النص من استجابة OpenRouter (تشبه استجابة OpenAI)
            return data['choices'][0]['message']['content']
        else:
            logger.error(f"OpenRouter API Error {resp.status_code}: {resp.text}")
            return f"Error form AI Provider: {resp.status_code}"
            
    except Exception as e:
        logger.error(f"Connection Exception: {e}")
        return "Error: Failed to connect to AI server."

# --- 4. دوال التحليل (صور، شات، شخصية) ---

def get_lang_instruction(lang: str) -> str:
    if lang == "en": return "Speak ONLY in English."
    if lang == "de": return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    """تجهيز المحادثة وإرسالها"""
    lang_rule = get_lang_instruction(lang)
    
    # تحديد الشخصية
    sys_msg = "You are CimaBot, a helpful movie expert."
    p = (persona or "").lower()
    if "critic" in p: sys_msg = "You are a snobbish movie critic. You hate blockbusters."
    elif "joker" in p: sys_msg = "You are a funny bot. Make jokes about movies."
    elif "fan" in p: sys_msg = "You are a hyped fanboy! Use emojis! 🤩"
    
    # التعليمات للنظام (System Prompt)
    system_prompt = f"{sys_msg} RULES: 1. {lang_rule} 2. Movie titles MUST be in English inside [Brackets] like [Inception]. 3. Be concise."
    
    # تكوين قائمة الرسائل
    formatted_msgs = [{"role": "system", "content": system_prompt}]
    for m in messages:
        # التأكد من أن الرسالة تحتوي على نص فقط
        formatted_msgs.append({"role": m.get("role", "user"), "content": str(m.get("content", ""))})
        
    return _call_openrouter(formatted_msgs)

def analyze_image_search(image_file, lang: str = "ar") -> str:
    """تحليل الصور باستخدام OpenRouter Vision"""
    if not OPENROUTER_API_KEY:
        return "Error: API Key missing."
        
    try:
        # تحويل الصورة إلى Base64
        img_data = base64.b64encode(image_file.read()).decode('utf-8')
        image_file.seek(0) # إعادة المؤشر لبداية الملف
        
        prompt = f"Analyze the mood of this image and recommend 3 movies. {get_lang_instruction(lang)} Titles in [Brackets]."
        
        # رسالة خاصة للصور (Multimodal)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                    }
                ]
            }
        ]
        return _call_openrouter(messages)
            
    except Exception as e:
        logger.error(f"Image Processing Error: {e}")
        return "Error analyzing image."

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    valid = [m for m in movies if m]
    if not valid: return "Please enter movies."
    prompt = f"User likes: {', '.join(valid)}. Analyze personality and suggest 3 NEW movies. {get_lang_instruction(lang)} Titles in [Brackets]."
    return _call_openrouter([{"role": "user", "content": prompt}])

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    prompt = f"Matchmaker: Person A likes {u1}. Person B likes {u2}. Find middle ground movies. {get_lang_instruction(lang)} Titles in [Brackets]."
    return _call_openrouter([{"role": "user", "content": prompt}])

# --- 5. دوال TMDB (ثابتة ولم تتغير) ---

@lru_cache(maxsize=128)
def fetch_content(content_type="movie", category="popular", region=None):
    if not TMDB_API_KEY: return []
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
        if region:
            r_map = {"korea": "ko", "india": "hi", "arabic": "ar", "turkey": "tr", "spain": "es", "japan": "ja"}
            lang = r_map.get(region, "en")
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc&with_original_language={lang}"
        
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        return resp.json().get("results", []) if resp.status_code == 200 else []
    except: return []

def search_tmdb(query, content_type=None):
    if not TMDB_API_KEY or not query: return []
    try:
        q = requests.utils.quote(query)
        endpoint = f"search/{content_type}" if content_type in ["movie", "tv"] else "search/multi"
        url = f"{BASE_URL}/{endpoint}?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        return resp.json().get("results", []) if resp.status_code == 200 else []
    except: return []

def get_trailer(item_id, content_type="movie"):
    if not TMDB_API_KEY: return None
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/videos?api_key={TMDB_API_KEY}"
        res = requests.get(url, timeout=5).json()
        for v in res.get("results", []):
            if v.get("type") == "Trailer" and v.get("site") == "YouTube": return v.get("key")
    except: pass
    return None

def get_watch_providers(item_id, content_type="movie"):
    if not TMDB_API_KEY: return []
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/watch/providers?api_key={TMDB_API_KEY}"
        res = requests.get(url, timeout=5).json()
        return res.get("results", {}).get("SA", {}).get("flatrate", [])
    except: return []
