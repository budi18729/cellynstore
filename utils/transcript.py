import discord
import io
import datetime


def avatar_url(user):
    if user.avatar:
        return str(user.avatar.url)
    return f"https://cdn.discordapp.com/embed/avatars/{int(user.discriminator) % 5}.png"


def render_message(msg):
    ts = msg.created_at.strftime("%d %b %Y, %H:%M:%S")
    av = avatar_url(msg.author)
    name = msg.author.display_name
    color = "#00b4d8" if msg.author.bot else "#e2e8f0"

    content_html = ""

    if msg.content:
        text = msg.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        content_html += f'<div class="msg-content">{text}</div>'

    for embed in msg.embeds:
        title = (embed.title or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        fields_html = ""
        for field in embed.fields:
            val = field.value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            fields_html += f'<div class="embed-field"><span class="field-val">{val}</span></div>'
        footer = f'<div class="embed-footer">{embed.footer.text}</div>' if embed.footer and embed.footer.text else ""
        color_bar = f"#{embed.color.value:06x}" if embed.color else "#5865f2"
        content_html += f'''
        <div class="embed" style="border-left: 4px solid {color_bar}">
            {f'<div class="embed-title">{title}</div>' if title else ""}
            {fields_html}
            {footer}
        </div>'''

    return f'''
    <div class="message">
        <img class="avatar" src="{av}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
        <div class="msg-body">
            <div class="msg-header">
                <span class="username" style="color:{color}">{name}</span>
                <span class="timestamp">{ts}</span>
            </div>
            {content_html}
        </div>
    </div>'''


async def generate(channel, store_name="Cellyn Store"):
    messages = []
    async for msg in channel.history(limit=500, oldest_first=True):
        messages.append(msg)

    msgs_html = "\n".join(render_message(m) for m in messages)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    count = len(messages)

    html = f'''<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transcript — {channel.name}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    min-height: 100vh;
  }}

  .header {{
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
    border-bottom: 1px solid #21262d;
    padding: 28px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }}

  .header-left {{ display: flex; flex-direction: column; gap: 4px; }}

  .store-name {{
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #00b4d8;
  }}

  .channel-name {{
    font-family: 'Syne', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: #f0f6fc;
  }}

  .header-right {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }}

  .meta-label {{
    font-size: 10px;
    color: #484f58;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}

  .meta-value {{
    font-size: 12px;
    color: #8b949e;
  }}

  .badge {{
    display: inline-block;
    background: #00b4d8;
    color: #0d1117;
    font-family: 'Syne', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 3px 10px;
    border-radius: 20px;
    margin-top: 4px;
  }}

  .divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, #21262d 20%, #21262d 80%, transparent);
    margin: 0 40px;
  }}

  .messages {{
    padding: 24px 40px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .message {{
    display: flex;
    gap: 14px;
    padding: 8px 12px;
    border-radius: 6px;
    transition: background 0.1s;
  }}

  .message:hover {{ background: #161b22; }}

  .avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 2px;
    border: 2px solid #21262d;
  }}

  .msg-body {{ display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }}

  .msg-header {{ display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }}

  .username {{
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    font-weight: 700;
  }}

  .timestamp {{
    font-size: 10px;
    color: #484f58;
    letter-spacing: 0.5px;
  }}

  .msg-content {{
    color: #c9d1d9;
    line-height: 1.6;
    word-break: break-word;
  }}

  .embed {{
    background: #161b22;
    border-radius: 4px;
    padding: 12px 16px;
    margin-top: 4px;
    max-width: 520px;
  }}

  .embed-title {{
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: #f0f6fc;
    margin-bottom: 8px;
  }}

  .embed-field {{ margin: 2px 0; }}

  .field-val {{
    color: #8b949e;
    line-height: 1.7;
  }}

  .embed-footer {{
    font-size: 10px;
    color: #484f58;
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid #21262d;
  }}

  .footer {{
    text-align: center;
    padding: 32px 40px;
    color: #484f58;
    font-size: 11px;
    border-top: 1px solid #21262d;
    letter-spacing: 1px;
  }}
</style>
</head>
<body>
<div class="wrapper">
<div class="header">
  <div class="header-left">
    <span class="store-name">{store_name}</span>
    <span class="channel-name"># {channel.name}</span>
  </div>
  <div class="header-right">
    <span class="meta-label">Digenerate</span>
    <span class="meta-value">{now}</span>
    <span class="badge">{count} pesan</span>
  </div>
</div>

<div class="divider"></div>

<div class="messages">
{msgs_html}
</div>

<div class="footer">
  {store_name} &nbsp;·&nbsp; Midman System &nbsp;·&nbsp; {now}
</div>

</div><!-- end wrapper -->
</body>
</html>'''

    return discord.File(
        fp=io.StringIO(html),
        filename=f"transcript-{channel.name}.html"
    )
