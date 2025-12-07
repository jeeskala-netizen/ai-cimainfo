# api.py - Cleaned and corrected
import os
import logging
import base64
import requests
from functools import lru_cache
from typing import List, Dict, Optional
import config

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or getattr(config, "TMDB_API_KEY", None)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or getattr(config, "OPENROUTER_API_KEY", None)

if OPENROUTER_API_KEY:
    logger.info("OpenRouter API Key is configured and ready.")
else:
    logger.error("CRITICAL ERROR: OPENROUTER_API_KEY is missing in environment variables.")

BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = getattr(config, "REQUEST_TIMEOUT", 10)


def _call_openrouter(messages: List[Dict], temperature: float = 0.7) -> str:
    """
    Unified call to OpenRouter (or compatible) chat completions.
    Returns text or an error string.
    """
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY is missing. Please add it to environment."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Referer": "https://ai-cimainfo.onrender.com",
        "X-Title": "CimaBot",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemini-flash-1.5",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 800,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=25)
    except Exception as e:
        logger.exception("Connection Exception to OpenRouter")
        return "Error: Failed to connect to AI server."

    if resp.status_code != 200:
        logger.error("OpenRouter API Error %s: %s", resp.status_code, resp.text)
        try:
            body = resp.json()
            # try common error fields
            err_msg = body.get("error") or body.get("message") or resp.text
        except Exception:
            err_msg = resp.text
        return f"Error from AI provider: {resp.status_code} - {err_msg}"

    try:
        data = resp.json()
        # OpenRouter response shape may vary; try safe extraction
        choices = data.get("choices") or []
        if choices:
            first = choices[0]
            # message may be nested
            msg = first.get("message", {}) or {}
            content = msg.get("content") or first.get("text") or ""
            return content or ""
        # fallback to text field
        return data.get("text", "") or ""
    except Exception:
        logger.exception("Failed to parse OpenRouter response JSON")
        return "Error: Invalid response from AI provider."


def get_lang_instruction(lang: str) -> str:
    if lang == "en":
        return "Speak ONLY in English."
    if lang == "de":
        return "Speak ONLY in German."
    return "Speak ONLY in Arabic."


def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    """
    Prepare system prompt and forward to OpenRouter.
    messages: list of dicts with 'role' and 'content'
    persona: string to tweak system prompt
    """
    lang_rule = get_lang_instruction(lang)
    sys_msg = "You are CimaBot, a helpful movie expert."
    p = (persona or "").lower()
    if "critic" in p:
        sys_msg = "You are a snobbish movie critic. You hate blockbusters."
    elif "joker" in p:
        sys_msg = "You are a funny bot. Make jokes about movies."
    elif "fan" in p:
        sys_msg = "You are a hyped fanboy! Use emojis!"

    system_prompt = (
        f"{sys_msg} RULES: 1. {lang_rule} 2. Movie titles MUST be in English inside [Brackets]. 3. Be concise."
    )
    formatted_msgs = [{"role": "system", "content": system_prompt}]
    for m in messages:
        formatted_msgs.append({"role": m.get("role", "user"), "content": str(m.get("content", ""))})
    return _call_openrouter(formatted_msgs)


def analyze_image_search(image_file, lang: str = "ar") -> str:
    """
    Send multimodal request to OpenRouter: text + base64 image.
    """
    if not OPENROUTER_API_KEY:
        return "Error: API Key missing."

    try:
        image_file.seek(0)
        img_data = base64.b64encode(image_file.read()).decode("utf-8")
        prompt = f"Analyze the mood of this image and recommend 3 movies. {get_lang_instruction(lang)} Titles in [Brackets]."
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}},
                ],
            }
        ]
        return _call_openrouter(messages)
    except Exception:
        logger.exception("Image Processing Error")
        return "Error analyzing image."


def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    valid = [m for m in movies if m]
    if not valid:
        return "Please enter movies."
    prompt = f"User likes: {', '.join(valid)}. Analyze personality and suggest 3 NEW movies. {get_lang_instruction(lang)} Titles in [Brackets]."
    return _call_openrouter([{"role": "user", "content": prompt}])


def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    prompt = f"Matchmaker: Person A likes {u1}. Person B likes {u2}. Find middle ground movies. {get_lang_instruction(lang)} Titles in [Brackets]."
    return _call_openrouter([{"role": "user", "content": prompt}])


@lru_cache(maxsize=128)
def fetch_content(content_type: str = "movie", category: str = "popular", region: Optional[str] = None):
    if not TMDB_API_KEY:
        return []
    endpoint = "movie" if content_type == "movie" else "tv"
    try:
        if region:
            r_map = {"korea": "ko", "india": "hi", "arabic": "ar", "turkey": "tr", "spain": "es", "japan": "ja"}
            lang = r_map.get(region, "en")
            url = f"{BASE_URL}/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&sort_by=popularity.desc&with_original_language={lang}"
        else:
            url = f"{BASE_URL}/{endpoint}/{category}?api_key={TMDB_API_KEY}&language=ar-SA"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        logger.warning("TMDB fetch_content returned status %s", resp.status_code)
        return []
    except Exception:
        logger.exception("TMDB fetch_content error")
        return []


def search_tmdb(query: str, content_type: Optional[str] = None):
    if not TMDB_API_KEY or not query:
        return []
    try:
        q = requests.utils.quote(query)
        endpoint = f"search/{content_type}" if content_type in ["movie", "tv"] else "search/multi"
        url = f"{BASE_URL}/{endpoint}?api_key={TMDB_API_KEY}&query={q}&language=ar-SA"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        logger.warning("TMDB search returned status %s", resp.status_code)
        return []
    except Exception:
        logger.exception("TMDB search error")
        return []


def get_trailer(item_id: int, content_type: str = "movie") -> Optional[str]:
    if not TMDB_API_KEY:
        return None
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/videos?api_key={TMDB_API_KEY}"
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return None
        for v in res.json().get("results", []):
            if v.get("type") == "Trailer" and v.get("site") == "YouTube":
                return v.get("key")
    except Exception:
        logger.exception("get_trailer error")
    return None


def get_watch_providers(item_id: int, content_type: str = "movie"):
    if not TMDB_API_KEY:
        return []
    try:
        url = f"{BASE_URL}/{content_type}/{item_id}/watch/providers?api_key={TMDB_API_KEY}"
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return []
        return res.json().get("results", {}).get("SA", {}).get("flatrate", [])
    except Exception:
        logger.exception("get_watch_providers error")
        return []
