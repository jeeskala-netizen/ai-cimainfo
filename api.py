import requests
from groq import Groq
import config
import random
import base64
from functools import lru_cache # بديل للتخزين المؤقت لزيادة السرعة

# --- 1. إعداد العميل ---
client = None
try:
    if hasattr(config, 'GROQ_API_KEY') and config.GROQ_API_KEY:
        client = Groq(api_key=config.GROQ_API_KEY)
    else:
        print("Warning: GROQ_API_KEY missing.")
except Exception as e:
    print(f"Groq Error: {e}")

# --- 2. دوال TMDB (مع التخزين المؤقت) ---

@lru_cache(maxsize=100)
def fetch_content(content_type="movie", category="popular", region=None):
    """جلب المحتوى الرائج"""
    api_key = config.TMDB_API_KEY
    base_url = config.BASE_URL
    endpoint = "movie" if content_type == "movie" else "tv"
    
    region_map = {
        "korea": "&with_original_language=ko",
        "india": "&with_original_language=hi",
        "arabic": "&with_original_language=ar",
        "turkey": "&with_original_language=tr",
        "spain": "&with_original_language=es",
        "japan": "&with_original_language=ja&with_genres=16"
    }

    url = ""
    if region and region in region_map:
        url = f"{base_url}/discover/{endpoint}?api_key={api_key}&language=ar-SA&sort_by=popularity.desc{region_map[region]}"
    else:
        url = f"{base_url}/{endpoint}/{category}?api_key={api_key}&language=ar-SA"

    try:
        return requests.get(url).json().get('results', [])
    except:
        return []

def search_tmdb(query, content_type=None):
    """البحث عن فيلم أو مسلسل"""
    try:
        url = f"{config.BASE_URL}/search/multi?api_key={config.TMDB_API_KEY}&query={query}&language=ar-SA"
        if content_type:
            url = f"{config.BASE_URL}/search/{content_type}?api_key={config.TMDB_API_KEY}&query={query}&language=ar-SA"
        return requests.get(url).json().get('results', [])
    except:
        return []

def get_trailer(id, content_type="movie"):
    """جلب التريلر"""
    try:
        data = requests.get(f"{config.BASE_URL}/{content_type}/{id}/videos?api_key={config.TMDB_API_KEY}").json()
        for v in data.get('results', []):
            if v['type'] == "Trailer" and v['site'] == "YouTube":
                return v['key']
    except:
        pass
    return None

def get_watch_providers(id, content_type="movie"):
    """أين تشاهد"""
    try:
        data = requests.get(f"{config.BASE_URL}/{content_type}/{id}/watch/providers?api_key={config.TMDB_API_KEY}").json()
        if 'results' in data and 'SA' in data['results']:
            return data['results']['SA'].get('flatrate', [])
    except:
        pass
    return []

# --- 3. دوال الذكاء الاصطناعي (متعددة اللغات) ---

def get_lang_instruction(lang):
    if lang == "en": return "Speak ONLY in English."
    if lang == "de": return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

def chat_with_ai_formatted(messages, persona, lang="ar"):
    if not client: return "Error: API Key Missing."
    lang_rule = get_lang_instruction(lang)
    
    # تعريف الشخصيات (يمكن توسيعه)
    personas_map = {
        "Friendly": "You are CimaBot, a helpful movie consultant.",
        "Critic": "You are a snobbish critic. Hate blockbusters.",
        "Joker": "You are a comedian bot. Make jokes.",
        "Fanboy": "You are a hyped geek! Use emojis."
    }
    
    # تخمين الشخصية من الاسم المرسل (للبساطة)
    p_key = "Friendly"
    if any(x in persona for x in ["ناقد", "Critic", "Kritiker"]): p_key = "Critic"
    elif any(x in persona for x in ["جوكر", "Joker"]): p_key = "Joker"
    elif any(x in persona for x in ["متحمس", "Fanboy"]): p_key = "Fanboy"
    
    sys_prompt = f"""
    {personas_map[p_key]}
    RULES:
    1. {lang_rule}
    2. Movie Titles MUST be in English inside [Brackets] e.g. [Inception].
    3. No Asian scripts unless requested.
    """
    
    # بناء الرسائل
    if messages and messages[0].get("role") != "system":
        full = [{"role": "system", "content": sys_prompt}] + messages
    else:
        full = messages
        if full: full[0]["content"] = sys_prompt
        else: full = [{"role": "system", "content": sys_prompt}]
    
    try:
        return client.chat.completions.create(
            messages=full, model="llama-3.3-70b-versatile", temperature=0.7
        ).choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def analyze_image_search(image_file, lang="ar"):
    if not client: return "Error."
    try:
        # قراءة الصورة وتحويلها
        b64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_file.seek(0) # إعادة المؤشر
        
        lang_rule = get_lang_instruction(lang)
        prompt = f"Analyze image mood. Recommend 3 movies. {lang_rule}. Titles in [Brackets]."
        
        return client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
            temperature=0.6, max_tokens=500
        ).choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def analyze_dna(movies, lang="ar"):
    if not client: return "Error."
    lang_rule = get_lang_instruction(lang)
    prompt = f"User likes: {', '.join(movies)}. Analyze personality. Suggest 3 NEW movies. {lang_rule}. Titles in [Brackets]."
    try:
        return client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.7).choices[0].message.content
    except: return "Error."

def find_match(u1, u2, lang="ar"):
    if not client: return "Error."
    lang_rule = get_lang_instruction(lang)
    prompt = f"Matchmaker: Person A likes {u1}, Person B likes {u2}. Find middle ground movies. {lang_rule}. Titles in [Brackets]."
    try:
        return client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.7).choices[0].message.content
    except: return "Error."