# Api.py - واجهة للتعامل مع TMDB و Groq (مُنقّحة)
import os
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict

# حاول استيراد مكتبة Groq فقط إذا كانت متاحة
try:
    from groq import Groq
except Exception:
    Groq = None

import config  # ملف الإعدادات: ضع فيه مفاتيح API وURLs

# إعداد عميل Groq بأمان
client = None
if Groq and getattr(config, "GROQ_API_KEY", None):
    try:
        client = Groq(api_key=config.GROQ_API_KEY)
    except Exception as e:
        client = None
        print(f"Groq init error: {e}")
else:
    print("Warning: GROQ API key missing or Groq library not installed.")

# --- إعدادات TMDB ---
TMDB_API_KEY = getattr(config, "TMDB_API_KEY", None)
BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")

# خريطة للغات/مناطق خاصة
REGION_MAP = {
    "korea": "&with_original_language=ko",
    "india": "&with_original_language=hi",
    "arabic": "&with_original_language=ar",
    "turkey": "&with_original_language=tr",
    "spain": "&with_original_language=es",
    "japan": "&with_original_language=ja&with_genres=16",
}

# --- وظائف TMDB مع مهلات ومعالجة أخطاء محسنة ---
@lru_cache(maxsize=128)
def fetch_content(content_type: str = "movie", category: str = "popular", region: Optional[str] = None) -> List[Dict]:
    """Fetch popular/discover movies or tv shows. Returns list of results."""
    if not TMDB_API_KEY:
        return []
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        if region and region in REGION_MAP:
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc{REGION_MAP[region]}"
        else:
            url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []

def search_tmdb(query: str, content_type: Optional[str] = None) -> List[Dict]:
    """Search TMDB multi or specific type."""
    if not TMDB_API_KEY or not query:
        return []
    try:
        if content_type in ("movie", "tv"):
            url = f"{BASE_URL}/search/{content_type}?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}&language=ar-SA"
        else:
            url = f"{BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}&language=ar-SA"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
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
    except Exception:
        pass
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
        sa = data.get("SA") or data.get("sa")  # be tolerant
        if sa:
            return sa.get("flatrate", []) or sa.get("rent", []) or sa.get("buy", [])
    except Exception:
        pass
    return []

# --- وظائف AI (Groq) مع تعليمات اللغة والشخصية ---
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
    """Send chat messages to Groq client with system prompt formatting."""
    if not client:
        return "Error: AI client not configured."
    lang_rule = get_lang_instruction(lang)
    p_key = _resolve_persona_key(persona)
    sys_prompt = f"{PERSONAS_MAP[p_key]} RULES: 1. {lang_rule} 2. Movie Titles MUST be in English inside [Brackets] e.g. [Inception]. 3. No Asian scripts."
    # Build messages safely
    full = [{"role": "system", "content": sys_prompt}] + (messages or [])
    try:
        resp = client.chat.completions.create(messages=full, model="llama-3.3-70b-versatile", temperature=0.7)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def analyze_image_search(image_file, lang: str = "ar") -> str:
    """Send image (file-like) to Groq for analysis. Returns text response."""
    if not client:
        return "Error: AI client not configured."
    try:
        b64 = base64.b64encode(image_file.read()).decode("utf-8")
        image_file.seek(0)
        lang_rule = get_lang_instruction(lang)
        prompt = f"Analyze image mood. Recommend 3 movies. {lang_rule}. Titles in [Brackets]."
        # Use vision-capable model if available
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt},
                                                   {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
            model="llama-3.2-90b-vision-preview",
            temperature=0.6,
            max_tokens=500
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    if not client:
        return "Error: AI client not configured."
    lang_rule = get_lang_instruction(lang)
    prompt = f"User likes: {', '.join([m for m in movies if m])}. Analyze personality. Suggest 3 NEW movies. {lang_rule}. Titles in [Brackets]."
    try:
        resp = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.7)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    if not client:
        return "Error: AI client not configured."
    lang_rule = get_lang_instruction(lang)
    prompt = f"Matchmaker: Person A likes {u1}, Person B likes {u2}. Find middle ground movies. {lang_rule}. Titles in [Brackets]."
    try:
        resp = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.7)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"
