import requests
from groq import Groq
import config
import random
import base64
from functools import lru_cache

client = None
try:
    if hasattr(config, 'GROQ_API_KEY') and config.GROQ_API_KEY:
        client = Groq(api_key=config.GROQ_API_KEY)
    else: print("⚠️ Warning: GROQ Key missing.")
except Exception as e: print(f"❌ Groq Error: {e}")

# --- TMDB Functions (Added Timeouts) ---
@lru_cache(maxsize=100)
def fetch_content(content_type="movie", category="popular", region=None):
    api_key = config.TMDB_API_KEY; base_url = config.BASE_URL
    endpoint = "movie" if content_type == "movie" else "tv"
    region_map = {"korea": "&with_original_language=ko", "india": "&with_original_language=hi", "arabic": "&with_original_language=ar", "turkey": "&with_original_language=tr", "spain": "&with_original_language=es", "japan": "&with_original_language=ja&with_genres=16"}
    url = f"{base_url}/discover/{endpoint}?api_key={api_key}&language=ar-SA&sort_by=popularity.desc{region_map[region]}" if region and region in region_map else f"{base_url}/{endpoint}/{category}?api_key={api_key}&language=ar-SA"
    try:
        return requests.get(url, timeout=10).json().get('results', [])
    except: return []

def search_tmdb(query, content_type=None):
    try:
        url = f"{config.BASE_URL}/search/multi?api_key={config.TMDB_API_KEY}&query={query}&language=ar-SA"
        if content_type:
            url = f"{config.BASE_URL}/search/{content_type}?api_key={config.TMDB_API_KEY}&query={query}&language=ar-SA"
        return requests.get(url, timeout=10).json().get('results', [])
    except: return []

def get_trailer(id, content_type="movie"):
    try:
        data = requests.get(f"{config.BASE_URL}/{content_type}/{id}/videos?api_key={config.TMDB_API_KEY}", timeout=5).json()
        for v in data.get('results', []):
            if v['type'] == "Trailer" and v['site'] == "YouTube": return v['key']
    except: pass
    return None

def get_watch_providers(id, content_type="movie"):
    try:
        data = requests.get(f"{config.BASE_URL}/{content_type}/{id}/watch/providers?api_key={config.TMDB_API_KEY}", timeout=5).json()
        if 'results' in data and 'SA' in data['results']: return data['results']['SA'].get('flatrate', [])
    except: pass
    return []

# --- AI Functions ---
def get_lang_instruction(lang):
    if lang == "en": return "Speak ONLY in English."
    if lang == "de": return "Speak ONLY in German."
    return "Speak ONLY in Arabic."

def chat_with_ai_formatted(messages, persona, lang="ar"):
    if not client: return "Error: API Key Missing."
    lang_rule = get_lang_instruction(lang)
    
    personas_map = {
        "Friendly": "You are CimaBot, a helpful movie consultant.",
        "Critic": "You are a snobbish critic. Hate blockbusters.",
        "Joker": "You are a comedian bot. Make jokes.",
        "Fanboy": "You are a hyped geek! Use emojis."
    }
    p_key = "Friendly"
    if any(x in persona for x in ["ناقد", "Critic", "Kritiker"]): p_key = "Critic"
    elif any(x in persona for x in ["جوكر", "Joker"]): p_key = "Joker"
    elif any(x in persona for x in ["متحمس", "Fanboy"]): p_key = "Fanboy"
    
    sys_prompt = f"{personas_map[p_key]} RULES: 1. {lang_rule} 2. Movie Titles MUST be in English inside [Brackets] e.g. [Inception]. 3. No Asian scripts."
    
    if messages and messages[0].get("role") != "system": full = [{"role": "system", "content": sys_prompt}] + messages
    else: full = messages; 
    if full: full[0]["content"] = sys_prompt
    
    try: return client.chat.completions.create(messages=full, model="llama-3.3-70b-versatile", temperature=0.7).choices[0].message.content
    except Exception as e: return f"Error: {e}"

def analyze_image_search(image_file, lang="ar"):
    if not client: return "Error."
    try:
        b64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_file.seek(0)
        lang_rule = get_lang_instruction(lang)
        prompt = f"Analyze image mood. Recommend 3 movies. {lang_rule}. Titles in [Brackets]."
        return client.chat.completions.create(
            model="llama-3.2-90b-vision-preview", # تأكدنا من الموديل الصحيح
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
            temperature=0.6, max_tokens=500
        ).choices[0].message.content
    except Exception as e: return f"Error: {e}"

def analyze_dna(movies, lang="ar"):
    if not client: return "Error."
    lang_rule = get_lang_instruction(lang)
    prompt = f"User likes: {', '.join(movies)}. Analyze personality. Suggest 3 NEW movies. {lang_rule}. Titles in [Brackets]."
    try: return client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.7).choices[0].message.content
    except: return "Error."

def find_match(u1, u2, lang="ar"):
    if not client: return "Error."
    lang_rule = get_lang_instruction(lang)
    prompt = f"Matchmaker: Person A likes {u1}, Person B likes {u2}. Find middle ground movies. {lang_rule}. Titles in [Brackets]."
    try: return client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.7).choices[0].message.content
    except: return "Error."


App.py: 
from flask import Flask, render_template, request, jsonify
import api, languages, config, re, os

app = Flask(__name__)
# مفتاح سري عشوائي لتأمين الجلسات (مهم جداً)
app.secret_key = os.urandom(24) 

current_lang = "ar"

@app.route('/')
def home():
    t = languages.get_text(current_lang)
    return render_template('index.html', t=t, lang=current_lang)

@app.route('/change_lang/<lang>')
def change_lang(lang):
    global current_lang
    if lang in ['ar', 'en', 'de']: current_lang = lang
    return home()

def extract_movies_from_text(text):
    matches = re.findall(r'\[(.*?)\]', text)
    movies_data = []
    seen_ids = set()
    for name in matches:
        res = api.search_tmdb(name)
        if res:
            item = res[0]
            if item['id'] not in seen_ids and item.get('poster_path'):
                seen_ids.add(item['id'])
                movies_data.append({
                    "title": item.get('title') or item.get('name'),
                    "poster": config.IMAGE_URL + item['poster_path'],
                    "id": item['id'],
                    "type": 'movie' if item.get('title') else 'tv',
                    "overview": item.get('overview', '')
                })
    return movies_data

# --- Routes ---

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.form.get('msg')
    if not msg: return jsonify({'response': '...', 'movies': []}) # حماية من الإدخال الفارغ
    
    persona = request.form.get('persona')
    response_text = api.chat_with_ai_formatted([{"role": "user", "content": msg}], persona, current_lang)
    return jsonify({'response': response_text, 'movies': extract_movies_from_text(response_text)})

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    ctype = request.form.get('type')
    if not query: return jsonify({'movies': []})
    
    results = api.search_tmdb(query, ctype)
    movies = []
    for item in results:
        if item.get('poster_path'):
            movies.append({"title": item.get('title') or item.get('name'), "poster": config.IMAGE_URL + item['poster_path'], "id": item['id'], "type": 'movie' if item.get('title') else 'tv', "overview": item.get('overview', '')})
    return jsonify({'movies': movies})

@app.route('/browse_content', methods=['POST'])
def browse_content():
    content_type = request.form.get('type')
    category = request.form.get('category', 'popular')
    results = api.fetch_content(content_type, category)
    movies = []
    for item in results:
        if item.get('poster_path'):
            movies.append({"title": item.get('title') or item.get('name'), "poster": config.IMAGE_URL + item['poster_path'], "id": item['id'], "type": content_type, "overview": item.get('overview', '')})
    return jsonify({'movies': movies})

@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    if 'image' not in request.files: return jsonify({'error': 'No image'})
    file = request.files['image']
    if file.filename == '': return jsonify({'error': 'No selection'})
    
    # تحقق أمني بسيط من الامتداد
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return jsonify({'error': 'Invalid file type'})

    ai_text = api.analyze_image_search(file, current_lang)
    return jsonify({'response': ai_text, 'movies': extract_movies_from_text(ai_text)})

@app.route('/analyze_dna', methods=['POST'])
def analyze_dna():
    movies = [request.form.get('m1'), request.form.get('m2'), request.form.get('m3')]
    ai_text = api.analyze_dna(movies, current_lang)
    return jsonify({'response': ai_text, 'movies': extract_movies_from_text(ai_text)})

@app.route('/matchmaker', methods=['POST'])
def matchmaker():
    u1 = request.form.get('u1'); u2 = request.form.get('u2')
    ai_text = api.find_match(u1, u2, current_lang)
    return jsonify({'response': ai_text, 'movies': extract_movies_from_text(ai_text)})

@app.route('/get_details', methods=['POST'])
def get_details():
    mid = request.form.get('id'); mtype = request.form.get('type')
    providers = api.get_watch_providers(mid, mtype)
    clean_provs = []
    if providers:
        for p in providers:
            if p.get('logo_path'): clean_provs.append({'name': p['provider_name'], 'logo': config.IMAGE_URL + p['logo_path']})
    trailer = api.get_trailer(mid, mtype)
    return jsonify({'providers': clean_provs, 'trailer': trailer})

if __name__ == '__main__':
    app.run(debug=True)7
