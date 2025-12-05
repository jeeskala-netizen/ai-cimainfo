/* static/style.css - متجاوب للهواتف والتابلت وسطح المكتب */
/* خطوط */
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700;900&display=swap');

:root{
  --primary-1: #6a11cb;
  --primary-2: #2575fc;
  --bg-dark: #0f0c29;
  --glass: rgba(255,255,255,0.06);
  --accent: linear-gradient(135deg,var(--primary-1),var(--primary-2));
  --radius: 12px;
  --max-width: 1100px;
  --text-muted: #bfc7d6;
}

*{box-sizing:border-box}
html,body{height:100%;margin:0;font-family:'Tajawal',sans-serif;background:
  linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);color:#fff;}

/* نافبار */
.nav-wrapper{
  width:100%;
  background: rgba(15,12,41,0.98);
  padding: calc(10px + env(safe-area-inset-top)) 16px 10px;
  display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid rgba(138,43,226,0.12);
  position:sticky;top:0;z-index:100;
}
.logo{font-weight:900;font-size:1.2rem;background:var(--accent);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.lang-switch a{color:var(--text-muted);text-decoration:none;margin-left:8px}

/* قائمة التنقل */
.hamburger{display:none;flex-direction:column;gap:5px;cursor:pointer}
.hamburger .bar{width:24px;height:3px;background:#fff;border-radius:3px}
.nav-menu{display:flex;gap:8px;list-style:none;margin:0;padding:0;align-items:center}
.nav-menu li{padding:8px 12px;border-radius:20px;color:var(--text-muted);cursor:pointer;font-size:0.95rem}
.nav-menu li.active{background:var(--accent);color:#fff;box-shadow:0 6px 18px rgba(106,17,203,0.18)}

/* الحاوية الرئيسية */
.main-container{display:flex;justify-content:center;padding:18px;min-height:calc(100vh - 70px)}
.container{width:100%;max-width:var(--max-width);display:flex;gap:20px;align-items:flex-start}

/* العمود الأيسر (المحتوى) */
.page-section{display:none;width:100%}
.page-section.active-section{display:block}

/* صندوق الدردشة */
.chat-home-layout{display:flex;flex-direction:column;height:70vh;min-height:420px;background:var(--glass);border-radius:var(--radius);padding:12px;overflow:hidden}
.controls-wrapper{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px}
.custom-dropdown{position:relative;max-width:220px;width:100%}
.dropdown-selected{display:flex;justify-content:space-between;align-items:center;padding:8px;border-radius:10px;background:transparent;border:1px solid rgba(255,255,255,0.06);cursor:pointer}
.dropdown-options{position:absolute;right:0;top:calc(100% + 8px);background:#121025;border-radius:10px;min-width:180px;display:none;box-shadow:0 8px 20px rgba(0,0,0,0.6);z-index:50}
.custom-dropdown.active .dropdown-options{display:block}
.dropdown-options div{padding:10px 12px;color:var(--text-muted);cursor:pointer}
.dropdown-options div:hover{background:#1f1b3a;color:#fff}

/* صندوق الرسائل */
.chat-box{flex:1;overflow:auto;padding:8px;display:flex;flex-direction:column;gap:12px}
.message{display:flex;gap:10px;align-items:flex-start}
.bot-msg .avatar,.user-msg .avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.06)}
.bubble{background:rgba(30,30,50,0.7);padding:10px 14px;border-radius:14px;max-width:85%;line-height:1.5}
.user-msg{flex-direction:row-reverse}
.user-msg .bubble{background:linear-gradient(90deg,var(--primary-1),var(--primary-2));color:#fff}

/* منطقة الإدخال مثبتة */
.input-area{position:sticky;bottom:0;display:flex;gap:8px;padding:10px;background:linear-gradient(180deg,rgba(0,0,0,0.0),rgba(0,0,0,0.2));align-items:center}
.input-area input[type="text"]{flex:1;padding:12px;border-radius:999px;border:none;background:rgba(255,255,255,0.06);color:#fff;outline:none;font-size:15px}
.send-btn{width:44px;height:44px;border-radius:50%;border:none;background:linear-gradient(90deg,var(--primary-1),var(--primary-2));display:flex;align-items:center;justify-content:center;color:#fff;cursor:pointer}

/* شبكة البطاقات */
.grid-container{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.movie-card{background:rgba(255,255,255,0.03);border-radius:10px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column;align-items:center}
.movie-card img{width:100%;height:auto;display:block}
.movie-card h4{margin:8px;font-size:0.95rem;text-align:center;color:#fff;padding:0 6px}

/* مودال */
.modal{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,0.6);z-index:200}
.modal .modal-content{width:95%;max-width:900px;background:#0b0b16;border-radius:12px;overflow:hidden}

/* استجابة */
@media (max-width: 1024px){
  .grid-container{grid-template-columns:repeat(3,1fr)}
  .chat-home-layout{height:62vh}
}
@media (max-width: 768px){
  .hamburger{display:flex}
  .nav-menu{position:fixed;top:0;right:-100%;height:100%;width:72%;flex-direction:column;padding-top:70px;background:rgba(15,12,41,0.98);transition:right .25s ease;z-index:150}
  .nav-menu.active{right:0}
  .grid-container{grid-template-columns:repeat(2,1fr)}
  .main-container{padding:12px}
  .chat-home-layout{height:58vh;min-height:360px}
}
@media (max-width:420px){
  .grid-container{grid-template-columns:repeat(1,1fr)}
  .logo{font-size:1rem}
}
