"""
admin_embed.py — Embed Builder Blueprint untuk Cellyn Admin Panel
Menggunakan Discord REST API langsung (tidak butuh bot instance).
Daftarkan otomatis via admin.py:
    from admin_embed import embed_bp
    app.register_blueprint(embed_bp)
"""
import os, json, sqlite3
import requests
from functools import wraps
from flask import Blueprint, request as req, jsonify, session, redirect

DB_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")
API      = "https://discord.com/api/v10"

embed_bp = Blueprint("embed_bp", __name__)

def _ensure_tables():
    conn = sqlite3.connect(DB_FILE)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS embed_templates (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL UNIQUE,
        embed_json TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS embed_messages (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        label            TEXT NOT NULL,
        channel_id       TEXT NOT NULL,
        message_id       TEXT NOT NULL UNIQUE,
        embed_json       TEXT NOT NULL,
        content          TEXT DEFAULT NULL,
        auto_send        INTEGER DEFAULT 0,
        interval_minutes INTEGER DEFAULT 60,
        scheduled_time   TEXT DEFAULT NULL,
        next_send        TEXT DEFAULT NULL,
        active           INTEGER DEFAULT 1,
        sent_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

_ensure_tables()

def _migrate_embed_messages():
    conn = sqlite3.connect(DB_FILE)
    for col, defval in [
        ("content",          "TEXT DEFAULT NULL"),
        ("auto_send",        "INTEGER DEFAULT 0"),
        ("interval_minutes", "INTEGER DEFAULT 60"),
        ("scheduled_time",   "TEXT DEFAULT NULL"),
        ("next_send",        "TEXT DEFAULT NULL"),
        ("active",           "INTEGER DEFAULT 1"),
    ]:
        try:
            conn.execute(f"ALTER TABLE embed_messages ADD COLUMN {col} {defval}")
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                print(f"[EMBED] Migration {col}: {e}")
    conn.commit()
    conn.close()

_migrate_embed_messages()


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

def discord_headers():
    token = os.environ.get("TOKEN", "")
    return {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

def get_guild_channels():
    try:
        guild_id = os.environ.get("GUILD_ID", "")
        r = requests.get(f"{API}/guilds/{guild_id}/channels",
                         headers=discord_headers(), timeout=5)
        if r.status_code == 200:
            return [{"id": c["id"], "name": c["name"]}
                    for c in sorted(r.json(), key=lambda x: x.get("position", 0))
                    if c.get("type") == 0]
    except Exception:
        pass
    return []

def build_embed_payload(data: dict) -> dict:
    embed = {}
    if data.get("title"):       embed["title"] = data["title"]
    if data.get("url"):         embed["url"]   = data["url"]
    if data.get("description"): embed["description"] = data["description"]
    if data.get("color"):
        try: embed["color"] = int(str(data["color"]).lstrip("#"), 16)
        except: pass
    if data.get("timestamp"):
        ts = data["timestamp"]
        embed["timestamp"] = ts + ":00" if len(ts) == 16 else ts

    author = data.get("author", {})
    if author.get("name"):
        a = {"name": author["name"]}
        if author.get("url"):      a["url"]      = author["url"]
        if author.get("icon_url"): a["icon_url"]  = author["icon_url"]
        embed["author"] = a

    if data.get("thumbnail"): embed["thumbnail"] = {"url": data["thumbnail"]}
    if data.get("image"):     embed["image"]     = {"url": data["image"]}

    footer = data.get("footer", {})
    if footer.get("text"):
        f = {"text": footer["text"]}
        if footer.get("icon_url"): f["icon_url"] = footer["icon_url"]
        embed["footer"] = f

    fields = []
    for field in data.get("fields", []):
        if field.get("name") and field.get("value"):
            fields.append({"name": field["name"], "value": field["value"],
                           "inline": bool(field.get("inline", False))})
    if fields:
        embed["fields"] = fields
    return embed


# ═══════════════════════════════════════════════════════════════
#  HALAMAN UTAMA
# ═══════════════════════════════════════════════════════════════
@embed_bp.route("/embeds")
@login_required
def page_embeds():
    conn = get_db()
    templates = conn.execute("SELECT id, name FROM embed_templates ORDER BY name").fetchall()
    sent      = conn.execute(
        "SELECT id, label, channel_id, message_id, sent_at, auto_send, interval_minutes, scheduled_time, next_send, active FROM embed_messages ORDER BY sent_at DESC"
    ).fetchall()
    conn.close()
    channels = get_guild_channels()

    tpl_opts  = "".join(f'<option value="{t["id"]}">{t["name"]}</option>' for t in templates)
    ch_opts   = "".join(f'<option value="{c["id"]}">#{c["name"]}</option>' for c in channels)
    sent_rows = ""
    for s in sent:
        s_dict = dict(s)
        auto_info = "-"
        next_info = "-"
        if s_dict.get("auto_send"):
            sched = s_dict.get("scheduled_time")
            interval = s_dict.get("interval_minutes", 60)
            status_str = "✅" if s_dict.get("active") else "⏸"
            mode_str = f"Jam {sched}" if sched else f"{interval} mnt"
            auto_info = f"{status_str} {mode_str}"
            next_send = s_dict.get("next_send")
            next_info = str(next_send)[:16] if next_send else "-"
        sent_rows += f"""<tr>
          <td>{s['id']}</td><td>{s['label']}</td>
          <td>#{s['channel_id']}</td>
          <td><code style="font-size:.72rem">{s['message_id']}</code></td>
          <td>{str(s['sent_at'])[:16]}</td>
          <td style="font-size:.78rem">{auto_info}</td>
          <td style="font-size:.78rem">{next_info}</td>
          <td style="white-space:nowrap">
            <button class="btn btn-ghost btn-sm" onclick="loadSent('{s['message_id']}')">✏️ Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteSent('{s['message_id']}',this)">🗑</button>
          </td></tr>"""

    content = f"""
<div class="page-header">
  <h2 class="page-title">✉️ Embed Builder<small>Buat, kirim, dan kelola embed Discord</small></h2>
</div>
<div style="display:grid;grid-template-columns:1fr 360px;gap:1.25rem;align-items:start">

<!-- FORM -->
<div>
  <div class="card" style="margin-bottom:1rem">
    <div class="card-header"><span class="card-title">📁 Template</span></div>
    <div class="card-body">
      <div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center">
        <select id="tpl-select" style="flex:1;min-width:140px"><option value="">— Pilih template —</option>{tpl_opts}</select>
        <button class="btn btn-ghost btn-sm" onclick="loadTemplate()">Load</button>
        <button class="btn btn-warning btn-sm" onclick="saveTemplate()">Simpan</button>
        <button class="btn btn-danger btn-sm" onclick="deleteTemplate()">Hapus</button>
      </div>
      <input id="tpl-name" placeholder="Nama template baru..." style="margin-top:.6rem">
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-title">🛠 Konten Embed</span></div>
    <div class="card-body">
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Title</label><input id="f-title" placeholder="Judul embed"></div>
        <div class="form-group"><label>Title URL</label><input id="f-url" placeholder="https://..."></div>
      </div>
      <div class="form-group" style="margin-top:.75rem">
        <label>Description</label><textarea id="f-desc" rows="4" placeholder="Deskripsi (markdown didukung)..."></textarea>
      </div>
      <div class="form-grid form-grid-2" style="margin-top:.75rem">
        <div class="form-group"><label>Color</label><input id="f-color" type="color" value="#5865f2" style="height:38px;padding:3px 5px;cursor:pointer"></div>
        <div class="form-group"><label>Timestamp (opsional)</label><input id="f-timestamp" type="datetime-local"></div>
      </div>
      <div class="divider"></div>
      <label>Author</label>
      <div class="form-grid" style="grid-template-columns:1fr 1fr 1fr;gap:.75rem;margin-top:.4rem">
        <div class="form-group"><label>Nama</label><input id="f-author-name" placeholder="Nama"></div>
        <div class="form-group"><label>URL</label><input id="f-author-url" placeholder="https://..."></div>
        <div class="form-group"><label>Icon URL</label><input id="f-author-icon" placeholder="https://..."></div>
      </div>
      <div class="divider"></div>
      <label>Gambar</label>
      <div class="form-grid form-grid-2" style="margin-top:.4rem">
        <div class="form-group"><label>Thumbnail URL</label><input id="f-thumbnail" placeholder="https://..."></div>
        <div class="form-group"><label>Image URL</label><input id="f-image" placeholder="https://..."></div>
      </div>
      <div class="divider"></div>
      <label>Footer</label>
      <div class="form-grid form-grid-2" style="margin-top:.4rem">
        <div class="form-group"><label>Teks Footer</label><input id="f-footer-text" placeholder="Footer text"></div>
        <div class="form-group"><label>Footer Icon URL</label><input id="f-footer-icon" placeholder="https://..."></div>
      </div>
      <div class="divider"></div>
      <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem">
        <label style="margin:0">Fields</label>
        <button class="btn btn-ghost btn-sm" onclick="addField()">+ Tambah Field</button>
      </div>
      <div id="fields-container"></div>
      <div class="divider"></div>
      <label>Kirim ke Discord</label>
      <div class="form-grid form-grid-2" style="margin-top:.4rem">
        <div class="form-group"><label>Channel</label>
          <select id="f-channel"><option value="">— Pilih channel —</option>{ch_opts}</select>
        </div>
        <div class="form-group"><label>Label Internal</label><input id="f-label" placeholder="Catatan untuk embed ini..."></div>
      </div>
      <div class="form-group" style="margin-top:.75rem">
        <label>Message Content (opsional — untuk mention role/everyone)</label>
        <input id="f-content" placeholder="Contoh: &lt;@&amp;ROLE_ID&gt; atau @everyone">
        <span style="font-size:.72rem;color:var(--muted);margin-top:3px;display:block">Teks dikirim bareng embed, gunakan untuk tag role.</span>
      </div>
      <div class="divider"></div>
      <label>Auto Send (opsional)</label>
      <div style="display:flex;align-items:center;gap:8px;margin-top:.4rem;margin-bottom:.6rem">
        <input type="checkbox" id="f-autosend" onchange="toggleAutoSend(this)" style="width:auto">
        <span style="font-size:.82rem;color:var(--muted2)">Aktifkan auto send terjadwal</span>
      </div>
      <div id="autosend-opts" style="display:none">
        <div class="form-grid form-grid-2">
          <div class="form-group">
            <label>Mode</label>
            <select id="f-mode" onchange="toggleAutoSendMode(this.value)">
              <option value="interval">Interval (setiap N menit)</option>
              <option value="schedule">Jadwal jam tertentu (setiap hari)</option>
            </select>
          </div>
          <div class="form-group" id="f-interval-wrap">
            <label>Interval (menit)</label>
            <input id="f-interval" type="number" value="60" min="1" placeholder="60">
          </div>
          <div class="form-group" id="f-schedule-wrap" style="display:none">
            <label>Jam kirim WIB (HH:MM)</label>
            <input id="f-schedule" type="text" placeholder="09:00">
            <span style="font-size:.72rem;color:var(--muted);margin-top:3px;display:block">Input jam WIB, otomatis dikonversi ke UTC.</span>
          </div>
        </div>
      </div>
      <div class="form-actions" style="margin-top:1rem">
        <button class="btn btn-ghost" onclick="updatePreview()">🔄 Preview</button>
        <button class="btn btn-primary" onclick="sendEmbed()">📨 Kirim</button>
        <button class="btn btn-ghost" onclick="clearForm()">🗑 Reset</button>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:1rem">
    <div class="card-header"><span class="card-title">📋 Embed Terkirim</span></div>
    <div class="card-body" style="padding:0">
      <table><thead><tr><th>#</th><th>Label</th><th>Channel</th><th>Message ID</th><th>Waktu</th><th>Auto Send</th><th>Next Send</th><th>Aksi</th></tr></thead>
      <tbody>{sent_rows or '<tr><td colspan="6" class="empty">Belum ada embed terkirim</td></tr>'}</tbody></table>
    </div>
  </div>
</div>

<!-- PREVIEW -->
<div style="position:sticky;top:1.5rem">
  <div class="card">
    <div class="card-header"><span class="card-title">👁 Preview</span></div>
    <div class="card-body" style="background:#313338;border-radius:0 0 12px 12px;min-height:120px">
      <div id="preview-area"><div style="color:#72767d;font-size:.82rem;text-align:center;padding:2rem 0">Isi form lalu klik Preview...</div></div>
    </div>
  </div>
</div>
</div>

<div id="toast-box" style="position:fixed;bottom:20px;right:20px;z-index:999"></div>

<style>
.discord-embed{{border-left:4px solid #5865f2;background:#2b2d31;border-radius:0 4px 4px 0;padding:12px 16px;overflow:hidden}}
.de-author{{display:flex;align-items:center;gap:7px;margin-bottom:6px}}
.de-author img,.de-footer img{{width:20px;height:20px;border-radius:50%;object-fit:cover}}
.de-author-name{{font-size:.82rem;font-weight:600;color:#fff}}
.de-title{{font-size:.95rem;font-weight:700;color:#00b0f4;margin-bottom:5px;word-break:break-word}}
.de-title a{{color:#00b0f4;text-decoration:none}}
.de-desc{{font-size:.84rem;color:#dcddde;white-space:pre-wrap;word-break:break-word;margin-bottom:8px}}
.de-fields{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}}
.de-field{{min-width:100px}}.de-field.inline{{flex:1}}
.de-fname{{font-size:.78rem;font-weight:700;color:#fff;margin-bottom:2px}}
.de-fval{{font-size:.8rem;color:#dcddde;white-space:pre-wrap;word-break:break-word}}
.de-image img{{max-width:100%;border-radius:4px;margin-top:8px}}
.de-thumb{{float:right;margin-left:10px}}.de-thumb img{{width:72px;height:72px;object-fit:cover;border-radius:4px}}
.de-footer{{display:flex;align-items:center;gap:6px;margin-top:8px;font-size:.72rem;color:#a3a6aa;clear:both}}
.field-block{{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:8px;position:relative}}
.rm-field{{position:absolute;top:8px;right:8px;background:rgba(224,85,85,.15);color:var(--danger);border:1px solid rgba(224,85,85,.25);border-radius:4px;padding:2px 8px;cursor:pointer;font-size:.72rem}}
.toast-item{{background:#3ba55d;color:#fff;padding:10px 16px;border-radius:8px;margin-top:8px;font-size:.84rem;box-shadow:0 2px 8px rgba(0,0,0,.3)}}
.toast-item.err{{background:#ed4245}}
</style>

<script>
let fieldCount=0,editingMessageId=null;
function toast(msg,err=false){{const b=document.getElementById('toast-box');const e=document.createElement('div');e.className='toast-item'+(err?' err':'');e.textContent=msg;b.appendChild(e);setTimeout(()=>e.remove(),3000);}}
function addField(n='',v='',inline=false){{
  const i=fieldCount++;const d=document.createElement('div');d.className='field-block';d.id='f'+i;
  d.innerHTML=`<button class="rm-field" onclick="document.getElementById('f${{i}}').remove()">✕</button>
    <div class="form-grid form-grid-2" style="gap:.5rem">
      <div class="form-group"><label>Nama</label><input class="fn" value="${{n}}" placeholder="Nama field"></div>
      <div class="form-group"><label>Value</label><textarea class="fv" rows="2" placeholder="Value">${{v}}</textarea></div>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-top:6px"><input type="checkbox" class="fi" ${{inline?'checked':''}}><span style="font-size:.8rem;color:var(--muted2)">Inline</span></div>`;
  document.getElementById('fields-container').appendChild(d);
}}
function collectData(){{
  const fields=[];
  document.querySelectorAll('.field-block').forEach(b=>{{const n=b.querySelector('.fn')?.value.trim();const v=b.querySelector('.fv')?.value.trim();if(n&&v)fields.push({{name:n,value:v,inline:b.querySelector('.fi')?.checked||false}});}});
  return{{title:document.getElementById('f-title').value.trim(),url:document.getElementById('f-url').value.trim(),description:document.getElementById('f-desc').value.trim(),color:document.getElementById('f-color').value,timestamp:document.getElementById('f-timestamp').value||null,author:{{name:document.getElementById('f-author-name').value.trim(),url:document.getElementById('f-author-url').value.trim(),icon_url:document.getElementById('f-author-icon').value.trim()}},thumbnail:document.getElementById('f-thumbnail').value.trim(),image:document.getElementById('f-image').value.trim(),footer:{{text:document.getElementById('f-footer-text').value.trim(),icon_url:document.getElementById('f-footer-icon').value.trim()}},fields,content:document.getElementById('f-content')?.value.trim()||''}}; 
}}
function loadDataIntoForm(d){{
  if(!d)return;
  ['title','url'].forEach(k=>document.getElementById('f-'+k).value=d[k]||'');
  document.getElementById('f-desc').value=d.description||'';
  document.getElementById('f-color').value=d.color||'#5865f2';
  document.getElementById('f-timestamp').value=d.timestamp||'';
  document.getElementById('f-author-name').value=d.author?.name||'';
  document.getElementById('f-author-url').value=d.author?.url||'';
  document.getElementById('f-author-icon').value=d.author?.icon_url||'';
  document.getElementById('f-thumbnail').value=d.thumbnail||'';
  document.getElementById('f-image').value=d.image||'';
  document.getElementById('f-footer-text').value=d.footer?.text||'';
  document.getElementById('f-footer-icon').value=d.footer?.icon_url||'';
  document.getElementById('f-content').value=d.content||'';
  document.getElementById('fields-container').innerHTML='';fieldCount=0;
  (d.fields||[]).forEach(f=>addField(f.name,f.value,f.inline));
  updatePreview();
}}
function clearForm(){{loadDataIntoForm({{}});editingMessageId=null;document.getElementById('f-label').value='';document.getElementById('f-channel').value='';document.getElementById('f-content').value='';document.getElementById('f-autosend').checked=false;document.getElementById('autosend-opts').style.display='none';document.getElementById('f-interval').value='60';document.getElementById('f-schedule').value='';document.getElementById('preview-area').innerHTML='<div style="color:#72767d;font-size:.82rem;text-align:center;padding:2rem 0">Isi form lalu klik Preview...</div>';}}
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}}
function updatePreview(){{
  const d=collectData();const col=d.color||'#5865f2';
  let h=`<div class="discord-embed" style="border-left-color:${{col}}">`;
  if(d.thumbnail)h+=`<div class="de-thumb"><img src="${{d.thumbnail}}" onerror="this.style.display='none'"></div>`;
  if(d.author?.name){{h+=`<div class="de-author">`;if(d.author.icon_url)h+=`<img src="${{d.author.icon_url}}" onerror="this.style.display='none'">`;h+=`<span class="de-author-name">${{esc(d.author.name)}}</span></div>`;}}
  if(d.title)h+=d.url?`<div class="de-title"><a href="${{d.url}}" target="_blank">${{esc(d.title)}}</a></div>`:`<div class="de-title">${{esc(d.title)}}</div>`;
  if(d.description)h+=`<div class="de-desc">${{esc(d.description)}}</div>`;
  if(d.fields.length){{h+=`<div class="de-fields">`;d.fields.forEach(f=>{{h+=`<div class="de-field${{f.inline?' inline':''}}"><div class="de-fname">${{esc(f.name)}}</div><div class="de-fval">${{esc(f.value)}}</div></div>`;}});h+=`</div>`;}}
  if(d.image)h+=`<div class="de-image"><img src="${{d.image}}" onerror="this.style.display='none'"></div>`;
  if(d.footer?.text||d.timestamp){{h+=`<div class="de-footer">`;if(d.footer?.icon_url)h+=`<img src="${{d.footer.icon_url}}" onerror="this.style.display='none'">`;if(d.footer?.text)h+=`<span>${{esc(d.footer.text)}}</span>`;if(d.footer?.text&&d.timestamp)h+=`<span> • </span>`;if(d.timestamp)h+=`<span>${{new Date(d.timestamp).toLocaleString('id-ID')}}</span>`;h+=`</div>`;}}
  h+=`</div>`;document.getElementById('preview-area').innerHTML=h;
}}
async function sendEmbed(){{
  const ch=document.getElementById('f-channel').value;const lbl=document.getElementById('f-label').value.trim();
  if(!ch)return toast('Pilih channel dulu!',true);if(!lbl)return toast('Isi label dulu!',true);
  const d=collectData();const autoSend=document.getElementById('f-autosend')?.checked||false;
  const mode=document.getElementById('f-mode')?.value||'interval';
  const interval=parseInt(document.getElementById('f-interval')?.value||'60');
  const schedule=document.getElementById('f-schedule')?.value.trim()||'';
  const payload={{embed:d,channel_id:ch,label:lbl,content:d.content||'',
    auto_send:autoSend,interval_minutes:interval,
    scheduled_time:mode==='schedule'?schedule:'',}};
  if(editingMessageId)payload.message_id=editingMessageId;
  const url=editingMessageId?'/embeds/api/edit':'/embeds/api/send';
  const r=await fetch(url,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});
  const data=await r.json();
  if(data.ok){{toast(editingMessageId?'✅ Embed diupdate!':'✅ Embed terkirim!');editingMessageId=null;setTimeout(()=>location.reload(),1500);}}
  else toast('❌ '+(data.error||'Gagal'),true);
}}
async function loadTemplate(){{const id=document.getElementById('tpl-select').value;if(!id)return toast('Pilih template dulu!',true);const r=await fetch('/embeds/api/template/'+id);const d=await r.json();if(d.ok)loadDataIntoForm(JSON.parse(d.embed_json));else toast('❌ '+d.error,true);}}
async function saveTemplate(){{
  const sel=document.getElementById('tpl-select');const name=document.getElementById('tpl-name').value.trim()||(sel.options[sel.selectedIndex]?.text)||'';
  if(!name||name.startsWith('—'))return toast('Isi nama template dulu!',true);
  const r=await fetch('/embeds/api/template/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name,embed_json:JSON.stringify(collectData())}})}});
  const d=await r.json();if(d.ok){{toast('✅ Template tersimpan!');setTimeout(()=>location.reload(),1500);}}else toast('❌ '+d.error,true);
}}
async function deleteTemplate(){{const id=document.getElementById('tpl-select').value;if(!id)return toast('Pilih template dulu!',true);if(!confirm('Hapus template ini?'))return;const r=await fetch('/embeds/api/template/'+id,{{method:'DELETE'}});const d=await r.json();if(d.ok){{toast('✅ Dihapus!');setTimeout(()=>location.reload(),1500);}}else toast('❌ '+d.error,true);}}
async function loadSent(mid){{const r=await fetch('/embeds/api/sent/'+mid);const d=await r.json();if(d.ok){{editingMessageId=mid;loadDataIntoForm(JSON.parse(d.embed_json));document.getElementById('f-label').value=d.label||'';document.getElementById('f-channel').value=d.channel_id||'';toast('📝 Loaded untuk edit');window.scrollTo({{top:0,behavior:'smooth'}});
if(d.auto_send){{document.getElementById('f-autosend').checked=true;
document.getElementById('autosend-opts').style.display='';
if(d.scheduled_time){{document.getElementById('f-mode').value='schedule';
document.getElementById('f-interval-wrap').style.display='none';
document.getElementById('f-schedule-wrap').style.display='';
document.getElementById('f-schedule').value=d.scheduled_time||'';}}else{{
document.getElementById('f-interval').value=d.interval_minutes||60;}}}}}}else toast('❌ '+d.error,true);}}
async function deleteSent(mid,btn){{if(!confirm('Hapus embed dari Discord & DB?'))return;const r=await fetch('/embeds/api/sent/'+mid,{{method:'DELETE'}});const d=await r.json();if(d.ok){{toast('✅ Embed dihapus!');btn.closest('tr').remove();}}else toast('❌ '+d.error,true);}}
function toggleAutoSend(cb){{
  document.getElementById('autosend-opts').style.display=cb.checked?'':'none';
}}
function toggleAutoSendMode(val){{
  document.getElementById('f-interval-wrap').style.display=val==='interval'?'':'none';
  document.getElementById('f-schedule-wrap').style.display=val==='schedule'?'':'none';
}}
['f-title','f-url','f-desc','f-color','f-author-name','f-thumbnail','f-image','f-footer-text'].forEach(id=>document.getElementById(id)?.addEventListener('input',updatePreview));
</script>"""

    from admin import render_page
    return render_page(content)


# ═══════════════════════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════════════════════

@embed_bp.route("/embeds/api/send", methods=["POST"])
@login_required
def api_send():
    data = req.json
    channel_id = data.get("channel_id")
    label      = data.get("label", "untitled")
    embed_data = data.get("embed", {})
    if not channel_id:
        return jsonify(ok=False, error="Channel ID kosong")
    try:
        msg_content = data.get("content", "").strip()
        payload = {"embeds": [build_embed_payload(embed_data)]}
        if msg_content:
            payload["content"] = msg_content
        r = requests.post(
            f"{API}/channels/{channel_id}/messages",
            headers=discord_headers(),
            json=payload,
            timeout=10
        )
        if r.status_code not in (200, 201):
            return jsonify(ok=False, error=f"Discord error {r.status_code}: {r.text[:200]}")
        msg_id = r.json()["id"]
        conn = get_db()
        auto_send      = 1 if data.get("auto_send") else 0
        interval_mins  = int(data.get("interval_minutes", 60))
        scheduled_time = data.get("scheduled_time", "").strip() or None
        content_msg2   = data.get("content", "").strip() or None
        import datetime as _dt
        now_dt = _dt.datetime.now(_dt.timezone.utc)
        if scheduled_time and auto_send:
            try:
                h, m = map(int, scheduled_time.split(":"))
                # Konversi WIB (UTC+7) → UTC
                utc_h = (h - 7) % 24
                nxt = now_dt.replace(hour=utc_h, minute=m, second=0, microsecond=0)
                if nxt <= now_dt:
                    nxt += _dt.timedelta(days=1)
            except Exception:
                nxt = now_dt + _dt.timedelta(minutes=interval_mins)
        elif auto_send:
            nxt = now_dt + _dt.timedelta(minutes=interval_mins)
        else:
            nxt = None
        conn.execute(
            "INSERT INTO embed_messages (label,channel_id,message_id,embed_json,content,auto_send,interval_minutes,scheduled_time,next_send,active) VALUES (?,?,?,?,?,?,?,?,?,1)",
            (label, channel_id, msg_id, json.dumps(embed_data), content_msg2, auto_send, interval_mins, scheduled_time, nxt.isoformat() if nxt else None)
        )
        conn.commit(); conn.close()
        return jsonify(ok=True, message_id=msg_id)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@embed_bp.route("/embeds/api/edit", methods=["POST"])
@login_required
def api_edit():
    data = req.json
    message_id = data.get("message_id")
    channel_id = data.get("channel_id")
    embed_data = data.get("embed", {})
    label      = data.get("label", "untitled")
    try:
        msg_content = data.get("content", "").strip()
        payload = {"embeds": [build_embed_payload(embed_data)]}
        if msg_content:
            payload["content"] = msg_content
        r = requests.patch(
            f"{API}/channels/{channel_id}/messages/{message_id}",
            headers=discord_headers(),
            json=payload,
            timeout=10
        )
        if r.status_code not in (200, 201):
            return jsonify(ok=False, error=f"Discord error {r.status_code}: {r.text[:200]}")
        conn = get_db()
        auto_send      = 1 if data.get("auto_send") else 0
        interval_mins  = int(data.get("interval_minutes", 60))
        scheduled_time = data.get("scheduled_time", "").strip() or None
        content_msg2   = data.get("content", "").strip() or None
        import datetime as _dt
        now_dt = _dt.datetime.now(_dt.timezone.utc)
        if scheduled_time and auto_send:
            try:
                h, m = map(int, scheduled_time.split(":"))
                # Konversi WIB (UTC+7) → UTC
                utc_h = (h - 7) % 24
                nxt = now_dt.replace(hour=utc_h, minute=m, second=0, microsecond=0)
                if nxt <= now_dt:
                    nxt += _dt.timedelta(days=1)
            except Exception:
                nxt = now_dt + _dt.timedelta(minutes=interval_mins)
        elif auto_send:
            nxt = now_dt + _dt.timedelta(minutes=interval_mins)
        else:
            nxt = None
        conn.execute(
            "UPDATE embed_messages SET embed_json=?,label=?,content=?,auto_send=?,interval_minutes=?,scheduled_time=?,next_send=?,updated_at=CURRENT_TIMESTAMP WHERE message_id=?",
            (json.dumps(embed_data), label, content_msg2, auto_send, interval_mins, scheduled_time, nxt.isoformat() if nxt else None, message_id)
        )
        conn.commit(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@embed_bp.route("/embeds/api/sent/<message_id>", methods=["GET"])
@login_required
def api_get_sent(message_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM embed_messages WHERE message_id=?", (message_id,)).fetchone()
    conn.close()
    if not row: return jsonify(ok=False, error="Tidak ditemukan")
    return jsonify(ok=True, **dict(row))


@embed_bp.route("/embeds/api/sent/<message_id>", methods=["DELETE"])
@login_required
def api_delete_sent(message_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM embed_messages WHERE message_id=?", (message_id,)).fetchone()
    if not row: conn.close(); return jsonify(ok=False, error="Tidak ditemukan")
    try:
        requests.delete(f"{API}/channels/{row['channel_id']}/messages/{message_id}",
                        headers=discord_headers(), timeout=10)
    except Exception:
        pass
    conn.execute("DELETE FROM embed_messages WHERE message_id=?", (message_id,))
    conn.commit(); conn.close()
    return jsonify(ok=True)


@embed_bp.route("/embeds/api/template/<int:tpl_id>", methods=["GET"])
@login_required
def api_get_template(tpl_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM embed_templates WHERE id=?", (tpl_id,)).fetchone()
    conn.close()
    if not row: return jsonify(ok=False, error="Tidak ditemukan")
    return jsonify(ok=True, **dict(row))


@embed_bp.route("/embeds/api/template/save", methods=["POST"])
@login_required
def api_save_template():
    data = req.json
    name = data.get("name", "").strip()
    embed_json = data.get("embed_json", "{}")
    if not name: return jsonify(ok=False, error="Nama kosong")
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO embed_templates (name,embed_json) VALUES (?,?) "
            "ON CONFLICT(name) DO UPDATE SET embed_json=excluded.embed_json,updated_at=CURRENT_TIMESTAMP",
            (name, embed_json)
        )
        conn.commit(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@embed_bp.route("/embeds/api/template/<int:tpl_id>", methods=["DELETE"])
@login_required
def api_delete_template(tpl_id):
    conn = get_db()
    conn.execute("DELETE FROM embed_templates WHERE id=?", (tpl_id,))
    conn.commit(); conn.close()
    return jsonify(ok=True)
