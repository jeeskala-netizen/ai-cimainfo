import streamlit as st
from st_clickable_images import clickable_images
from streamlit_option_menu import option_menu
import config
import styles
import api
import languages
import re 

# --- 1. إعدادات الصفحة (يجب أن تكون أول سطر) ---
st.set_page_config(page_title="AI Cinema Hub", page_icon="🔮", layout="wide")

# --- إدارة اللغة (Language State) ---
# التعديل: اللغة الافتراضية أصبحت الإنجليزية 'en'
if 'language' not in st.session_state: st.session_state.language = 'en'

# زر تبديل اللغة (أعلى الصفحة)
c_title, c_lang = st.columns([6, 1])
with c_lang:
    # التعديل: جعلنا English الخيار الأول في القائمة
    lang_choice = st.selectbox("🌐", ["English", "العربية", "Deutsch"], label_visibility="collapsed")
    
    # منطق التبديل
    if lang_choice == "English": st.session_state.language = "en"
    elif lang_choice == "Deutsch": st.session_state.language = "de"
    else: st.session_state.language = "ar"

# تحميل النصوص والستايل بناءً على اللغة المختارة
T = languages.get_text(st.session_state.language)
styles.load_css(direction=T['dir'])

# عنوان التطبيق
with c_title:
    st.markdown(f"<h1 style='margin:0; text-align: center;'>{T['app_title']}</h1>", unsafe_allow_html=True)

# --- دالة تحديث الرابط (Router) ---
def update_url(page_name):
    st.session_state.page = page_name
    st.query_params["page"] = page_name

current_query = st.query_params.get("page", "chat_home")

# --- تهيئة الذاكرة (Session State) ---
if 'page' not in st.session_state: st.session_state.page = current_query
if 'selected_movie' not in st.session_state: st.session_state.selected_movie = None
if 'favorites' not in st.session_state: st.session_state.favorites = []
if 'content_type' not in st.session_state: st.session_state.content_type = "movie"
if 'previous_nav' not in st.session_state: st.session_state.previous_nav = "home" # مفتاح داخلي
if 'dna_result' not in st.session_state: st.session_state.dna_result = None
if 'match_result' not in st.session_state: st.session_state.match_result = None
if 'visual_result' not in st.session_state: st.session_state.visual_result = None

# مزامنة الرابط
if st.session_state.page != current_query:
    st.session_state.page = current_query

# تهيئة الرسائل (إذا لم تكن موجودة)
if "messages" not in st.session_state: 
    # الافتراضي: رسالة الشخصية الأولى
    st.session_state.messages = [{"role": "assistant", "content": T['welcome_msgs'][0]}]

# --- 2. القائمة العلوية (Top Navigation) ---
# تحديد التبويب النشط بناءً على الصفحة الحالية
curr_idx = 0
if st.session_state.page == "chat_home": curr_idx = 0
elif st.session_state.page == "browse": curr_idx = 1 if st.session_state.content_type == "movie" else 2
elif st.session_state.page == "visual_detective": curr_idx = 3
elif st.session_state.page == "dna_analysis": curr_idx = 4
elif st.session_state.page == "matchmaker": curr_idx = 5
elif st.session_state.page == "library": curr_idx = 6

selected_nav = option_menu(
    menu_title=None, 
    options=T['menu'], 
    icons=["chat-quote", "film", "tv", "camera", "fingerprint", "people-arrows", "heart"],
    default_index=curr_idx,
    orientation="horizontal", 
    styles={
        "container": {"padding": "0!important", "background-color": "rgba(255,255,255,0.05)", "border-radius": "15px"},
        "icon": {"color": "#f0e68c", "font-size": "14px"}, 
        "nav-link": {"font-size": "13px", "text-align": "center", "margin": "0px", "--hover-color": "#4b0082", "color": "white"},
        "nav-link-selected": {"background-color": "#6a11cb", "color": "white", "box-shadow": "0px 0px 15px rgba(106, 17, 203, 0.5)"},
    }
)

# منطق التوجيه (بناءً على ترتيب القائمة لضمان عمل اللغات)
if selected_nav == T['menu'][0] and st.session_state.page != "chat_home": update_url("chat_home"); st.rerun()
elif selected_nav == T['menu'][1]: st.session_state.content_type = "movie"; update_url("browse"); st.rerun()
elif selected_nav == T['menu'][2]: st.session_state.content_type = "tv"; update_url("browse"); st.rerun()
elif selected_nav == T['menu'][3]: update_url("visual_detective"); st.rerun()
elif selected_nav == T['menu'][4]: update_url("dna_analysis"); st.rerun()
elif selected_nav == T['menu'][5]: update_url("matchmaker"); st.rerun()
elif selected_nav == T['menu'][6]: update_url("library"); st.rerun()

st.markdown("---")

# --- 4. الدوال المساعدة ---

def extract_and_display_media(text, idx):
    """استخراج وعرض الأفلام من ردود الذكاء الاصطناعي"""
    st.markdown(text)
    matches = re.findall(r'\[(.*?)\]', text)
    if matches:
        st.markdown("---")
        cols = st.columns(len(matches))
        for i, m in enumerate(matches):
            res = api.search_tmdb(m)
            if res:
                item = res[0]
                if item.get('poster_path'):
                    with cols[i % 3]:
                        st.image(config.IMAGE_URL + item['poster_path'], use_container_width=True)
                        # مفتاح فريد للزر
                        if st.button(f"⬅️", key=f"btn_{item['id']}_{idx}_{i}"):
                            st.session_state.selected_movie = item
                            update_url("details")
                            st.rerun()

def show_grid(items):
    """عرض شبكة الأفلام"""
    if not items: st.warning("No results."); return
    imgs, names = [], []
    for it in items:
        if it.get('poster_path'):
            imgs.append(config.IMAGE_URL + it['poster_path'])
            names.append(it.get('title') or it.get('name'))
    if imgs:
        clk = clickable_images(
            imgs, titles=names,
            div_style={"display": "flex", "justify-content": "center", "flex-wrap": "wrap", "gap": "15px", "padding": "10px"},
            img_style={"cursor": "pointer", "border-radius": "12px", "width": "140px", "box-shadow": "0 5px 15px rgba(0,0,0,0.5)"},
            key=f"grid_{st.session_state.page}_{len(items)}"
        )
        if clk > -1:
            # البحث عن العنصر الصحيح في القائمة الأصلية
            target_img = imgs[clk]
            original_item = None
            for it in items:
                if it.get('poster_path') and (config.IMAGE_URL + it['poster_path']) == target_img:
                    original_item = it
                    break
            
            if original_item:
                st.session_state.selected_movie = original_item
                update_url("details")
                st.rerun()

# --- 5. الصفحات ---

# 1. الشات (الصفحة الرئيسية)
if st.session_state.page == "chat_home":
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1: 
            persona = st.radio(T['persona_label'], T['personas'], horizontal=True)
        with c2: 
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🎭 {T['new_chat']}", use_container_width=True):
                st.session_state.messages = []
                
                # جلب رسالة الترحيب الصحيحة حسب الشخصية واللغة
                try:
                    p_index = T['personas'].index(persona)
                    custom_welcome = T['welcome_msgs'][p_index]
                except:
                    custom_welcome = T['welcome_msgs'][0]
                
                st.session_state.messages.append({"role": "assistant", "content": custom_welcome})
                st.rerun()
    
    # عرض الرسائل
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant": extract_and_display_media(msg["content"], i)
                else: st.write(msg["content"])
    
    # إدخال المستخدم
    if p := st.chat_input(T['input_placeholder']):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        with st.chat_message("assistant"):
            with st.spinner("..."):
                r = api.chat_with_ai_formatted(st.session_state.messages, persona, st.session_state.language)
                extract_and_display_media(r, len(st.session_state.messages))
                st.session_state.messages.append({"role": "assistant", "content": r})

# 2. المحقق البصري
elif st.session_state.page == "visual_detective":
    st.markdown(f"<h2 style='text-align: center;'>{T['header_visual']}</h2>", unsafe_allow_html=True)
    st.caption(f"<div style='text-align:center'>{T['visual_desc']}</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 1])
    with c1:
        up = st.file_uploader(T['upload_text'], type=['jpg', 'png'])
        if up:
            st.image(up, use_container_width=True)
            if st.button(T['analyze_btn'], use_container_width=True):
                with st.spinner("..."): 
                    st.session_state.visual_result = api.analyze_image_search(up, st.session_state.language)
    with c2:
        if st.session_state.visual_result: 
            st.success(T['success_analysis'])
            extract_and_display_media(st.session_state.visual_result, 77)

# 3. تحليل DNA
elif st.session_state.page == "dna_analysis":
    st.markdown(f"<h2 style='text-align: center;'>{T['header_dna']}</h2>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        m1 = st.text_input(T['movie_1'])
        m2 = st.text_input(T['movie_2'])
        m3 = st.text_input(T['movie_3'])
        if st.button(T['analyze_dna_btn'], use_container_width=True):
            if m1 and m2 and m3:
                with st.spinner("..."): 
                    st.session_state.dna_result = api.analyze_dna([m1, m2, m3], st.session_state.language)
    with c2:
        if st.session_state.dna_result: 
            st.success(T['success_analysis'])
            extract_and_display_media(st.session_state.dna_result, 99)

# 4. توفيق القلوب (Matchmaker)
elif st.session_state.page == "matchmaker":
    st.markdown(f"<h2 style='text-align: center;'>{T['header_match']}</h2>", unsafe_allow_html=True)
    st.caption(f"<div style='text-align:center'>{T['match_desc']}</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: u1 = st.text_input(T['user_1'])
    with c2: u2 = st.text_input(T['user_2'])
    
    if st.button(T['match_btn'], use_container_width=True):
        if u1 and u2:
            with st.spinner("..."): 
                st.session_state.match_result = api.find_match(u1, u2, st.session_state.language)
    
    if st.session_state.match_result: 
        st.success(T['success_match'])
        extract_and_display_media(st.session_state.match_result, 88)

# 5. التفاصيل (Details)
elif st.session_state.page == "details":
    item = st.session_state.selected_movie
    if item:
        if st.button(T['back_btn']): update_url("chat_home"); st.rerun()
        
        if item.get('backdrop_path'): 
            st.image(config.BACKDROP_URL + item['backdrop_path'], use_container_width=True)
        
        st.markdown(f"<h1 style='text-align: center;'>{item.get('title') or item.get('name')}</h1>", unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 2])
        with c1: 
            if item.get('poster_path'): st.image(config.IMAGE_URL + item['poster_path'], use_container_width=True)
            
            st.markdown(f"**{T['providers']}**")
            provs = api.get_watch_providers(item['id'], 'movie' if item.get('title') else 'tv')
            if provs:
                cols = st.columns(len(provs))
                for i, p in enumerate(provs): 
                    if p.get('logo_path'): 
                        with cols[i]: st.image(config.IMAGE_URL + p['logo_path'], width=40)
            else:
                st.caption(T['no_providers'])
            
            st.markdown("---")
            is_fav = any(f['id']==item['id'] for f in st.session_state.favorites)
            if st.button(T['fav_rem'] if is_fav else T['fav_add'], use_container_width=True):
                if is_fav: st.session_state.favorites = [f for f in st.session_state.favorites if f['id']!=item['id']]
                else: 
                    item['media_type'] = 'movie' if item.get('title') else 'tv'
                    st.session_state.favorites.append(item)
                st.rerun()
        
        with c2:
            st.subheader(T['story'])
            st.write(item.get('overview'))
            tr = api.get_trailer(item['id'], 'movie' if item.get('title') else 'tv')
            if tr: 
                st.markdown(f"### {T['trailer']}")
                st.video(tr)

# 6. التصفح (Browse)
elif st.session_state.page == "browse":
    t_type = T['browse_movies'] if st.session_state.content_type == "movie" else T['browse_tv']
    st.markdown(f"<h2 style='text-align: center;'>{t_type}</h2>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 3])
    with c1: 
        sort = st.selectbox(T['sort_label'], T['sort_opts'])
        # Map sort back to API keys
        cat = "popular"
        if sort == T['sort_opts'][1]: cat = "top_rated"
        elif sort == T['sort_opts'][2]: cat = "now_playing" if st.session_state.content_type=="movie" else "on_the_air"
    
    with c2: search = st.text_input(T['search_placeholder'])
    
    if search: res = api.search_tmdb(search, st.session_state.content_type)
    else: res = api.fetch_content(st.session_state.content_type, cat)
    show_grid(res)

# 7. المكتبة (Library)
elif st.session_state.page == "library":
    st.markdown(f"<h2 style='text-align: center;'>{T['header_fav']}</h2>", unsafe_allow_html=True)
    show_grid(st.session_state.favorites)