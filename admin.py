"""
admin.py — Cellyn Store Admin Panel
Jalankan: python admin.py
Akses: http://localhost:5000
Password default: cellyn123 (ubah via env ADMIN_PASSWORD)
"""

import os
import sys
import sqlite3
import html

# Load .env manual
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line = _line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from admin_embed import embed_bp
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET", "cellyn-admin-secret-2024")
app.register_blueprint(embed_bp)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "cellyn123")
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")


# ── DB ────────────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def safe_int(val, min_val=None):
    """Konversi string ke int dengan aman. Return None jika tidak valid."""
    try:
        v = int(str(val).strip())
        if min_val is not None and v < min_val:
            return None
        return v
    except (ValueError, TypeError):
        return None


# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── BASE TEMPLATE ─────────────────────────────────────────────────────────────
BASE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cellyn Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
 :root{
  --bg:#0b0d12;--surface:#12151c;--surface2:#151a24;--surface3:#1a2230;
  --border:#262b35;--border2:#2f3643;
  --gold:#c9a84c;--gold2:#e8c96a;--gold3:#9b7a2e;
  --accent:#9cd6ff;--accent2:#5bb7ff;
  --text:#eef0f6;--muted:#7c8798;--muted2:#9aa6b8;
  --danger:#e06a6a;--success:#4dbb8a;--warning:#e3a24f;
  --sidebar-w:252px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{
  font-family:'Plus Jakarta Sans',sans-serif;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(201,168,76,.12), transparent 60%),
    radial-gradient(1200px 600px at 100% 10%, rgba(92,188,255,.12), transparent 55%),
    var(--bg);
  color:var(--text);min-height:100vh;display:flex;
}
a{color:var(--gold);text-decoration:none;}

/* ── SIDEBAR ── */
.sidebar{width:var(--sidebar-w);min-height:100vh;background:linear-gradient(180deg, #12151c 0%, #0f1218 100%);
  border-right:1px solid var(--border);display:flex;flex-direction:column;position:fixed;top:0;left:0;z-index:200;transition:transform .25s ease;}
.sidebar-logo{padding:1.6rem 1.35rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:.85rem;}
.sidebar-logo img{width:40px;height:40px;border-radius:10px;object-fit:cover;box-shadow:0 10px 24px rgba(0,0,0,.35);}
.sidebar-logo-text{font-family:'Cormorant Garamond',serif;font-size:1.2rem;font-weight:700;letter-spacing:.06em;line-height:1.1;}
.sidebar-logo-text span{display:block;font-size:.65rem;font-weight:400;color:var(--gold);letter-spacing:.15em;text-transform:uppercase;font-family:'Plus Jakarta Sans',sans-serif;}
.sidebar-nav{flex:1;padding:1rem 0;overflow-y:auto;}
.nav-section{padding:.35rem 1.25rem;font-size:.6rem;font-weight:600;color:var(--muted);letter-spacing:.15em;text-transform:uppercase;margin-top:.75rem;}
.nav-item{display:flex;align-items:center;gap:.75rem;padding:.62rem 1.35rem;color:var(--muted2);font-size:.84rem;font-weight:500;
  transition:all .18s;cursor:pointer;border-left:2px solid transparent;margin:2px 0;border-radius:0 10px 10px 0;}
.nav-item:hover{color:var(--text);background:rgba(255,255,255,.03);border-left-color:var(--border2);}
.nav-item.active{color:var(--gold);background:linear-gradient(90deg,rgba(201,168,76,.14),rgba(255,255,255,0));border-left-color:var(--gold);box-shadow:inset 0 0 0 1px rgba(201,168,76,.15);}
.nav-item svg{width:15px;height:15px;flex-shrink:0;opacity:.7;}
.nav-item.active svg{opacity:1;}
.sidebar-footer{padding:1rem 1.25rem;border-top:1px solid var(--border);}
.nav-logout{display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;border-radius:8px;color:var(--danger);font-size:.82rem;
  font-weight:500;transition:all .15s;cursor:pointer;background:rgba(224,85,85,.05);border:1px solid rgba(224,85,85,.15);}
.nav-logout:hover{background:rgba(224,85,85,.12);color:var(--danger);}
.nav-logout svg{width:15px;height:15px;}

/* ── TOPBAR MOBILE ── */
.topbar{display:none;height:56px;background:var(--surface);border-bottom:1px solid var(--border);
  padding:0 1rem;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:150;}
.topbar-logo{font-family:'Cormorant Garamond',serif;font-size:1rem;font-weight:700;}
.topbar-logo span{color:var(--gold);}
.hamburger{background:none;border:none;color:var(--text);cursor:pointer;padding:.4rem;}
.hamburger svg{width:22px;height:22px;}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:190;backdrop-filter:blur(2px);}
.sidebar-overlay.active{display:block;}

/* ── MAIN CONTENT ── */
.main{margin-left:var(--sidebar-w);flex:1;min-height:100vh;display:flex;flex-direction:column;}
.content{flex:1;padding:2.2rem;animation:fadeUp .4s ease both;}

/* ── PAGE HEADER ── */
.page-header{margin-bottom:1.75rem;}
.page-title{font-family:'Cormorant Garamond',serif;font-size:2rem;font-weight:700;letter-spacing:.04em;color:var(--text);}
.page-title small{display:block;font-family:'Plus Jakarta Sans',sans-serif;font-size:.8rem;font-weight:500;color:var(--muted);margin-top:.25rem;letter-spacing:.08em;text-transform:uppercase;}
.page-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem;}

/* ── CARDS ── */
.card{background:linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,.01)), var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:1.25rem;box-shadow:0 18px 40px rgba(0,0,0,.24);backdrop-filter:blur(6px);}
.card-header{padding:.9rem 1.35rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--surface2);}
.card-title{font-size:.72rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);}
.card-body{padding:1.25rem;}

/* ── STAT CARDS ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin-bottom:1.5rem;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.25rem;position:relative;overflow:hidden;transition:border-color .2s, transform .2s;}
.stat-card:hover{border-color:var(--border2);transform:translateY(-2px);}
.stat-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;}
.stat-card.ml::after{background:linear-gradient(90deg,#3498DB,transparent);}
.stat-card.ff::after{background:linear-gradient(90deg,#FF6B35,transparent);}
.stat-card.robux::after{background:linear-gradient(90deg,#E91E63,transparent);}
.stat-card.gp::after{background:linear-gradient(90deg,#9B59B6,transparent);}
.stat-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;margin-bottom:.75rem;font-size:1rem;}
.stat-label{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.2em;font-weight:500;}
.stat-value{font-family:'Cormorant Garamond',serif;font-size:2.2rem;font-weight:700;margin-top:.15rem;line-height:1;}
.stat-sub{font-size:.72rem;color:var(--muted);margin-top:.3rem;}

/* ── TABLE ── */
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:.7rem 1.25rem;font-size:.67rem;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);border-bottom:1px solid var(--border);font-weight:600;}
td{padding:.85rem 1.25rem;border-bottom:1px solid rgba(38,43,53,.6);font-size:.83rem;vertical-align:middle;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:rgba(201,168,76,.03);}

/* ── BADGE ── */
.badge{display:inline-flex;align-items:center;padding:.2rem .55rem;border-radius:4px;font-size:.67rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;}
.badge-gamepass{background:rgba(124,106,255,.12);color:#a090ff;border:1px solid rgba(124,106,255,.25);}
.badge-crate{background:rgba(255,107,157,.12);color:#ff8ab5;border:1px solid rgba(255,107,157,.25);}
.badge-boost{background:rgba(201,168,76,.12);color:var(--gold2);border:1px solid rgba(201,168,76,.25);}
.badge-limited{background:rgba(77,187,138,.12);color:#5dd4a0;border:1px solid rgba(77,187,138,.25);}
.badge-ml{background:rgba(52,152,219,.12);color:#60aadb;border:1px solid rgba(52,152,219,.25);}
.badge-ff{background:rgba(255,107,53,.12);color:#ff8860;border:1px solid rgba(255,107,53,.25);}
.badge-aktif{background:rgba(77,187,138,.12);color:var(--success);border:1px solid rgba(77,187,138,.25);}
.badge-nonaktif{background:rgba(224,85,85,.12);color:var(--danger);border:1px solid rgba(224,85,85,.25);}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.58rem 1.05rem;border-radius:10px;
  font-family:'Plus Jakarta Sans',sans-serif;font-size:.8rem;font-weight:600;cursor:pointer;border:none;transition:all .18s;text-decoration:none;}
.btn:hover{transform:translateY(-1px);box-shadow:0 12px 26px rgba(0,0,0,.28);}
.btn-primary{background:linear-gradient(135deg,var(--gold),var(--gold3));color:#0a0c14;font-weight:600;}
.btn-primary:hover{background:linear-gradient(135deg,var(--gold2),var(--gold));color:#0a0c14;}
.btn-danger{background:rgba(224,85,85,.1);color:var(--danger);border:1px solid rgba(224,85,85,.25);}
.btn-danger:hover{background:rgba(224,85,85,.2);}
.btn-ghost{background:var(--surface2);color:var(--muted2);border:1px solid var(--border);}
.btn-ghost:hover{color:var(--text);border-color:var(--border2);}
.btn-success{background:rgba(77,187,138,.1);color:var(--success);border:1px solid rgba(77,187,138,.25);}
.btn-success:hover{background:rgba(77,187,138,.2);}
.btn-warning{background:rgba(224,148,64,.1);color:var(--warning);border:1px solid rgba(224,148,64,.25);}
.btn-warning:hover{background:rgba(224,148,64,.2);}
.btn-sm{padding:.3rem .65rem;font-size:.73rem;}

/* ── FORMS ── */
.form-grid{display:grid;gap:1rem;}.form-grid-2{grid-template-columns:1fr 1fr;}
.form-group{display:flex;flex-direction:column;gap:.4rem;}
label{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.12em;font-weight:600;}
input,select,textarea{background:var(--surface2);border:1px solid var(--border);border-radius:10px;
  padding:.65rem .95rem;color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;font-size:.84rem;
  transition:border-color .15s,width .15s;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--gold3);background:rgba(201,168,76,.04);}
select option{background:var(--surface2);}
textarea{resize:vertical;min-height:80px;}
.form-actions{display:flex;gap:.75rem;margin-top:.5rem;}

/* ── RATE DISPLAY ── */
.rate-display{background:var(--surface2);border:1px solid var(--border);border-radius:10px;
  padding:1rem 1.25rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:1.25rem;}
.rate-value{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:700;color:var(--gold);}

/* ── MODAL ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:1000;
  align-items:center;justify-content:center;backdrop-filter:blur(5px);padding:1rem;}
.modal-overlay.active{display:flex;}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:16px;
  padding:1.75rem;width:100%;max-width:480px;animation:modalIn .2s ease;}
@keyframes modalIn{from{opacity:0;transform:scale(.96) translateY(8px)}to{opacity:1;transform:scale(1) translateY(0)}}

@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.modal-title{font-family:'Cormorant Garamond',serif;font-size:1.2rem;font-weight:700;margin-bottom:1.5rem;color:var(--text);}

/* ── FLASH ── */
.flash-list{list-style:none;margin-bottom:1.25rem;}
.flash{padding:.7rem 1rem;border-radius:8px;font-size:.82rem;margin-bottom:.4rem;font-weight:500;}
.flash-success{background:rgba(77,187,138,.1);border:1px solid rgba(77,187,138,.25);color:var(--success);}
.flash-error{background:rgba(224,85,85,.1);border:1px solid rgba(224,85,85,.25);color:var(--danger);}

/* ── MISC ── */
.empty{text-align:center;padding:3rem;color:var(--muted);font-size:.83rem;}
.note{margin-top:1rem;padding:.9rem 1.25rem;background:var(--surface2);border-radius:8px;border:1px solid var(--border);font-size:.78rem;color:var(--muted);}
.inline-form{display:flex;gap:.5rem;align-items:center;}
.inline-form input{width:auto;min-width:80px;}
.divider{height:1px;background:var(--border);margin:1.25rem 0;}
code{background:var(--surface3);padding:.1rem .4rem;border-radius:4px;font-size:.8rem;color:var(--muted2);}

/* ── MOBILE ── */
@media(max-width:768px){
  .sidebar{transform:translateX(-100%);}
  .sidebar.open{transform:translateX(0);}
  .topbar{display:flex;}
  .main{margin-left:0;}
  .content{padding:1rem;}
  .form-grid-2{grid-template-columns:1fr;}
  .stats-grid{grid-template-columns:1fr 1fr;}
  th,td{padding:.6rem .75rem;}
  .page-title{font-size:1.4rem;}
  table{font-size:.78rem;}
}
@media(max-width:480px){
  .stats-grid{grid-template-columns:1fr;}
}
</style>
</head>
<body>
<!-- Sidebar Overlay -->
<div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>

<!-- Sidebar -->
NAVPLACEHOLDER

<!-- Main -->
<div class="main">
  <!-- Topbar Mobile -->
  <div class="topbar">
    <div class="topbar-logo">CELLYN <span>ADMIN</span></div>
    <button class="hamburger" onclick="toggleSidebar()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
      </svg>
    </button>
  </div>
  <div class="content">
    FLASHPLACEHOLDER
    CONTENTPLACEHOLDER
  </div>
</div>

<script>
function toggleSidebar(){
  document.querySelector('.sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('active');
}
function closeSidebar(){
  document.querySelector('.sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('active');
}
function openModal(id){document.getElementById(id).classList.add('active');}
function closeModal(id){document.getElementById(id).classList.remove('active');}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    document.querySelectorAll('.modal-overlay.active').forEach(m=>m.classList.remove('active'));
    closeSidebar();
  }
});
document.querySelectorAll('.modal-overlay').forEach(m=>{
  m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('active');});
});
</script>
</body>
</html>"""


def render_page(content, **ctx):
    from flask import get_flashed_messages
    nav = ""
    if session.get("logged_in"):
        ep = request.endpoint
        def _a(label, href, icon, ep_name):
            active = "active" if ep == ep_name else ""
            return f'''<a href="{href}" class="nav-item {active}">
              {icon}<span>{label}</span>
            </a>'''
        ico_dash  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'
        ico_ml    = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 3"/></svg>'
        ico_ff    = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>'
        ico_robux = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
        ico_auto  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.8a19.79 19.79 0 01-3.07-8.72A2 2 0 012 1h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 8.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>'
        ico_out   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
        nav = f'''<aside class="sidebar">
  <div class="sidebar-logo">
    <img src="https://i.imgur.com/xp2F452.png" alt="Cellyn">
    <div class="sidebar-logo-text">Cellyn Admin<span>Store Management</span></div>
  </div>
  <nav class="sidebar-nav">
    <div class="nav-section">Menu</div>
    {_a("Dashboard", "/", ico_dash, "index")}
    <div class="nav-section">Produk</div>
    {_a("Mobile Legends", "/ml", ico_ml, "page_ml")}
    {_a("Free Fire", "/ff", ico_ff, "page_ff")}
    {_a("Robux Store", "/robux", ico_robux, "page_robux")}
    {_a("GP Topup", "/gp", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>', "page_gp")}
    <div class="nav-section">Tools</div>
    {_a("Lainnya", "/lainnya", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>', "page_lainnya")}
    {_a("QRIS", "/qr", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3zM17 17h3v3h-3zM14 20h3"/></svg>', "page_qr")}
    {_a("Statistik", "/stats", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>', "page_stats")}
    {_a("Info Layanan", "/service-info", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>', "page_service_info")}
    {_a("Embed Builder", "/embeds", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 10h8M8 14h5"/></svg>', "page_embeds")}
    {_a("AutoPost", "/autopost", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>', "page_autopost")}
  </nav>
  <div class="sidebar-footer">
    <a href="/logout" class="nav-logout">{ico_out}<span>Logout</span></a>
  </div>
</aside>'''
    msgs = get_flashed_messages(with_categories=True)
    flash_html = ""
    if msgs:
        flash_html = '<ul class="flash-list">'
        for cat, msg in msgs:
            flash_html += f'<li class="flash flash-{cat}">{msg}</li>'
        flash_html += '</ul>'
    html = BASE.replace("NAVPLACEHOLDER", nav).replace("FLASHPLACEHOLDER", flash_html).replace("CONTENTPLACEHOLDER", content)
    return render_template_string(html, **ctx)


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password", "").strip() == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Password salah."
    content = f"""
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1rem;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(201,168,76,.12), transparent 60%),
    radial-gradient(1200px 600px at 100% 10%, rgba(92,188,255,.12), transparent 55%),
    #0b0d12;">
  <div style="width:100%;max-width:380px;">
    <div style="text-align:center;margin-bottom:2rem;">
      <img src="https://i.imgur.com/xp2F452.png" alt="Cellyn" style="width:72px;height:72px;border-radius:16px;margin-bottom:1rem;box-shadow:0 8px 32px rgba(201,168,76,.2);">
      <div style="font-family:'Cormorant Garamond',serif;font-size:1.8rem;font-weight:700;letter-spacing:.04em;">Cellyn Admin</div>
      <div style="color:var(--muted);font-size:.75rem;margin-top:.3rem;letter-spacing:.1em;text-transform:uppercase;">Store Management Panel</div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Login</span></div>
      <div style="padding:1.5rem;">
        <form method="post">
          <div class="form-group" style="margin-bottom:1.25rem;">
            <label>Password Admin</label>
            <input type="password" name="password" placeholder="••••••••" autofocus required>
          </div>
          {'<div class="flash flash-error" style="margin-bottom:1rem;">'+error+'</div>' if error else ''}
          <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;padding:.7rem;">
            Masuk
          </button>
        </form>
      </div>
    </div>
  </div>
</div>"""
    return render_page(content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    conn = get_conn()
    ml_count = conn.execute("SELECT COUNT(*) FROM ml_products").fetchone()[0]
    ff_count = conn.execute("SELECT COUNT(*) FROM ff_products").fetchone()[0]
    robux_count = conn.execute("SELECT COUNT(*) FROM robux_products WHERE active=1").fetchone()[0]
    row = conn.execute("SELECT rate FROM robux_rate WHERE id=1").fetchone()
    rate = row[0] if row else 0
    conn.close()
    rate_str = f"Rp {rate:,}" if rate else "Belum diset"
    content = f"""
<div class="page-header">
  <div class="page-title">Dashboard <small>Ringkasan produk aktif</small></div>
</div>
<div class="stats-grid">
  <div class="stat-card ml"><div class="stat-label">Mobile Legends</div>
    <div class="stat-value">{ml_count}</div><div class="stat-sub">produk aktif</div></div>
  <div class="stat-card ff"><div class="stat-label">Free Fire</div>
    <div class="stat-value">{ff_count}</div><div class="stat-sub">produk aktif</div></div>
  <div class="stat-card robux"><div class="stat-label">Robux Store</div>
    <div class="stat-value">{robux_count}</div><div class="stat-sub">item aktif</div></div>
</div>
<div class="card">
  <div class="card-header"><span class="card-title">Rate Robux</span></div>
  <div style="padding:1.5rem;">
    <div class="rate-display">
      <div>
        <div style="font-size:.75rem;color:var(--muted);margin-bottom:.25rem;">Rate saat ini</div>
        <div class="rate-value">{rate_str}<span style="font-size:.9rem;color:var(--muted);font-weight:400">/Robux</span></div>
      </div>
      <form method="post" action="/robux/rate" class="inline-form">
        <input type="number" name="rate" placeholder="Rate baru" min="1" style="width:140px;" required>
        <button type="submit" class="btn btn-primary btn-sm">Update</button>
      </form>
    </div>
  </div>
</div>"""
    return render_page(content)

# ── ML / GAMES ─────────────────────────────────────────────────────────────────
@app.route("/ml")
@login_required
def page_ml():
    conn = get_conn()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS games ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, "
        "name TEXT NOT NULL, color INTEGER DEFAULT 3407872, "
        "needs_server INTEGER DEFAULT 0, id_label TEXT DEFAULT 'Player ID', "
        "active INTEGER DEFAULT 1)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS game_products ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, game_code TEXT NOT NULL, "
        "label TEXT NOT NULL, dm INTEGER NOT NULL DEFAULT 0, "
        "harga INTEGER NOT NULL, active INTEGER DEFAULT 1)"
    )
    conn.commit()
    games = conn.execute("SELECT * FROM games ORDER BY id").fetchall()
    selected_game = request.args.get("game", games[0]["code"] if games else "")
    products = conn.execute(
        "SELECT * FROM game_products WHERE game_code=? ORDER BY dm, id", (selected_game,)
    ).fetchall() if selected_game else []
    conn.close()

    game_tabs = "".join(
        f'<a href="/ml?game={g["code"]}" class="btn {"btn-primary" if g["code"]==selected_game else "btn-ghost"} btn-sm">{g["name"]}</a>'
        for g in games
    )
    rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{i+1}</td>
      <td>{p['label']}</td>
      <td style="color:var(--muted)">{p['dm']}</td>
      <td>Rp {p['harga']:,}</td>
      <td><span style="color:{'var(--success)' if p['active'] else 'var(--danger)'};font-size:.8rem;">{'Aktif' if p['active'] else 'Nonaktif'}</span></td>
      <td><div style="display:flex;gap:.5rem;">
        <button class="btn btn-ghost btn-sm" onclick="openEditProd({p['id']},'{p['label'].replace(chr(39), chr(92)+chr(39))}',{p['dm']},{p['harga']})">Edit</button>
        <form method="post" action="/ml/product/toggle/{p['id']}?game={selected_game}" style="display:inline;">
          <button type="submit" class="btn btn-sm {'btn-danger' if p['active'] else 'btn-success'}">{'Nonaktifkan' if p['active'] else 'Aktifkan'}</button>
        </form>
        <form method="post" action="/ml/product/delete/{p['id']}?game={selected_game}" style="display:inline;" onsubmit="return confirm('Hapus produk ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for i, p in enumerate(products)) or f'<tr><td colspan="6" class="empty">Belum ada produk untuk {selected_game}</td></tr>'

    game_rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{i+1}</td>
      <td><span class="badge badge-ml">{g['code']}</span></td>
      <td>{g['name']}</td>
      <td>{'Ya' if g['needs_server'] else 'Tidak'}</td>
      <td>{g['id_label']}</td>
      <td><span style="color:{'var(--success)' if g['active'] else 'var(--danger)'};font-size:.8rem;">{'Aktif' if g['active'] else 'Nonaktif'}</span></td>
      <td><div style="display:flex;gap:.5rem;">
        <button class="btn btn-ghost btn-sm" onclick="openEditGame({g['id']},'{g['code']}','{g['name'].replace(chr(39),chr(92)+chr(39))}',{g['needs_server']},'{g['id_label'].replace(chr(39),chr(92)+chr(39))}')">Edit</button>
        <form method="post" action="/ml/game/toggle/{g['id']}" style="display:inline;">
          <button type="submit" class="btn btn-sm {'btn-danger' if g['active'] else 'btn-success'}">{'Nonaktifkan' if g['active'] else 'Aktifkan'}</button>
        </form>
      </div></td>
    </tr>""" for i, g in enumerate(games)) or '<tr><td colspan="7" class="empty">Belum ada game</td></tr>'

    game_opts = "".join(
        f'<option value="{g["code"]}" {"selected" if g["code"]==selected_game else ""}>{g["name"]}</option>'
        for g in games
    )
    content = f"""
<div class="page-header">
  <div class="page-title">Topup Game <small>{len(games)} game</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-game')">+ Tambah Game</button>
</div>
<div class="card" style="margin-bottom:1.5rem;"><table>
  <thead><tr><th>#</th><th>Kode</th><th>Nama</th><th>Server ID?</th><th>Label ID</th><th>Status</th><th>Aksi</th></tr></thead>
  <tbody>{game_rows}</tbody>
</table></div>
<div class="page-header" style="margin-top:2rem;">
  <div class="page-title">Produk <small>filter per game</small></div>
  <div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;">{game_tabs}
    <button class="btn btn-primary btn-sm" onclick="openModal('modal-add-prod')">+ Tambah Produk</button>
  </div>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Label</th><th>DM/Qty</th><th>Harga</th><th>Status</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<div class="modal-overlay" id="modal-add-game"><div class="modal">
  <div class="modal-title">Tambah Game</div>
  <form method="post" action="/ml/game/add">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Kode Game</label><input type="text" name="code" placeholder="contoh: PUBG" required></div>
      <div class="form-group"><label>Nama Game</label><input type="text" name="name" placeholder="contoh: PUBG Mobile" required></div>
    </div>
    <div class="form-grid form-grid-2" style="margin-top:1rem;">
      <div class="form-group"><label>Label ID Player</label><input type="text" name="id_label" placeholder="contoh: Player ID PUBG" required></div>
      <div class="form-group"><label>Butuh Server ID?</label><select name="needs_server"><option value="0">Tidak</option><option value="1">Ya</option></select></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-game')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-game"><div class="modal">
  <div class="modal-title">Edit Game</div>
  <form method="post" action="/ml/game/edit">
    <input type="hidden" name="id" id="edit-game-id">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Kode Game</label><input type="text" name="code" id="edit-game-code" required></div>
      <div class="form-group"><label>Nama Game</label><input type="text" name="name" id="edit-game-name" required></div>
    </div>
    <div class="form-grid form-grid-2" style="margin-top:1rem;">
      <div class="form-group"><label>Label ID Player</label><input type="text" name="id_label" id="edit-game-idlabel" required></div>
      <div class="form-group"><label>Butuh Server ID?</label><select name="needs_server" id="edit-game-server"><option value="0">Tidak</option><option value="1">Ya</option></select></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-game')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-add-prod"><div class="modal">
  <div class="modal-title">Tambah Produk</div>
  <form method="post" action="/ml/product/add?game={selected_game}">
    <div class="form-group"><label>Game</label><select name="game_code">{game_opts}</select></div>
    <div class="form-group" style="margin-top:1rem;"><label>Label Produk</label><input type="text" name="label" placeholder="contoh: 86 Diamond" required></div>
    <div class="form-grid form-grid-2" style="margin-top:1rem;">
      <div class="form-group"><label>DM / Qty</label><input type="number" name="dm" placeholder="contoh: 86" min="0" required></div>
      <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" placeholder="contoh: 15000" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-prod')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-prod"><div class="modal">
  <div class="modal-title">Edit Produk</div>
  <form method="post" action="/ml/product/edit?game={selected_game}">
    <input type="hidden" name="id" id="edit-prod-id">
    <div class="form-group"><label>Label Produk</label><input type="text" name="label" id="edit-prod-label" required></div>
    <div class="form-grid form-grid-2" style="margin-top:1rem;">
      <div class="form-group"><label>DM / Qty</label><input type="number" name="dm" id="edit-prod-dm" min="0" required></div>
      <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" id="edit-prod-harga" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-prod')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditGame(id,code,name,needs,idlabel){{
  document.getElementById('edit-game-id').value=id;
  document.getElementById('edit-game-code').value=code;
  document.getElementById('edit-game-name').value=name;
  document.getElementById('edit-game-idlabel').value=idlabel;
  document.getElementById('edit-game-server').value=needs;
  openModal('modal-edit-game');
}}
function openEditProd(id,label,dm,harga){{
  document.getElementById('edit-prod-id').value=id;
  document.getElementById('edit-prod-label').value=label;
  document.getElementById('edit-prod-dm').value=dm;
  document.getElementById('edit-prod-harga').value=harga;
  openModal('modal-edit-prod');
}}
</script>"""
    content = _service_info_widget("ml", "Topup Game (ML/FF/WDP)") + content
    return render_page(content)


@app.route("/ml/game/add", methods=["POST"])
@login_required
def ml_game_add():
    code = request.form.get("code", "").strip().upper()
    name = request.form.get("name", "").strip()
    id_label = request.form.get("id_label", "Player ID").strip()
    needs_server = 1 if request.form.get("needs_server") == "1" else 0
    if not code or not name:
        flash("Kode dan nama game wajib diisi.", "error")
        return redirect(url_for("page_ml"))
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO games (code, name, needs_server, id_label) VALUES (?,?,?,?)",
            (code, name, needs_server, id_label)
        )
        conn.commit()
        flash(f"Game {name} berhasil ditambahkan.", "success")
    except Exception:
        flash(f"Kode game {code} sudah ada.", "error")
    conn.close()
    return redirect(url_for("page_ml"))


@app.route("/ml/game/edit", methods=["POST"])
@login_required
def ml_game_edit():
    gid = safe_int(request.form.get("id"), min_val=1)
    code = request.form.get("code", "").strip().upper()
    name = request.form.get("name", "").strip()
    id_label = request.form.get("id_label", "Player ID").strip()
    needs_server = 1 if request.form.get("needs_server") == "1" else 0
    if not gid or not code or not name:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ml"))
    conn = get_conn()
    conn.execute(
        "UPDATE games SET code=?, name=?, needs_server=?, id_label=? WHERE id=?",
        (code, name, needs_server, id_label, gid)
    )
    conn.commit()
    conn.close()
    flash("Game berhasil diupdate.", "success")
    return redirect(url_for("page_ml"))


@app.route("/ml/game/toggle/<int:gid>", methods=["POST"])
@login_required
def ml_game_toggle(gid):
    conn = get_conn()
    conn.execute("UPDATE games SET active = 1 - active WHERE id=?", (gid,))
    conn.commit()
    conn.close()
    flash("Status game diubah.", "success")
    return redirect(url_for("page_ml"))


@app.route("/ml/product/add", methods=["POST"])
@login_required
def ml_product_add():
    game_code = request.form.get("game_code", "").strip().upper()
    label = request.form.get("label", "").strip()
    dm = safe_int(request.form.get("dm"), min_val=0)
    harga = safe_int(request.form.get("harga"), min_val=1)
    if not game_code or not label or dm is None or harga is None:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ml", game=game_code))
    conn = get_conn()
    conn.execute(
        "INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
        (game_code, label, dm, harga)
    )
    conn.commit()
    conn.close()
    flash(f"Produk {label} berhasil ditambahkan.", "success")
    return redirect(url_for("page_ml", game=game_code))


@app.route("/ml/product/edit", methods=["POST"])
@login_required
def ml_product_edit():
    pid = safe_int(request.form.get("id"), min_val=1)
    label = request.form.get("label", "").strip()
    dm = safe_int(request.form.get("dm"), min_val=0)
    harga = safe_int(request.form.get("harga"), min_val=1)
    game_code = request.args.get("game", "")
    if not pid or not label or dm is None or harga is None:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ml", game=game_code))
    conn = get_conn()
    conn.execute(
        "UPDATE game_products SET label=?, dm=?, harga=? WHERE id=?", (label, dm, harga, pid)
    )
    conn.commit()
    conn.close()
    flash("Produk berhasil diupdate.", "success")
    return redirect(url_for("page_ml", game=game_code))


@app.route("/ml/product/toggle/<int:pid>", methods=["POST"])
@login_required
def ml_product_toggle(pid):
    game_code = request.args.get("game", "")
    conn = get_conn()
    conn.execute("UPDATE game_products SET active = 1 - active WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    flash("Status produk diubah.", "success")
    return redirect(url_for("page_ml", game=game_code))


@app.route("/ml/product/delete/<int:pid>", methods=["POST"])
@login_required
def ml_product_delete(pid):
    game_code = request.args.get("game", "")
    conn = get_conn()
    conn.execute("DELETE FROM game_products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    flash("Produk berhasil dihapus.", "success")
    return redirect(url_for("page_ml", game=game_code))


# Redirect /ff ke /ml untuk backwards compatibility
@app.route("/ff")
@login_required
def page_ff():
    return redirect(url_for("page_ml", game="FF"))


# ── ROBUX ──────────────────────────────────────────────────────────────────────
@app.route("/robux")
@login_required
def page_robux():
    conn = get_conn()
    products = conn.execute("SELECT * FROM robux_products ORDER BY category, id").fetchall()
    categories = [r[0] for r in conn.execute(
        "SELECT DISTINCT category FROM robux_products ORDER BY category").fetchall()]
    conn.close()
    cat_opts = "".join(f'<option value="{c}">' for c in categories)
    rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{p['id']}</td>
      <td><span class="badge badge-{p['category'].lower()}">{p['category']}</span></td>
      <td>{p['name']}</td>
      <td style="color:var(--accent)">{p['robux']:,} Robux</td>
      <td><span style="color:{'var(--success)' if p['active'] else 'var(--danger)'};font-size:.8rem;">{'Aktif' if p['active'] else 'Nonaktif'}</span></td>
      <td><div style="display:flex;gap:.5rem;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm" onclick="openEditRobux({p['id']},'{p['category']}','{p['name'].replace(chr(39), chr(92)+chr(39))}',{p['robux']})">Edit</button>
        <form method="post" action="/robux/toggle/{p['id']}" style="display:inline;">
          <button type="submit" class="btn btn-sm {'btn-danger' if p['active'] else 'btn-success'}">{'Nonaktifkan' if p['active'] else 'Aktifkan'}</button>
        </form>
        <form method="post" action="/robux/delete/{p['id']}" style="display:inline;" onsubmit="return confirm('Hapus item ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for p in products) or '<tr><td colspan="6" class="empty">Belum ada produk Robux</td></tr>'
    content = f"""
<div class="page-header">
  <div class="page-title">Robux Store <small>{len(products)} item</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-robux')">+ Tambah Item</button>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Kategori</th><th>Nama Item</th><th>Robux</th><th>Status</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<datalist id="cat-list">{cat_opts}</datalist>
<div class="modal-overlay" id="modal-add-robux"><div class="modal">
  <div class="modal-title">Tambah Item Robux</div>
  <form method="post" action="/robux/add">
    <div class="form-grid">
      <div class="form-group"><label>Kategori</label>
        <input type="text" name="category" placeholder="GAMEPASS / CRATE / BOOST / LIMITED" required list="cat-list"></div>
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Nama Item</label><input type="text" name="name" placeholder="contoh: VIP + LUCK" required></div>
        <div class="form-group"><label>Harga Robux</label><input type="number" name="robux" placeholder="contoh: 445" min="1" required></div>
      </div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-robux')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-robux"><div class="modal">
  <div class="modal-title">Edit Item Robux</div>
  <form method="post" action="/robux/edit">
    <input type="hidden" name="id" id="edit-robux-id">
    <div class="form-grid">
      <div class="form-group"><label>Kategori</label><input type="text" name="category" id="edit-robux-cat" list="cat-list" required></div>
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Nama Item</label><input type="text" name="name" id="edit-robux-name" required></div>
        <div class="form-group"><label>Harga Robux</label><input type="number" name="robux" id="edit-robux-robux" min="1" required></div>
      </div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-robux')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditRobux(id,cat,name,robux){{
  document.getElementById('edit-robux-id').value=id;
  document.getElementById('edit-robux-cat').value=cat;
  document.getElementById('edit-robux-name').value=name;
  document.getElementById('edit-robux-robux').value=robux;
  openModal('modal-edit-robux');
}}
</script>"""
    content = _service_info_widget("robux", "Robux Store") + content
    return render_page(content)


@app.route("/robux/add", methods=["POST"])
@login_required
def robux_add():
    category = request.form.get("category", "").strip().upper()
    name = request.form.get("name", "").strip()
    robux = safe_int(request.form.get("robux"), min_val=1)
    if not category or not name or robux is None:
        flash("Input tidak valid. Semua field wajib diisi dengan benar.", "error")
        return redirect(url_for("page_robux"))
    conn = get_conn()
    conn.execute("INSERT INTO robux_products (category, name, robux) VALUES (?,?,?)", (category, name, robux))
    conn.commit(); conn.close()
    flash(f"Item {name} berhasil ditambahkan.", "success")
    return redirect(url_for("page_robux"))


@app.route("/robux/edit", methods=["POST"])
@login_required
def robux_edit():
    pid = safe_int(request.form.get("id"), min_val=1)
    category = request.form.get("category", "").strip().upper()
    name = request.form.get("name", "").strip()
    robux = safe_int(request.form.get("robux"), min_val=1)
    if pid is None or not category or not name or robux is None:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_robux"))
    conn = get_conn()
    conn.execute("UPDATE robux_products SET category=?, name=?, robux=? WHERE id=?", (category, name, robux, pid))
    conn.commit(); conn.close()
    flash("Item Robux berhasil diupdate.", "success")
    return redirect(url_for("page_robux"))


@app.route("/robux/toggle/<int:pid>", methods=["POST"])
@login_required
def robux_toggle(pid):
    conn = get_conn()
    row = conn.execute("SELECT active FROM robux_products WHERE id=?", (pid,)).fetchone()
    if row:
        conn.execute("UPDATE robux_products SET active=? WHERE id=?", (0 if row[0] else 1, pid))
        conn.commit()
    conn.close()
    return redirect(url_for("page_robux"))


@app.route("/robux/delete/<int:pid>", methods=["POST"])
@login_required
def robux_delete(pid):
    conn = get_conn()
    conn.execute("DELETE FROM robux_products WHERE id=?", (pid,))
    conn.commit(); conn.close()
    flash("Item Robux berhasil dihapus.", "success")
    return redirect(url_for("page_robux"))


@app.route("/robux/rate", methods=["POST"])
@login_required
def robux_rate():
    rate = safe_int(request.form.get("rate"), min_val=1)
    if rate is None:
        flash("Rate tidak valid. Masukkan angka lebih dari 0.", "error")
        return redirect(url_for("index"))
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO robux_rate (id, rate) VALUES (1, ?)", (rate,))
    conn.commit(); conn.close()
    flash(f"Rate berhasil diupdate ke Rp {rate:,}/Robux.", "success")
    return redirect(url_for("index"))


# ── GP TOPUP ──────────────────────────────────────────────────────────────────

@app.route("/gp")
@login_required
def page_gp():
    from utils.db import get_conn as _gc
    conn = _gc()
    tickets = conn.execute("SELECT * FROM gp_tickets ORDER BY opened_at DESC LIMIT 50").fetchall()
    conn.close()

    import os
    gp_rate = int(__import__("sqlite3").connect(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")
    ).execute("SELECT value FROM bot_state WHERE key='gp_rate'").fetchone()[0] or 0)

    rows = ""
    for t in tickets:
        paid = "✅ Lunas" if t["paid"] else "⏳ Belum bayar"
        link = f'<a href="{t["gp_link"]}" target="_blank">Link</a>' if t["gp_link"] else "-"
        rows += f"""<tr>
            <td><code>{t['channel_id']}</code></td>
            <td><code>{t['user_id']}</code></td>
            <td>{t['robux']} Robux</td>
            <td>{t['gp_price']} Robux</td>
            <td>Rp {t['total']:,}</td>
            <td>{paid}</td>
            <td>{link}</td>
            <td style='font-size:12px'>{(t['opened_at'] or '')[:16]}</td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='8' class='empty'>Belum ada tiket GP.</td></tr>"

    content = f"""
<div class="page-header">
  <h2 class="page-title">🎮 GP Topup<small>Topup Robux via Gamepass</small></h2>
</div>

<div class="stats-grid">
  <div class="stat-card gp">
    <div class="stat-label">Rate GP</div>
    <div class="stat-value" style="font-size:1.4rem">Rp {gp_rate:,}</div>
    <div class="stat-sub">per Robux</div>
  </div>
</div>

<div class="card">
  <div class="card-header">
    <span class="card-title">Ubah Rate GP</span>
  </div>
  <div class="card-body">
    <form method="post" action="/gp/rate" style="display:flex;gap:10px;align-items:flex-end">
      <div class="form-group" style="flex:1">
        <label>Rate Baru (Rp per Robux)</label>
        <input type="number" name="rate" min="1" value="{gp_rate}" required>
      </div>
      <button type="submit" class="btn btn-primary">Simpan & Refresh Catalog</button>
    </form>
    <p class="note" style="margin-top:10px">Setelah simpan, catalog channel GP akan otomatis diperbarui. Gunakan <code>!gpcatalog</code> jika perlu refresh manual.</p>
  </div>
</div>

<div class="card">
  <div class="card-header"><span class="card-title">Riwayat Tiket GP (50 terakhir)</span></div>
  <div class="card-body" style="padding:0">
    <table>
      <thead><tr>
        <th>Channel ID</th><th>User ID</th><th>Robux</th>
        <th>Harga GP</th><th>Total</th><th>Status</th><th>Link GP</th><th>Waktu</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>
"""
    return render_page(content)


@app.route("/gp/rate", methods=["POST"])
@login_required
def gp_rate_save():
    import sqlite3 as _sq, os
    rate = safe_int(request.form.get("rate"), min_val=1)
    if not rate:
        flash("Rate tidak valid.", "error")
        return redirect(url_for("page_gp"))
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")
    conn = _sq.connect(db_path)
    conn.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES ('gp_rate', ?)", (str(rate),))
    conn.commit()
    conn.close()
    flash(f"Rate GP diubah ke Rp {rate:,}/Robux. Refresh catalog via !gpcatalog di Discord.", "success")
    return redirect(url_for("page_gp"))


# ── STATISTIK ─────────────────────────────────────────────────────────────────
@app.route("/stats")
def page_stats():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()

    # Total per layanan
    c.execute("SELECT layanan, COUNT(*) as total, SUM(nominal) as omzet FROM transaction_log GROUP BY layanan")
    per_layanan = {row["layanan"]: {"total": row["total"], "omzet": row["omzet"] or 0} for row in c.fetchall()}

    # Total keseluruhan
    c.execute("SELECT COUNT(*) as total, SUM(nominal) as omzet FROM transaction_log")
    row = c.fetchone()
    grand_total = row["total"] or 0
    grand_omzet = row["omzet"] or 0

    # 7 hari terakhir (harian)
    c.execute("""
        SELECT date(closed_at) as tgl, COUNT(*) as total, SUM(nominal) as omzet
        FROM transaction_log
        WHERE closed_at >= date('now', '-6 days')
        GROUP BY date(closed_at)
        ORDER BY tgl ASC
    """)
    harian = c.fetchall()

    # Produk terlaris (top 5)
    c.execute("""
        SELECT item, COUNT(*) as total
        FROM transaction_log
        WHERE item IS NOT NULL AND item != '-'
        GROUP BY item ORDER BY total DESC LIMIT 5
    """)
    terlaris = c.fetchall()

    # Jam tersibuk
    c.execute("""
        SELECT strftime('%H', closed_at) as jam, COUNT(*) as total
        FROM transaction_log
        GROUP BY jam ORDER BY total DESC LIMIT 5
    """)
    peak_hours = c.fetchall()

    # 30 hari terakhir
    c.execute("""
        SELECT date(closed_at) as tgl, COUNT(*) as total, SUM(nominal) as omzet
        FROM transaction_log
        WHERE closed_at >= date('now', '-29 days')
        GROUP BY date(closed_at)
        ORDER BY tgl ASC
    """)
    bulanan = c.fetchall()

    conn.close()

    label_map = {"midman":"Midman Trade","robux":"Robux","ml":"ML","ff":"Free Fire","jualbeli":"Jual Beli","cloudphone":"Cloud Phone","nitro":"Discord Nitro","scaset":"SC/Aset Game"}

    # Stat cards
    layanan_list = [
        ("midman","💼","#7c5cbf"),("robux","🎮","#E91E63"),
        ("ml","💎","#3498DB"),("ff","🔥","#FF6B35"),("jualbeli","🤝","#4dbb8a"),
        ("cloudphone","📱","#00BFFF"),("nitro","💜","#5865F2"),("scaset","🎮","#F0A500")
    ]
    stat_cards = ""
    for key, ico, color in layanan_list:
        d = per_layanan.get(key, {"total":0,"omzet":0})
        stat_cards += f"""
        <div class="stat-card" style="border-top:2px solid {color}20;position:relative;overflow:hidden;">
          <div style="position:absolute;top:-15px;right:-15px;font-size:3rem;opacity:.06;">{ico}</div>
          <div style="font-size:1.6rem;margin-bottom:.2rem;">{ico}</div>
          <div class="stat-label">{label_map[key]}</div>
          <div class="stat-value" style="color:{color};">{d['total']}</div>
          <div class="stat-sub">Rp {d['omzet']:,}</div>
        </div>"""

    # Chart data harian (7 hari)
    from datetime import date, timedelta
    today = date.today()
    days7 = [(today - timedelta(days=i)).isoformat() for i in range(6,-1,-1)]
    harian_map = {row["tgl"]: {"total": row["total"], "omzet": row["omzet"] or 0} for row in harian}
    chart_labels = [d[-5:] for d in days7]
    chart_total  = [harian_map.get(d, {}).get("total", 0) for d in days7]
    chart_omzet  = [harian_map.get(d, {}).get("omzet", 0) for d in days7]

    # Chart data 30 hari
    days30 = [(today - timedelta(days=i)).isoformat() for i in range(29,-1,-1)]
    bulanan_map = {row["tgl"]: {"total": row["total"], "omzet": row["omzet"] or 0} for row in bulanan}
    chart30_labels = [d[-5:] for d in days30]
    chart30_total  = [bulanan_map.get(d, {}).get("total", 0) for d in days30]

    # Tabel terlaris
    terlaris_html = ""
    for i, row in enumerate(terlaris, 1):
        terlaris_html += f"<tr><td>{i}</td><td>{row['item']}</td><td>{row['total']}</td></tr>"
    if not terlaris_html:
        terlaris_html = "<tr><td colspan=3 class='empty'>Belum ada data</td></tr>"

    # Peak hours
    peak_html = ""
    for row in peak_hours:
        peak_html += f"<tr><td>{row['jam']}:00</td><td>{row['total']} transaksi</td></tr>"
    if not peak_html:
        peak_html = "<tr><td colspan=2 class='empty'>Belum ada data</td></tr>"

    content = f"""
<div class="page-header">
  <div class="page-title">Statistik<small>Data transaksi sukses semua layanan</small></div>
</div>

<!-- Summary Cards -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">
  <div class="stat-card" style="border-top:2px solid var(--accent);">
    <div class="stat-label">Total Transaksi</div>
    <div class="stat-value">{grand_total}</div>
    <div class="stat-sub">Semua layanan</div>
  </div>
  <div class="stat-card" style="border-top:2px solid var(--success);">
    <div class="stat-label">Total Omzet</div>
    <div class="stat-value" style="font-size:1.4rem;">Rp {grand_omzet:,}</div>
    <div class="stat-sub">Semua layanan</div>
  </div>
</div>

<!-- Per Layanan -->
<div class="stats-grid" style="margin-bottom:1.5rem;">
  {stat_cards}
</div>

<!-- Charts -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">
  <div class="card">
    <div class="card-header"><span class="card-title">📈 Transaksi 7 Hari</span></div>
    <div class="card-body"><canvas id="chart7" height="180"></canvas></div>
  </div>
  <div class="card">
    <div class="card-header"><span class="card-title">📊 Transaksi 30 Hari</span></div>
    <div class="card-body"><canvas id="chart30" height="180"></canvas></div>
  </div>
</div>

<!-- Tabel bawah -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
  <div class="card">
    <div class="card-header"><span class="card-title">🏆 Produk Terlaris</span></div>
    <table>
      <thead><tr><th>#</th><th>Item</th><th>Terjual</th></tr></thead>
      <tbody>{terlaris_html}</tbody>
    </table>
  </div>
  <div class="card">
    <div class="card-header"><span class="card-title">🕐 Jam Tersibuk</span></div>
    <table>
      <thead><tr><th>Jam</th><th>Transaksi</th></tr></thead>
      <tbody>{peak_html}</tbody>
    </table>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script>
const chartDefaults = {{
  responsive: true,
  plugins: {{ legend: {{ display: false }} }},
  scales: {{
    x: {{ grid: {{ color: 'rgba(255,255,255,.04)' }}, ticks: {{ color: '#6a7a95', font: {{ size: 10 }} }} }},
    y: {{ grid: {{ color: 'rgba(255,255,255,.04)' }}, ticks: {{ color: '#6a7a95', font: {{ size: 10 }} }}, beginAtZero: true }}
  }}
}};
new Chart(document.getElementById('chart7'), {{
  type: 'bar',
  data: {{
    labels: {chart_labels},
    datasets: [{{ data: {chart_total}, backgroundColor: 'rgba(124,92,191,.5)', borderColor: '#7c5cbf', borderWidth: 1, borderRadius: 4 }}]
  }},
  options: chartDefaults
}});
new Chart(document.getElementById('chart30'), {{
  type: 'line',
  data: {{
    labels: {chart30_labels},
    datasets: [{{ data: {chart30_total}, borderColor: '#4dbb8a', backgroundColor: 'rgba(77,187,138,.1)', borderWidth: 2, pointRadius: 2, fill: true, tension: .4 }}]
  }},
  options: chartDefaults
}});
</script>"""
    return render_page(content)


# ── LAINNYA (Cloud Phone & Nitro) ─────────────────────────────────────────────
@app.route("/lainnya")
def page_lainnya():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, category, name, harga, active FROM lainnya_products ORDER BY category, id")
    products = [dict(r) for r in c.fetchall()]
    conn.close()

    # Group by category
    categories = {}
    for p in products:
        categories.setdefault(p["category"], []).append(p)

    cat_html = ""
    for cat, items in categories.items():
        rows = ""
        for p in items:
            status = "Aktif" if p["active"] else "Nonaktif"
            status_badge = f'<span style="color:{"#4dbb8a" if p["active"] else "#e74c3c"};font-size:.8rem;">{status}</span>'
            rows += f"""
            <tr>
              <td>{p["id"]}</td>
              <td>{p["name"]}</td>
              <td>Rp {p["harga"]:,}</td>
              <td>{status_badge}</td>
              <td>
                <div style="display:flex;gap:.4rem;">
                  <a href="/lainnya/edit/{p["id"]}" class="btn-sm btn-primary">Edit</a>
                  <a href="/lainnya/toggle/{p["id"]}" class="btn-sm {"btn-warn" if p["active"] else "btn-success"}">{"Nonaktifkan" if p["active"] else "Aktifkan"}</a>
                  <a href="/lainnya/delete/{p["id"]}" class="btn-sm btn-danger" onclick="return confirm('Hapus item ini?')">Hapus</a>
                </div>
              </td>
            </tr>"""
        cat_html += f"""
        <div class="card" style="margin-bottom:1rem;">
          <div class="card-header"><span class="card-title">{cat}</span></div>
          <table>
            <thead><tr><th>ID</th><th>Nama</th><th>Harga</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    content = f"""
<div class="page-header">
  <div class="page-title">Lainnya<small>Kelola produk Cloud Phone & Discord Nitro</small></div>
</div>

<!-- Tambah Produk -->
<div class="card" style="margin-bottom:1.5rem;">
  <div class="card-header"><span class="card-title">➕ Tambah Produk</span></div>
  <div class="card-body">
    <form method="POST" action="/lainnya/add" style="display:grid;grid-template-columns:2fr 2fr 1fr 1fr auto;gap:.75rem;align-items:end;">
      <div>
        <label style="font-size:.8rem;color:#6a7a95;display:block;margin-bottom:.3rem;">Kategori</label>
        <input name="category" placeholder="Contoh: CLOUD PHONE" style="width:100%;padding:.5rem .75rem;background:#131622;border:1px solid #1e2435;border-radius:6px;color:#e2e8f0;font-size:.9rem;">
      </div>
      <div>
        <label style="font-size:.8rem;color:#6a7a95;display:block;margin-bottom:.3rem;">Nama Item</label>
        <input name="name" placeholder="Contoh: REDFINGER VIP 7DAY" style="width:100%;padding:.5rem .75rem;background:#131622;border:1px solid #1e2435;border-radius:6px;color:#e2e8f0;font-size:.9rem;">
      </div>
      <div>
        <label style="font-size:.8rem;color:#6a7a95;display:block;margin-bottom:.3rem;">Harga (Rp)</label>
        <input name="harga" type="number" placeholder="20500" style="width:100%;padding:.5rem .75rem;background:#131622;border:1px solid #1e2435;border-radius:6px;color:#e2e8f0;font-size:.9rem;">
      </div>
      <button type="submit" class="btn-primary" style="padding:.5rem 1rem;height:fit-content;margin-top:auto;">Tambah</button>
    </form>
  </div>
</div>

<!-- Daftar Produk -->
{cat_html if cat_html else '<div class="card"><div class="card-body empty">Belum ada produk</div></div>'}
"""
    return render_page(content)


@app.route("/lainnya/add", methods=["POST"])
def lainnya_add():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    category = request.form.get("category", "").strip().upper()
    name = request.form.get("name", "").strip().upper()
    harga = request.form.get("harga", "0").strip()
    if not category or not name or not harga:
        flash("Semua field wajib diisi!", "error")
        return redirect(url_for("page_lainnya"))
    try:
        harga_int = int(harga)
    except ValueError:
        flash("Harga harus berupa angka!", "error")
        return redirect(url_for("page_lainnya"))
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO lainnya_products (category, name, harga, active) VALUES (?,?,?,1)",
              (category, name, harga_int))
    conn.commit()
    conn.close()
    flash(f"Produk {name} berhasil ditambahkan!", "success")
    return redirect(url_for("page_lainnya"))


@app.route("/lainnya/edit/<int:pid>", methods=["GET", "POST"])
def lainnya_edit(pid):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    if request.method == "POST":
        category = request.form.get("category", "").strip().upper()
        name = request.form.get("name", "").strip().upper()
        harga = request.form.get("harga", "0").strip()
        try:
            harga_int = int(harga)
        except ValueError:
            harga_int = 0
        c.execute("UPDATE lainnya_products SET category=?, name=?, harga=? WHERE id=?",
                  (category, name, harga_int, pid))
        conn.commit()
        conn.close()
        flash("Produk berhasil diupdate!", "success")
        return redirect(url_for("page_lainnya"))
    c.execute("SELECT * FROM lainnya_products WHERE id=?", (pid,))
    p = dict(c.fetchone())
    conn.close()
    content = f"""
<div class="page-header">
  <div class="page-title">Edit Produk<small>{p["name"]}</small></div>
</div>
<div class="card" style="max-width:500px;">
  <div class="card-body">
    <form method="POST" style="display:flex;flex-direction:column;gap:1rem;">
      <div>
        <label style="font-size:.8rem;color:#6a7a95;display:block;margin-bottom:.3rem;">Kategori</label>
        <input name="category" value="{p["category"]}" style="width:100%;padding:.5rem .75rem;background:#131622;border:1px solid #1e2435;border-radius:6px;color:#e2e8f0;">
      </div>
      <div>
        <label style="font-size:.8rem;color:#6a7a95;display:block;margin-bottom:.3rem;">Nama Item</label>
        <input name="name" value="{p["name"]}" style="width:100%;padding:.5rem .75rem;background:#131622;border:1px solid #1e2435;border-radius:6px;color:#e2e8f0;">
      </div>
      <div>
        <label style="font-size:.8rem;color:#6a7a95;display:block;margin-bottom:.3rem;">Harga (Rp)</label>
        <input name="harga" type="number" value="{p["harga"]}" style="width:100%;padding:.5rem .75rem;background:#131622;border:1px solid #1e2435;border-radius:6px;color:#e2e8f0;">
      </div>
      <div style="display:flex;gap:.75rem;">
        <button type="submit" class="btn-primary">Simpan</button>
        <a href="/lainnya" class="btn-sm" style="padding:.5rem 1rem;background:#1e2435;border-radius:6px;color:#e2e8f0;text-decoration:none;">Batal</a>
      </div>
    </form>
  </div>
</div>"""
    return render_page(content)


@app.route("/lainnya/toggle/<int:pid>")
def lainnya_toggle(pid):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE lainnya_products SET active = 1 - active WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return redirect(url_for("page_lainnya"))


@app.route("/lainnya/delete/<int:pid>")
def lainnya_delete(pid):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM lainnya_products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    flash("Produk berhasil dihapus!", "success")
    return redirect(url_for("page_lainnya"))


# ── QR SLOTS ───────────────────────────────────────────────────────────────────
@app.route("/qr")
@login_required
def page_qr():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS qr_slots (
        slot INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '',
        detail TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1
    )""")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(qr_slots)").fetchall()]
    if "detail" not in cols:
        conn.execute("ALTER TABLE qr_slots ADD COLUMN detail TEXT NOT NULL DEFAULT ''")
    for i in range(1, 11):
        conn.execute(
            "INSERT OR IGNORE INTO qr_slots (slot, label, detail, url) VALUES (?,?,?,?)",
            (i, f"QRIS {i}", "", "")
        )
    conn.commit()
    slots = conn.execute("SELECT * FROM qr_slots ORDER BY slot").fetchall()
    conn.close()

    def _js(s):
        s = s or ""
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")

    def _h(s):
        return html.escape(s or "")

    rows = "".join(f"""<tr>
      <td style="color:var(--muted);font-weight:600">!qr{s['slot']}</td>
      <td>{_h(s['label'])}</td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted);font-size:.85rem">{_h(s['detail'])}</td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted);font-size:.85rem">{_h(s['url']) if s['url'] else '<span style="color:#555">Belum diset</span>'}</td>
      <td>{'<img src="'+_h(s['url'])+'" style="height:48px;border-radius:6px">' if s['url'] else ''}</td>
      <td><span style="color:{'var(--success)' if s['active'] else 'var(--danger)'};font-size:.85rem">{'Aktif' if s['active'] else 'Nonaktif'}</span></td>
      <td><div style="display:flex;gap:.4rem">
        <button class="btn btn-ghost btn-sm" onclick="openEditQR({s['slot']},'{_js(s['label'])}','{_js(s['detail'])}','{_js(s['url'])}')">Edit</button>
        <form method="post" action="/qr/toggle/{s['slot']}" style="display:inline">
          <button class="btn btn-sm {'btn-danger' if s['active'] else 'btn-success'}">{'Nonaktifkan' if s['active'] else 'Aktifkan'}</button>
        </form>
      </div></td>
    </tr>""" for s in slots)

    content = f"""
<div class="page-header">
  <div class="page-title">QRIS Slots <small>!qr1 — !qr{len(slots)}</small></div>
</div>
<div class="card"><table>
  <thead><tr><th>Command</th><th>Label</th><th>Detail</th><th>URL Gambar</th><th>Preview</th><th>Status</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<div class="modal-overlay" id="modal-edit-qr"><div class="modal">
  <div class="modal-title">Edit Slot QRIS</div>
  <form method="post" action="/qr/edit">
    <input type="hidden" name="slot" id="edit-qr-slot">
    <div class="form-group"><label>Label</label>
      <input type="text" name="label" id="edit-qr-label" placeholder="contoh: QRIS Admin 1" required>
    </div>
    <div class="form-group" style="margin-top:1rem"><label>Detail</label>
      <input type="text" name="detail" id="edit-qr-detail" placeholder="contoh: QRIS GoPay / Transfer BCA">
    </div>
    <div class="form-group" style="margin-top:1rem"><label>URL Gambar QR</label>
      <input type="text" name="url" id="edit-qr-url" placeholder="https://i.imgur.com/xxx.png">
      <small style="color:var(--muted)">Upload gambar ke Imgur/ImgBB lalu paste URL-nya di sini</small>
    </div>
    <div class="form-actions" style="margin-top:1.5rem">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-qr')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditQR(slot, label, detail, url) {{
  document.getElementById('edit-qr-slot').value = slot;
  document.getElementById('edit-qr-label').value = label;
  document.getElementById('edit-qr-detail').value = detail || '';
  document.getElementById('edit-qr-url').value = url;
  openModal('modal-edit-qr');
}}
</script>"""
    return render_page(content)


@app.route("/qr/edit", methods=["POST"])
@login_required
def qr_edit():
    slot = safe_int(request.form.get("slot"), min_val=1)
    label = request.form.get("label", "").strip()
    detail = request.form.get("detail", "").strip()
    url = request.form.get("url", "").strip()
    if not slot or not label:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_qr"))
    conn = get_conn()
    conn.execute("UPDATE qr_slots SET label=?, detail=?, url=? WHERE slot=?", (label, detail, url, slot))
    conn.commit()
    conn.close()
    flash(f"Slot !qr{slot} berhasil diupdate.", "success")
    return redirect(url_for("page_qr"))


@app.route("/qr/toggle/<int:slot>", methods=["POST"])
@login_required
def qr_toggle(slot):
    conn = get_conn()
    conn.execute("UPDATE qr_slots SET active = 1 - active WHERE slot=?", (slot,))
    conn.commit()
    conn.close()
    flash(f"Status slot !qr{slot} diubah.", "success")
    return redirect(url_for("page_qr"))




# ── SERVICE INFO (Deskripsi, S&K, Cara Bayar per Layanan) ─────────────────────

def _get_service_info_admin(service_key):
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS service_info (
        service_key TEXT PRIMARY KEY,
        description TEXT DEFAULT '',
        terms TEXT DEFAULT '',
        payment_info TEXT DEFAULT ''
    )""")
    conn.commit()
    row = conn.execute(
        "SELECT description, terms, payment_info FROM service_info WHERE service_key=?",
        (service_key,)
    ).fetchone()
    conn.close()
    if row:
        return {"description": row[0] or "", "terms": row[1] or "", "payment_info": row[2] or ""}
    return {"description": "", "terms": "", "payment_info": ""}


def _service_info_widget(service_key, label):
    """Render HTML widget form info layanan untuk disematkan di halaman admin."""
    info = _get_service_info_admin(service_key)
    desc = info["description"].replace('"', '&quot;')
    terms = info["terms"].replace('"', '&quot;')
    pay = info["payment_info"].replace('"', '&quot;')
    return f"""
<div class="card" style="margin-bottom:24px;border-left:4px solid #7c5cbf">
  <div class="card-header" style="display:flex;align-items:center;gap:10px">
    <span style="font-size:18px">ℹ️</span>
    <span style="font-weight:600">Info Layanan — {label}</span>
    <span style="font-size:12px;color:var(--muted);margin-left:4px">Ditampilkan ke member sebelum buka tiket</span>
  </div>
  <div class="card-body">
    <form method="POST" action="/service-info/save">
      <input type="hidden" name="service_key" value="{service_key}">
      <div style="margin-bottom:14px">
        <label style="display:block;margin-bottom:6px;font-weight:500;color:var(--muted);font-size:13px">📋 DESKRIPSI PRODUK</label>
        <textarea name="description" rows="3" style="width:100%;background:var(--input-bg);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:10px;font-size:14px;resize:vertical" placeholder="Jelaskan layanan ini secara singkat...">{info['description']}</textarea>
      </div>
      <div style="margin-bottom:14px">
        <label style="display:block;margin-bottom:6px;font-weight:500;color:var(--muted);font-size:13px">📜 SYARAT & KETENTUAN</label>
        <textarea name="terms" rows="4" style="width:100%;background:var(--input-bg);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:10px;font-size:14px;resize:vertical" placeholder="Tuliskan syarat & ketentuan layanan...">{info['terms']}</textarea>
      </div>
      <div style="margin-bottom:14px">
        <label style="display:block;margin-bottom:6px;font-weight:500;color:var(--muted);font-size:13px">💳 CARA PEMBAYARAN</label>
        <textarea name="payment_info" rows="3" style="width:100%;background:var(--input-bg);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:10px;font-size:14px;resize:vertical" placeholder="Jelaskan cara pembayaran yang tersedia...">{info['payment_info']}</textarea>
      </div>
      <div style="display:flex;gap:10px;align-items:center">
        <button type="submit" class="btn btn-primary" style="min-width:120px">💾 Simpan</button>
        <span style="font-size:12px;color:var(--muted)">Kosongkan semua field untuk menonaktifkan info embed.</span>
      </div>
    </form>
  </div>
</div>"""


@app.route("/service-info/save", methods=["POST"])
@login_required
def service_info_save():
    service_key = request.form.get("service_key", "").strip()
    description = request.form.get("description", "").strip()
    terms = request.form.get("terms", "").strip()
    payment_info = request.form.get("payment_info", "").strip()

    try:
        from utils.service_info import SERVICE_KEYS
        valid_keys = list(SERVICE_KEYS.keys())
    except Exception:
        valid_keys = ["midman_trade", "midman_jb", "robux", "ml", "lainnya", "scaset", "gp"]
    if service_key not in valid_keys:
        flash("Service key tidak valid.", "error")
        return redirect(url_for("index"))

    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS service_info (
        service_key TEXT PRIMARY KEY,
        description TEXT DEFAULT '',
        terms TEXT DEFAULT '',
        payment_info TEXT DEFAULT ''
    )""")
    conn.execute(
        "INSERT OR REPLACE INTO service_info (service_key, description, terms, payment_info) VALUES (?,?,?,?)",
        (service_key, description, terms, payment_info)
    )
    conn.commit()
    conn.close()

    # Redirect ke halaman asal berdasarkan service_key
    redirect_map = {
        "midman_trade": "page_service_info",
        "midman_jb": "page_service_info",
        "robux": "page_robux",
        "ml": "page_ml",
        "lainnya": "page_lainnya",
        "scaset": "page_service_info",
        "gp": "page_service_info",
        "vilog": "page_service_info",
    }
    flash(f"Info layanan berhasil disimpan.", "success")
    target = redirect_map.get(service_key, "page_service_info")
    return redirect(url_for(target))


@app.route("/service-info")
@login_required
def page_service_info():
    """Halaman khusus untuk kelola info layanan yang tidak punya halaman admin tersendiri."""
    try:
        from utils.service_info import SERVICE_KEYS
        widgets = "\n".join(
            _service_info_widget(k, v) for k, v in SERVICE_KEYS.items()
        )
    except Exception:
        widgets = (
            _service_info_widget("midman_trade", "Midman Trade")
            + _service_info_widget("midman_jb", "Midman Jual Beli")
            + _service_info_widget("scaset", "SC TB / Aset Game")
        )
    content = f"""
<div class="page-header"><h2>ℹ️ Info Layanan</h2><p class="text-muted">Kelola informasi yang ditampilkan ke member sebelum membuka tiket.</p></div>
{widgets}
"""
    return render_page(content)


@app.route("/autopost")
@login_required
def page_autopost():
    from utils.autoposter_settings import get_autopost_tasks, get_autopost_history
    tasks = get_autopost_tasks()
    history = get_autopost_history(limit=30)
    
    tasks_html = ""
    for t in tasks:
        status_color = "#4dbb8a" if t["is_active"] else "#e05555"
        status_text = "Aktif" if t["is_active"] else "Mati"
        tasks_html += f"""
        <tr>
            <td><strong>#{t['id']}</strong></td>
            <td><code>{t['channel_id']}</code></td>
            <td>{t['interval_minutes']}m</td>
            <td>{t['message'][:60]}...</td>
            <td><span style="color:{status_color};font-weight:600;">{status_text}</span></td>
            <td>
                <a href="/autopost/edit/{t['id']}" class="btn btn-sm">Edit</a>
                <form method="POST" action="/autopost/toggle/{t['id']}" style="display:inline;">
                    <button type="submit" class="btn btn-sm">Toggle</button>
                </form>
                <form method="POST" action="/autopost/delete/{t['id']}" style="display:inline;">
                    <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('Hapus?')">Hapus</button>
                </form>
            </td>
        </tr>"""
    
    if not tasks_html:
        tasks_html = "<tr><td colspan=6 class='empty'>Belum ada autopost task.</td></tr>"
    
    history_html = ""
    for h in history:
        status_icon = "✅" if h["status"] == "success" else "❌"
        history_html += f"""
        <tr>
            <td>{h['id']}</td>
            <td>#{h['task_id']}</td>
            <td>{h['message'][:50]}...</td>
            <td>{status_icon}</td>
            <td>{h['created_at']}</td>
        </tr>"""
    
    if not history_html:
        history_html = "<tr><td colspan=5 class='empty'>Belum ada history.</td></tr>"
    
    content = f"""
    <div class="page-header">
        <h2>📡 AutoPost</h2>
        <p class="text-muted">Kelola auto-post pesan ke channel Discord.</p>
    </div>
    
    <div class="card">
        <div class="card-header">Tambah AutoPost</div>
        <div class="card-body">
            <form method="POST" action="/autopost/add">
                <div class="form-grid-2">
                    <div>
                        <label>Channel ID (pisahkan dengan koma untuk multiple)</label>
                        <input type="text" name="channel_id" placeholder="123456,789012,345678" required>
                    </div>
                    <div>
                        <label>Interval (menit)</label>
                        <input type="number" name="interval_minutes" value="60" min="1" required>
                    </div>
                </div>
                <div>
                    <label>Pesan</label>
                    <textarea name="message" rows="3" placeholder="Pesan yang akan di-post..." required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Tambah</button>
            </form>
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">Daftar AutoPost</div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr><th>ID</th><th>Channel ID</th><th>Interval</th><th>Pesan</th><th>Status</th><th>Aksi</th></tr>
                </thead>
                <tbody>{tasks_html}</tbody>
            </table>
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">History (30 terakhir)</div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr><th>ID</th><th>Task</th><th>Pesan</th><th>Status</th><th>Waktu</th></tr>
                </thead>
                <tbody>{history_html}</tbody>
            </table>
        </div>
    </div>
    """
    return render_page(content)


@app.route("/autopost/add", methods=["POST"])
@login_required
def autopost_add():
    from utils.autoposter_settings import add_autopost_task
    channel_id = request.form.get("channel_id", "").strip()
    interval_minutes = int(request.form.get("interval_minutes", 60))
    message = request.form.get("message", "").strip()
    token = os.environ.get("AUTOPOSTER_TOKEN", "")
    add_autopost_task(channel_id, message, interval_minutes, token)
    flash("AutoPost berhasil ditambahkan.", "success")
    return redirect(url_for("page_autopost"))


@app.route("/autopost/toggle/<int:tid>", methods=["POST"])
@login_required
def autopost_toggle(tid):
    from utils.autoposter_settings import toggle_autopost_task
    toggle_autopost_task(tid)
    return redirect(url_for("page_autopost"))


@app.route("/autopost/delete/<int:tid>", methods=["POST"])
@login_required
def autopost_delete(tid):
    from utils.autoposter_settings import delete_autopost_task
    delete_autopost_task(tid)
    flash("AutoPost dihapus.", "success")
    return redirect(url_for("page_autopost"))


@app.route("/autopost/edit/<int:tid>", methods=["GET"])
@login_required
def autopost_edit(tid):
    from utils.autoposter_settings import get_autopost_task
    task = get_autopost_task(tid)
    if not task:
        flash("Task tidak ditemukan.", "error")
        return redirect(url_for("page_autopost"))
    
    content = f"""
    <div class="page-header">
        <h2>✏️ Edit AutoPost #{tid}</h2>
    </div>
    
    <div class="card">
        <div class="card-body">
            <form method="POST" action="/autopost/edit/{tid}">
                <div class="form-grid-2">
                    <div>
                        <label>Channel ID (pisahkan dengan koma untuk multiple)</label>
                        <input type="text" name="channel_id" value="{task['channel_id']}" required>
                    </div>
                    <div>
                        <label>Interval (menit)</label>
                        <input type="number" name="interval_minutes" value="{task['interval_minutes']}" min="1" required>
                    </div>
                </div>
                <div>
                    <label>Pesan</label>
                    <textarea name="message" rows="5" required>{task['message']}</textarea>
                </div>
                <div style="margin-top:1rem;display:flex;gap:0.5rem;">
                    <button type="submit" class="btn btn-primary">Simpan</button>
                    <a href="/autopost" class="btn">Batal</a>
                </div>
            </form>
        </div>
    </div>
    """
    return render_page(content)


@app.route("/autopost/edit/<int:tid>", methods=["POST"])
@login_required
def autopost_edit_save(tid):
    from utils.autoposter_settings import update_autopost_task
    channel_id = request.form.get("channel_id", "").strip()
    interval_minutes = int(request.form.get("interval_minutes", 60))
    message = request.form.get("message", "").strip()
    update_autopost_task(tid, message=message, interval_minutes=interval_minutes)
    flash("AutoPost berhasil diupdate.", "success")
    return redirect(url_for("page_autopost"))


if __name__ == "__main__":
    port = int(os.environ.get("ADMIN_PORT", 5000))
    print(f"[ADMIN] Cellyn Store Admin Panel berjalan di http://localhost:{port}")
    print(f"[ADMIN] Password: {ADMIN_PASSWORD}")
    app.run(host="0.0.0.0", port=port, debug=False)
