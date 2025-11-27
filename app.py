from flask import Flask, render_template, request, jsonify
import api
import languages
import config
import re

app = Flask(__name__)
current_lang = "ar"

@app.route('/')
def home():
    t = languages.get_text(current_lang)
    return render_template('index.html', t=t, lang=current_lang)

@app.route('/change_lang/<lang>')
def change_lang(lang):
    global current_lang
    if lang in ['ar', 'en', 'de']:
        current_lang = lang
    return home()

# --- دالة مساعدة لاستخراج بيانات الأفلام ---
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

# --- المسارات (Routes) ---

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.form.get('msg')
    persona = request.form.get('persona')
    # لاحظ: هنا نستخدم قائمة بسيطة للتاريخ، يمكن تطويرها لـ Session لاحقاً
    response_text = api.chat_with_ai_formatted(
        [{"role": "user", "content": msg}], 
        persona, 
        current_lang
    )
    movies = extract_movies_from_text(response_text)
    return jsonify({'response': response_text, 'movies': movies})

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    ctype = request.form.get('type')
    results = api.search_tmdb(query, ctype)
    movies = []
    for item in results:
        if item.get('poster_path'):
            movies.append({
                "title": item.get('title') or item.get('name'),
                "poster": config.IMAGE_URL + item['poster_path'],
                "id": item['id'],
                "type": 'movie' if item.get('title') else 'tv',
                "overview": item.get('overview', '')
            })
    return jsonify({'movies': movies})

# ✅ هذا هو المسار الجديد المهم للتحميل التلقائي
@app.route('/browse_content', methods=['POST'])
def browse_content():
    content_type = request.form.get('type')
    category = request.form.get('category', 'popular')
    
    results = api.fetch_content(content_type, category)
    movies = []
    for item in results:
        if item.get('poster_path'):
            movies.append({
                "title": item.get('title') or item.get('name'),
                "poster": config.IMAGE_URL + item['poster_path'],
                "id": item['id'],
                "type": content_type,
                "overview": item.get('overview', '')
            })
    return jsonify({'movies': movies})

@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    if 'image' not in request.files: return jsonify({'error': 'No image'})
    file = request.files['image']
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
            if p.get('logo_path'):
                clean_provs.append({'name': p['provider_name'], 'logo': config.IMAGE_URL + p['logo_path']})
    trailer = api.get_trailer(mid, mtype)
    return jsonify({'providers': clean_provs, 'trailer': trailer})

if __name__ == '__main__':
    app.run(debug=True)