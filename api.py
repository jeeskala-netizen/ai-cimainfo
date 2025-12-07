# Api.py - Optimized for OpenRouter with Fallback
import os
import logging
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict
import config

# --- Logging setup
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- Configuration & Keys
# قراءة المفاتيح من بيئة العمل (Render) أو ملف config
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or getattr(config, "TMDB_API_KEY", None)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)

# إعدادات TMDB
BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = 10

# --- AI Core Functions (OpenRouter Priority) ---

def _call_ai_service(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 500) -> str:
    """
    الدالة المركزية للاتصال بالذكاء الاصطناعي.
    الأولوية: OpenRouter -> ثم Gemini Direct
    """
    
    # 1. محاولة استخدام OpenRouter (الخيار الأفضل والمستقر)
    if OPENROUTER_API_KEY:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://ai-cimainfo.onrender.com",
                "X-Title": "CimaBot",
                "Content-Type": "application/json"
            }
            
            # نستخدم موديل Gemini Flash عبر OpenRouter لأنه سريع ورخيص/مجاني
            # يمكنك تغييره إلى "meta-llama/llama-3-8b-instruct:free" إذا أردت
            payload = {
                "model": "google/gemini-flash-1.5",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=25)
            
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            else:
                logger.error(f"OpenRouter Error {resp.status_code}: {resp.text}")
                # لا نوقف التنفيذ، بل نحاول الانتقال للخيار الاحتياطي
        except Exception as e:
            logger.error(f"OpenRouter Connection Failed: {e}")

    # 2. الخيار الاحتياطي: استخدام Gemini Google API مباشرة
    if GEMINI_API_KEY:
        logger.info("Falling back to Direct Gemini API...")
        return _fallback_gemini_direct(messages, temperature)

    return "Error: AI configuration missing. Please set OPENROUTER_API_KEY."

def _fallback_gemini_direct(messages: List[Dict], temperature: float) -> str:
    """نسخة مبسطة للاتصال المباشر بجوجل في حال فشل OpenRouter"""
    try:
        # تحويل صيغة الرسائل إلى نص بسيط لأن API جوجل المباشر معقد في السياق
        prompt_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        # استخدام موديل Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": temperature}
        }
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        
        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Fallback Gemini Error: {e}")
    
    return "Error: All AI services failed."

# --- Helper Functions (TMDB) - (لم تتغير لأنها سليمة) ---

@lru_cache(maxsize=128)
def fetch_content(content_type="movie", category="popular", region=None):
    if not TMDB_API_KEY: return []
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
        if region:
            # خريطة بسيطة للمناطق
            r_map = {"korea": "ko", "india": "hi", "arabic": "ar", "turkey": "tr", "spain": "es", "japan": "ja"}
            lang_code = r_map.get(region, "en")
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc&with_original_language={lang_code}"
        
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        return resp.json().get("results", []) if resp.status_code == 200 else []
    except Exception as e:
        logger.error(f"TMDB Fetch Error: {e}")
        return []

def search_tmdb(query, content_type=None):
    if not TMDB_API_KEY or not query: return []
    try:
        q = requests.utils.quote(query)
        endpoint = f"search/{content_type}" if content_type in ["movie", "tv"] else "search/multi"
        url = f"{BASE_URL}/{endpoint}?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        return resp.json().get("results", []) if resp.status_code == 200 else []
    except Exception: return []

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

# --- AI Logic Wrappers (Chat, Image, DNA) ---

def get_lang_instruction(lang: str) -> str:
    if lang == "en": return "Speak ONLY in English."
    if lang == "de": return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    lang_rule = get_lang_instruction(lang)
    
    # تحديد الشخصية
    system_instruction = "You are a helpful movie assistant."
    p_lower = (persona or "").lower()
    if "critic" in p_lower: system_instruction = "You are a snobbish movie critic. You hate cliche movies."
    elif "joker" in p_lower: system_instruction = "You are a funny comedian bot. Make jokes about movies."
    elif "fan" in p_lower: system_instruction = "You are a hyped fanboy! Use lots of emojis!"
    
    system_content = f"{system_instruction} RULES: 1. {lang_rule} 2. Movie Titles MUST be in English inside [Brackets] like [The Matrix]. 3. Be concise."

    # بناء قائمة الرسائل لـ OpenRouter
    # نضع تعليمات النظام أولاً
    full_messages = [{"role": "system", "content": system_content}]
    
    # نضيف تاريخ المحادثة
    for m in messages or []:
        full_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        
    return _call_ai_service(full_messages)

def analyze_image_search(image_file, lang: str = "ar") -> str:
    """
    تحليل الصور باستخدام OpenRouter Vision.
    """
    if not OPENROUTER_API_KEY and not GEMINI_API_KEY:
        return "Error: AI keys missing."

    try:
        # تجهيز الصورة كـ Base64
        image_data = image_file.read()
        b64_image = base64.b64encode(image_data).decode('utf-8')
        image_file.seek(0)
        
        prompt = f"Analyze the mood of this image and recommend 3 movies that fit this mood. {get_lang_instruction(lang)}. Return titles in [Brackets]."
        
        # هيكلية الرسالة للصور (OpenAI Vision Compatible)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
                    }
                ]
            }
        ]
        
        return _call_ai_service(messages)
        
    except Exception as e:
        logger.error(f"Image Analysis Error: {e}")
        return "Error processing image."

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    valid_movies = [m for m in movies if m]
    if not valid_movies: return "Please enter at least one movie."
    
    prompt = f"User likes: {', '.join(valid_movies)}. Analyze their personality based on these movies and suggest 3 NEW recommendations. {get_lang_instruction(lang)}. Titles in [Brackets]."
    
    return _call_ai_service([{"role": "user", "content": prompt}])

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    prompt = f"Matchmaker: Person A likes {u1}. Person B likes {u2}. Find 3 middle-ground movies they both might like. {get_lang_instruction(lang)}. Titles in [Brackets]."
    return _call_ai_service([{"role": "user", "content": prompt}])
