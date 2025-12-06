# Api.py - Gemini edition (استبدال Groq بـ Gemini REST)
import os
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict

import config  # تأكد أن config يحتوي على GEMINI_API_KEY و GEMINI_MODEL أو ضعهم كمتغيرات بيئة

# TMDB settings
TMDB_API_KEY = getattr(config, "TMDB_API_KEY", None)
BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")

# Gemini settings
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", None)
GEMINI_MODEL = getattr(config, "GEMINI_MODEL", "models/gemini-1.0")
GEMINI_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta2/models/{model}:generate?key={api_key}"

# Helper to call Gemini generate endpoint
def _call_gemini(prompt_text: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        return "Error: Gemini API key or model not configured."
    url = GEMINI_ENDPOINT_TEMPLATE.format(model=GEMINI_MODEL, api_key=GEMINI_API_KEY)
    payload = {
        "prompt": {"text": prompt_text},
        "temperature": temperature,
        "maxOutputTokens": max_tokens
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # استخرج النص من الاستجابة بأكثر الطرق احتمالاً
        if "candidates" in data and isinstance(data["candidates"], list) and len(data["candidates"]) > 0:
            cand = data["candidates"][0]
            # قد يكون المحتوى في حقل content أو output.content أو text
            if isinstance(cand, dict):
                return cand.get("output", {}).get("content") or cand.get("content") or cand.get("text") or ""
        return data.get("output", {}).get("text", "") or ""
    except Exception as e:
        return f"Error: {e}"

# TMDB helpers
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
    if not TMDB_API_KEY:
        return []
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        if region and region in REGION_MAP:
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc{REGION_MAP[region]}"
        else:
            url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
        resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []

def search_tmdb(query: str, content_type: Optional[str] = None) -> List[Dict]:
    if not TMDB_API_KEY or not query:
        return []
    try:
        q = requests.utils.quote(query)
        if content_type in ("movie", "tv"):
            url = f"{BASE_URL}/search/{content_type}?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        else:
            url = f"{BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []

def get_trailer(item_id: int, content_type: str = "movie") -> Optional[str]:
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
    except Exception:
        pass
    return []

# AI functions using Gemini
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
    lang_rule = get_lang_instruction(lang)
    p_key = _resolve_persona_key(persona)
    sys_prompt = f"{PERSONAS_MAP[p_key]} RULES: 1. {lang_rule} 2. Movie Titles MUST be in English inside [Brackets] e.g. [Inception]. 3. No Asian scripts."
    prompt_parts = [sys_prompt, "\n--- Conversation ---\n"]
    for m in messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        prompt_parts.append(f"{role.upper()}: {content}\n")
    prompt_parts.append("\nAssistant:")
    prompt_text = "\n".join(prompt_parts)
    return _call_gemini(prompt_text, temperature=0.7, max_tokens=500)

def analyze_image_search(image_file, lang: str = "ar") -> str:
    try:
        b64 = base64.b64encode(image_file.read()).decode("utf-8")
        image_file.seek(0)
    except Exception as e:
        return f"Error reading image: {e}"
    lang_rule = get_lang_instruction(lang)
    prompt = (
        f"Analyze the mood of the following image and recommend 3 movies. {lang_rule} "
        "Return titles inside [Brackets].\n\n"
        f"Image (base64): data:image/jpeg;base64,{b64}\n\n"
        "Provide a short explanation and 3 movie recommendations."
    )
    return _call_gemini(prompt, temperature=0.6, max_tokens=500)

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    lang_rule = get_lang_instruction(lang)
    prompt = f"User likes: {', '.join([m for m in movies if m])}. Analyze personality and suggest 3 NEW movies. {lang_rule} Titles in [Brackets]."
    return _call_gemini(prompt, temperature=0.7, max_tokens=400)

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    lang_rule = get_lang_instruction(lang)
    prompt = f"Matchmaker: Person A likes {u1}. Person B likes {u2}. Find middle ground movies. {lang_rule} Titles in [Brackets]."
    return _call_gemini(prompt, temperature=0.7, max_tokens=400)
