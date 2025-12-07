# Api.py - Gemini-ready API wrapper for TMDB and Google Generative Language (Gemini)
import os
import logging
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict
import config  # نبقي عليه كخيار احتياطي

# --- Logging setup
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ==========================================
# منطقة تحميل المفاتيح (تم التعديل للقراءة المباشرة)
# ==========================================

# 1. محاولة قراءة المفاتيح مباشرة من بيئة السيرفر (Render) أولاً
# إذا لم نجدها، نحاول قراءتها من ملف config
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or getattr(config, "TMDB_API_KEY", None)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or getattr(config, "GEMINI_MODEL", "gemini-1.5-flash")

BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = getattr(config, "REQUEST_TIMEOUT", 10)

# طباعة رسالة تشخيصية في الـ Logs عند بدء التشغيل
if GEMINI_API_KEY:
    # نطبع أول 4 حروف فقط للأمان للتأكد من أنه قرأ المفتاح
    masked_key = GEMINI_API_KEY[:4] + "..."
    logger.info(f"✅ GEMINI_API_KEY Found: {masked_key} | Model: {GEMINI_MODEL}")
else:
    logger.error("❌ CRITICAL: GEMINI_API_KEY is Missing or Empty!")

# ==========================================

# --- Helpers for Gemini endpoint normalization and call

def _normalize_gemini_model(model: str) -> str:
    """
    Normalize model identifier so the final path contains exactly one 'models/' prefix.
    """
    if not model:
        return "models/gemini-1.5-flash"
    model = model.strip().strip("/")
    if model.startswith("models/"):
        return model
    return f"models/{model}"

def _call_gemini(prompt_text: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """
    Call Gemini REST generateContent endpoint.
    Updated to use the correct v1beta/v1 API structure (contents -> parts).
    """
    # التحقق مرة أخرى داخل الدالة
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    
    if not current_key:
        logger.error("Attempted to call Gemini but API Key is None")
        return "Error: Gemini API key not configured."
    
    normalized_model = _normalize_gemini_model(GEMINI_MODEL)
    
    # Correct Endpoint for Gemini
    url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:generateContent?key={current_key}"
    
    # Correct Payload Structure for Gemini
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if resp.status_code != 200:
            logger.error(f"Gemini API Error {resp.status_code}: {resp.text}")
            return f"Error: Gemini API returned status {resp.status_code}"
            
        data = resp.json()
        
        candidates = data.get("candidates")
        if candidates and isinstance(candidates, list):
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")
        
        return ""

    except Exception as e:
        logger.exception("Gemini call failed")
        return f"Error: {str(e)}"

# --- TMDB helpers

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
    """Fetch popular/discover movies or tv shows from TMDB."""
    if not TMDB_API_KEY:
        return []
    
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        if region and region in REGION_MAP:
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc{REGION_MAP[region]}"
        else:
            url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
            
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        logger.debug("fetch_content error: %s", e)
        return []

def search_tmdb(query: str, content_type: Optional[str] = None) -> List[Dict]:
    """Search TMDB multi or specific type."""
    if not TMDB_API_KEY or not query:
        return []
    
    try:
        q = requests.utils.quote(query)
        if content_type in ("movie", "tv"):
            url = f"{BASE_URL}/search/{content_type}?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        else:
            url = f"{BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
            
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        logger.debug("search_tmdb error: %s", e)
        return []

def get_trailer(item_id: int, content_type: str = "movie") -> Optional[str]:
    """Return YouTube key for trailer if available."""
    if not TMDB_API_KEY:
        return None
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/videos?api_key={TMDB_API_KEY}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        for v in resp.json().get("results", []):
            if v.get("type") == "Trailer" and v.get("site") == "YouTube":
                return v.get("key")
    except Exception as e:
        logger.debug("get_trailer error: %s", e)
    return None

def get_watch_providers(item_id: int, content_type: str = "movie") -> List[Dict]:
    """Return list of providers for Saudi Arabia (SA) if present."""
    if not TMDB_API_KEY:
        return []
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/watch/providers?api_key={TMDB_API_KEY}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("results", {})
        sa = data.get("SA") or data.get("sa")
        if sa:
            return sa.get("flatrate", []) or sa.get("rent", []) or sa.get("buy", [])
    except Exception as e:
        logger.debug("get_watch_providers error: %s", e)
    return []

# --- AI functions using Gemini

def get_lang_instruction(lang: str) -> str:
    if lang == "en":
        return "Speak ONLY in English."
    if lang == "de":
        return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

PERSONAS_MAP = {
    "Friendly": "You are CimaBot, a helpful movie consultant.",
    "Critic": "You are a snobbish critic. Hate blockbusters.",
    "Joker": "You are a comedian bot. Make jokes.",
    "Fanboy": "You are a hyped geek! Use emojis."
}

def _resolve_persona_key(persona: str) -> str:
    p = (persona or "").lower()
    if any(x in p for x in ["critic", "kritiker"]):
        return "Critic"
    if any(x in p for x in ["joker", "jok"]):
        return "Joker"
    if any(x in p for x in ["fanboy", "wasis", "fan"]):
        return "Fanboy"
    return "Friendly"

def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    """
    Build a single prompt text from messages and persona, then call Gemini.
    """
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not current_key:
        return "Error: Gemini API key not configured."
    
    lang_rule = get_lang_instruction(lang)
    p_key = _resolve_persona_key(persona)
    
    sys_prompt = (
        f"{PERSONAS_MAP.get(p_key, PERSONAS_MAP['Friendly'])} RULES: 1. {lang_rule} "
        "2. Movie Titles MUST be in English inside [Brackets] e.g. [Inception]. 3. No Asian scripts."
    )
    
    prompt_parts = [sys_prompt, "\n--- Conversation ---\n"]
    for m in messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        prompt_parts.append(f"{role.upper()}: {content}\n")
    
    prompt_parts.append("\nAssistant:")
    prompt_text = "\n".join(prompt_parts)
    
    return _call_gemini(prompt_text, temperature=0.7, max_tokens=500)

def analyze_image_search(image_file, lang: str = "ar") -> str:
    """
    Encode image as base64 and include in prompt using Gemini Vision (multimodal).
    """
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not current_key:
        return "Error: Gemini API key not configured."
    
    try:
        # Read file and encode to base64
        image_data = image_file.read()
        b64 = base64.b64encode(image_data).decode("utf-8")
        image_file.seek(0)  # Reset cursor
    except Exception as e:
        return f"Error reading image: {e}"
    
    lang_rule = get_lang_instruction(lang)
    user_prompt = (
        f"Analyze the mood of the following image and recommend 3 movies. {lang_rule} "
        "Return titles inside [Brackets]. Provide a short explanation and 3 recommendations."
    )
    
    normalized_model = _normalize_gemini_model(GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:generateContent?key={current_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": user_prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 500
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=45)
        if resp.status_code != 200:
            logger.error(f"Gemini Vision Error {resp.status_code}: {resp.text}")
            return "Error analyzing image."
            
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return "No results found."
        
    except Exception as e:
        logger.exception("Gemini vision call failed")
        return f"Error: {e}"

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not current_key:
        return "Error: Gemini API key not configured."
    
    valid_movies = [m for m in movies if m]
    if not valid_movies:
        return "Please enter at least one movie."

    lang_rule = get_lang_instruction(lang)
    prompt = (
        f"User likes: {', '.join(valid_movies)}. Analyze personality and suggest 3 NEW movies. "
        f"{lang_rule} Titles in [Brackets]."
    )
    return _call_gemini(prompt, temperature=0.7, max_tokens=400)

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    current_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not current_key:
        return "Error: Gemini API key not configured."
        
    lang_rule = get_lang_instruction(lang)
    prompt = (
        f"Matchmaker: Person A likes {u1}. Person B likes {u2}. Find middle ground movies. "
        f"{lang_rule} Titles in [Brackets]."
    )
    return _call_gemini(prompt, temperature=0.7, max_tokens=400)
