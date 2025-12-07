# Api.py - Production Ready (OpenRouter Primary + Smart Gemini Fallback)
import os
import logging
import base64
import requests
from functools import lru_cache
from typing import List, Optional, Dict
import config

# --- إعدادات السجلات (Logging) لمعرفة الأخطاء فوراً ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- تحميل المفاتيح (مباشرة من Render لضمان القراءة) ---
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or getattr(config, "TMDB_API_KEY", None)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# المفاتيح الاحتياطية
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)

# طباعة حالة المفاتيح في السجل (للتأكد من أن Render قرأها)
if OPENROUTER_API_KEY:
    logger.info("✅ OpenRouter Key Detected.")
elif GEMINI_API_KEY:
    logger.info("⚠️ OpenRouter missing. Using Gemini Direct Fallback.")
else:
    logger.error("❌ CRITICAL: No AI Keys Found!")

# إعدادات TMDB
BASE_URL = getattr(config, "BASE_URL", "https://api.themoviedb.org/3")
IMAGE_URL = getattr(config, "IMAGE_URL", "https://image.tmdb.org/t/p/w500")
REQUEST_TIMEOUT = 10

# --- الدالة الرئيسية للذكاء الاصطناعي (Smart Router) ---

def _call_ai_service(messages: List[Dict], temperature: float = 0.7) -> str:
    """
    تحاول الاتصال بـ OpenRouter أولاً.
    إذا فشلت، تحاول الاتصال بـ Gemini مباشرة كخيار طوارئ.
    """
    
    # === الخطة أ: OpenRouter (الأفضل والأسرع) ===
    if OPENROUTER_API_KEY:
        try:
            # استخدام موديل Gemini Flash السريع والمجاني عبر OpenRouter
            model = "google/gemini-flash-1.5" 
            
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://ai-cimainfo.onrender.com", 
                "X-Title": "CimaBot",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 600
            }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            else:
                logger.error(f"OpenRouter Error {resp.status_code}: {resp.text}")
                # هنا لا نتوقف، بل ننتقل للخطة ب (Fallback)
                
        except Exception as e:
            logger.error(f"OpenRouter Connection Failed: {e}")

    # === الخطة ب: Gemini Direct (احتياطي الطوارئ) ===
    if GEMINI_API_KEY:
        logger.info("🔄 Switching to Gemini Direct API fallback...")
        return _fallback_gemini_direct(messages, temperature)

    return "Error: Could not contact AI. Please add OPENROUTER_API_KEY or ensure GEMINI_API_KEY is valid."

def _fallback_gemini_direct(messages: List[Dict], temperature: float) -> str:
    """
    اتصال مباشر بجوجل في حال تعطل OpenRouter.
    تم إصلاح خطأ 404 بتثبيت الموديل على gemini-1.5-flash
    """
    try:
        # تحويل المحادثة لنص واحد لأن واجهة REST البسيطة تفضل ذلك
        full_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        # استخدام النسخة v1beta الأحدث مع الموديل الصحيح لتجنب 404
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": temperature}
        }
        
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        
        if resp.status_code == 200:
            candidates = resp.json().get('candidates')
            if candidates:
                return candidates[0]['content']['parts'][0]['text']
            return "No content returned from Gemini."
        else:
            logger.error(f"Gemini Direct Error {resp.status_code}: {resp.text}")
            if resp.status_code == 404:
                return "Error: Gemini Model 404. Please report to developer."
            return f"Error: Gemini API Status {resp.status_code}"
            
    except Exception as e:
        logger.error(f"Gemini Direct Exception: {e}")
        return f"Error: {str(e)}"

# --- دوال مساعدة TMDB (تعمل بنجاح) ---

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

# --- دوال الواجهة (Chat, Image, Matchmaker) ---

def get_lang_instruction(lang: str) -> str:
    if lang == "en": return "Speak ONLY in English."
    if lang == "de": return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

def chat_with_ai_formatted(messages: List[Dict], persona: str, lang: str = "ar") -> str:
    """بناء المحادثة وإرسالها لـ OpenRouter"""
    lang_rule = get_lang_instruction(lang)
    
    # تحديد الشخصية
    sys_msg = "You are CimaBot, a helpful movie expert."
    p = (persona or "").lower()
    if "critic" in p: sys_msg = "You are a snobbish movie critic. You hate blockbusters."
    elif "joker" in p: sys_msg = "You are a funny bot. Make jokes about movies."
    elif "fan" in p: sys_msg = "You are a hyped fanboy! Use emojis! 🤩"
    
    system_prompt = f"{sys_msg} RULES: 1. {lang_rule} 2. Movie titles MUST be in English inside [Brackets] like [Inception]. 3. Be concise."
    
    # تكوين قائمة الرسائل
    formatted_msgs = [{"role": "system", "content": system_prompt}]
    for m in messages:
        formatted_msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        
    return _call_ai_service(formatted_msgs)

def analyze_image_search(image_file, lang: str = "ar") -> str:
    """تحليل الصور باستخدام OpenRouter Vision أو Gemini Fallback"""
    if not OPENROUTER_API_KEY and not GEMINI_API_KEY:
        return "Error: AI Keys missing."
        
    try:
        # تجهيز الصورة
        img_data = base64.b64encode(image_file.read()).decode('utf-8')
        image_file.seek(0)
        
        prompt = f"Analyze the mood of this image and recommend 3 movies. {get_lang_instruction(lang)} Titles in [Brackets]."
        
        # إذا كان OpenRouter موجود، نستخدمه (يدعم الصور)
        if OPENROUTER_API_KEY:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                    ]
                }
            ]
            return _call_ai_service(messages)
            
        # وإلا نستخدم Gemini Direct Vision كاحتياطي
        else:
            return _fallback_gemini_vision(img_data, prompt)
            
    except Exception as e:
        logger.error(f"Image Error: {e}")
        return "Error processing image."

def _fallback_gemini_vision(b64_data, prompt):
    try:
        # هنا أيضاً نستخدم الموديل الصحيح لتجنب 404
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_data}}
                ]
            }]
        }
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        if resp.status_code == 200:
            return resp.json()['candidates'][0]['content']['parts'][0]['text']
        else:
             logger.error(f"Gemini Vision Error {resp.status_code}: {resp.text}")
    except: pass
    return "Error analyzing image (Gemini Fallback)."

def analyze_dna(movies: List[str], lang: str = "ar") -> str:
    valid = [m for m in movies if m]
    if not valid: return "Please enter movies."
    prompt = f"User likes: {', '.join(valid)}. Analyze personality and suggest 3 NEW movies. {get_lang_instruction(lang)} Titles in [Brackets]."
    return _call_ai_service([{"role": "user", "content": prompt}])

def find_match(u1: str, u2: str, lang: str = "ar") -> str:
    prompt = f"Matchmaker: Person A likes {u1}. Person B likes {u2}. Find middle ground movies. {get_lang_instruction(lang)} Titles in [Brackets]."
    return _call_ai_service([{"role": "user", "content": prompt}])
