# Api.py - Gemini-ready API wrapper for TMDB and Google Generative Language (Gemini)
import os
import logging
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict
import config  # نبقي عليه للمتغيرات الأخرى فقط

# --- Logging setup
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ==========================================
# منطقة تحميل الإعدادات (تم الإصلاح لمنع خطأ 404)
# ==========================================

# قراءة مفتاح Gemini من بيئة Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)

# تعديل هام: تجاهل config.py في اسم الموديل واستخدام gemini-1.5-flash مباشرة كافتراضي
# هذا يحل مشكلة الخطأ 404 الناتجة عن استخدام gemini-1.0 القديم
GEMINI_MODEL = os.environ.get("GEMINI_MODEL")
if not GEMINI_MODEL:
    GEMINI_MODEL = "gemini-1.5-flash"

# TMDB Settings
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or getattr(config, "TMDB_API_KEY", None)
BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = getattr(config, "REQUEST_TIMEOUT", 10)

# طباعة رسالة تشخيصية في الـ Logs
if GEMINI_API_KEY:
    masked_key = GEMINI_API_KEY[:5] + "..."
    logger.info(f"✅ API Key Loaded: {masked_key} | Using Model: {GEMINI_MODEL}")
else:
    logger.error("❌ CRITICAL: GEMINI_API_KEY is Missing!")

# ==========================================

def _normalize_gemini_model(model: str) -> str:
    """Normalize model identifier."""
    # تنظيف الاسم لضمان عدم وجود أخطاء
    if not model: 
        return "models/gemini-1.5-flash"
    
    clean_model = model.strip().strip("/")
    if clean_model.startswith("models/"):
        return clean_model
    return f"models/{clean_model}"

def _call_gemini(prompt_text: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """Call Gemini REST API (v1beta)."""
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not current_key:
        return "Error: Gemini API key not configured."
    
    normalized_model = _normalize_gemini_model(GEMINI_MODEL)
    
    # Endpoint الصحيح لـ Gemini 1.5
    url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:generateContent?key={current_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # التعامل مع الأخطاء وتوضيح السبب
        if resp.status_code != 200:
            error_msg = f"Gemini Error {resp.status_code}: {resp.text}"
            logger.error(error_msg)
            if resp.status_code == 404:
                return "Error: Model not found (404). Please check GEMINI_MODEL setting."
            return f"Error connecting to AI ({resp.status_code})"
            
        data = resp.json()
        candidates = data.get("candidates")
        if candidates and isinstance(candidates, list):
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""

    except Exception as e:
        logger.exception("Gemini call failed")
        return "Error: Failed to contact AI server."

# --- TMDB helpers ---
REGION_MAP = {
    "korea": "&with_original_language=ko",
    "india": "&with_original_language=hi",
    "arabic": "&with_original_language=ar",
    "turkey": "&with_original_language=tr",
    "spain": "&with_original_language=es",
    "japan": "&with_original_language=ja&with_genres=16",
}

@lru_cache(maxsize=128)
def fetch_content(content_type: str = "movie", category: str = "popular", region: Optional[str] = None) -> List[Dict]:
    if not TMDB_API_KEY: return []
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        if region and region in REGION_MAP:
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc{REGION_MAP[region]}"
        else:
            url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except: return []

def search_tmdb(query: str, content_type: Optional[str] = None) -> List[Dict]:
    if not TMDB_API_KEY or not query: return []
    try:
        q = requests.utils.quote(query)
        if content_type in ("movie", "tv"):
            url = f"{BASE_URL}/search/{content_type}?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        else:
            url = f"{BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except: return []

def get_trailer(item_id: int, content_type: str = "movie") -> Optional[str]:
    if not TMDB_API_KEY: return None
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/videos?api_key={TMDB_API_KEY}"
        resp = requests.get(url, timeout=5); resp.raise_for_status()
        for v in resp.json().get("results", []):
            if v.get("type") == "Trailer" and v.get("site") == "YouTube": return v.get("key")
    except: return None

def get_watch_providers(item_id: int, content_type: str = "movie") -> List[Dict]:
    if not TMDB_API_KEY: return []
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/watch/providers?api_key={TMDB_API_KEY}"
        resp = requests.get(url, timeout=5); resp.raise_for_status()
        data = resp.json().get("results", {})
        sa = data.get("SA") or data.get("sa")
        if sa: return sa.get("flatrate", []) or sa.get("rent", []) or sa.get("buy", [])
    except: return []

# --- AI Helper Functions ---

def get_lang_instruction(lang: str) -> str:
    if lang == "en": return "Speak ONLY in English."
    if lang == "de": return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

PERSONAS_MAP = {
    "Friendly": "You are CimaBot, a helpful movie consultant.",
    "Critic": "You are a snobbish critic. Hate blockbusters.",
    "Joker": "You are a comedian bot. Make jokes.",
    "Fanboy": "You are a hyped geek! Use emojis."
}

def _resolve_persona_key(persona: str) -> str:
    p = (persona or "").lower()
    if "critic" in p: return "Critic"
    if "joker" in p: return "Joker"
    if "fan" in p: return "Fanboy"
    return "Friendly"

def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    lang_rule = get_lang_instruction(lang)
    p_key = _resolve_persona_key(persona)
    sys_prompt = f"{PERSONAS_MAP.get(p_key)} RULES: 1. {lang_rule} 2. Movie Titles MUST be in English inside [Brackets]. 3. No Asian scripts."
    
    prompt_parts = [sys_prompt, "\n--- Conversation ---\n"]
    for m in messages or []:
        prompt_parts.append(f"{m.get('role','user').upper()}: {m.get('content','')}\n")
    prompt_parts.append("\nAssistant:")
    
    return _call_gemini("\n".join(prompt_parts))

def analyze_image_search(image_file, lang: str = "ar") -> str:
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not current_key: return "Error: Gemini API key not configured."
    
    try:
        image_data = image_file.read()
        b64 = base64.b64encode(image_data).decode("utf-8")
        image_file.seek(0)
    except: return "Error reading image."
    
    normalized_model = _normalize_gemini_model(GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:generateContent?key={current_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": f"Analyze mood and suggest 3 movies. {get_lang_instruction(lang)} Titles in [Brackets]."},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
            ]
        }],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 500}
    }
    
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
        if resp.status_code == 200:
            return resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No results.")
        return f"Error analyzing image ({resp.status_code})"
    except Exception as e: return f"Error: {e}"

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    valid = [m for m in movies if m]
    if not valid: return "Please enter movies."
    return _call_gemini(f"User likes: {', '.join(valid)}. Analyze personality and suggest 3 NEW movies. {get_lang_instruction(lang)} Titles in [Brackets].")

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    return _call_gemini(f"Matchmaker: A likes {u1}, B likes {u2}. Suggest middle ground movies. {get_lang_instruction(lang)} Titles in [Brackets].")
