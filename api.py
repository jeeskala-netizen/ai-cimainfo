# api.py (cleaned)
import os, logging, base64, requests
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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if OPENROUTER_API_KEY:
    logger.info("OpenRouter API Key is configured.")
else:
    logger.error("CRITICAL: OPENROUTER_API_KEY is missing in environment.")

BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = getattr(config, "REQUEST_TIMEOUT", 10)

def _call_openrouter(messages: List[Dict], temperature: float = 0.7) -> str:
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY is missing."
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Referer": "https://ai-cimainfo.onrender.com",
        "X-Title": "CimaBot",
        "Content-Type": "application/json"
    }
    payload = {"model": "google/gemini-flash-1.5", "messages": messages, "temperature": temperature, "max_tokens": 800}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        if resp.status_code != 200:
            logger.error(f"OpenRouter API Error {resp.status_code}: {resp.text}")
            # try to extract error body
            try:
                err = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err = resp.text
            return f"Error from AI provider: {resp.status_code} - {err}"
        data = resp.json()
        # safe extraction
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {}).get("content") or choice.get("text") or ""
        return msg
    except Exception as e:
        logger.exception("Connection Exception")
        return "Error: Failed to connect to AI server."

def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    def get_lang_instruction(lang):
        if lang == "en": return "Speak ONLY in English."
        if lang == "de": return "Speak ONLY in German."
        return "Speak ONLY in Arabic."
    lang_rule = get_lang_instruction(lang)
    sys_msg = "You are CimaBot, a helpful movie expert."
    p = (persona or "").lower()
    if "critic" in p: sys_msg = "You are a snobbish movie critic. You hate blockbusters."
    elif "joker" in p: sys_msg = "You are a funny bot. Make jokes about movies."
    elif "fan" in p: sys_msg = "You are a hyped fanboy! Use emojis!"
    system_prompt = f"{sys_msg} RULES: 1. {lang_rule} 2. Movie titles MUST be in English inside [Brackets]. 3. Be concise."
    formatted = [{"role":"system","content":system_prompt}]
    for m in messages:
        formatted.append({"role": m.get("role","user"), "content": str(m.get("content",""))})
    return _call_openrouter(formatted)

def analyze_image_search(image_file, lang: str = "ar") -> str:
    if not OPENROUTER_API_KEY:
        return "Error: API Key missing."
    try:
        image_file.seek(0)
        img_data = base64.b64encode(image_file.read()).decode('utf-8')
        prompt = f"Analyze the mood of this image and recommend 3 movies. {('Speak ONLY in English.' if lang=='en' else 'Speak ONLY in Arabic.') } Titles in [Brackets]."
        messages = [{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img_data}"}}]}]
        return _call_openrouter(messages)
    except Exception as e:
        logger.exception("Image Processing Error")
        return "Error analyzing image."
# TMDB helpers (kept similar)...
