import streamlit as st
import streamlit.components.v1 as components

# لاحظ: قمنا بإضافة معامل direction للدالة
def load_css(direction="rtl"):
    # تحديد محاذاة النص بناءً على الاتجاه
    text_align = "right" if direction == "rtl" else "left"
    
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700;900&display=swap');
        
        html, body, [class*="st-"] {{
            font-family: 'Tajawal', sans-serif;
            direction: {direction};
        }}
        
        /* إجبار القوائم المنسدلة على اتباع الاتجاه */
        div[data-baseweb="select"] > div {{
            direction: {direction};
            text-align: {text_align};
        }}
        
        .stApp {{
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #ffffff;
        }}

        /* باقي التنسيقات كما هي تماماً (Nav container, buttons, hidden elements...) */
        /* ... انسخ باقي كود CSS من النسخة السابقة هنا ... */
        /* سأضع لك الأكواد المهمة فقط للاختصار، تأكد من نسخ كود الإخفاء السابق */
        
        .nav-container {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(4px);
        }}
        
        h1, h2 {{
            background: -webkit-linear-gradient(#fff, #a18cd1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
        }}

        /* الإخفاء النهائي */
        [data-testid="stSidebar"], [data-testid="collapsedControl"], 
        .stDeployButton, [data-testid="stToolbar"], [data-testid="stHeader"], 
        footer, header, #MainMenu, .viewerBadge_container__1QSob {{
            display: none !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # كود الجافاسكريبت للإخفاء (كما هو)
    components.html("""
        <script>
            function removeStreamlitElements() {
                const selectors = ['footer', 'header[data-testid="stHeader"]', '.stAppDeployButton', '[data-testid="stDecoration"]', 'div[class^="viewerBadge"]'];
                selectors.forEach(selector => {
                    const elements = window.parent.document.querySelectorAll(selector);
                    elements.forEach(el => { el.style.display = 'none'; el.innerHTML = ''; });
                });
            }
            removeStreamlitElements();
            setInterval(removeStreamlitElements, 500);
        </script>
    """, height=0, width=0)