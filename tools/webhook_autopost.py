import json
import os
import time
import random
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "webhook_config.json")
STATE_PATH = os.path.join(os.path.dirname(__file__), "webhook_state.json")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit(f"Config not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {"index": 0}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def post_webhook(url, content=None, embeds=None, username=None, avatar_url=None):
    payload = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def pick_message(messages, mode, state):
    if not messages:
        raise SystemExit("Messages list is empty")
    if mode == "random":
        return random.choice(messages)
    # default: rotate
    idx = state.get("index", 0) % len(messages)
    msg = messages[idx]
    state["index"] = idx + 1
    return msg


def main():
    cfg = load_config()
    url = cfg.get("webhook_url")
    if not url:
        raise SystemExit("webhook_url is required in config")

    messages = cfg.get("messages", [])
    mode = cfg.get("mode", "rotate")
    interval = int(cfg.get("interval_seconds", 0))
    username = cfg.get("username")
    avatar_url = cfg.get("avatar_url")

    state = load_state()

    def send_once():
        msg = pick_message(messages, mode, state)
        content = msg.get("content") if isinstance(msg, dict) else str(msg)
        embeds = msg.get("embeds") if isinstance(msg, dict) else None
        post_webhook(url, content=content, embeds=embeds, username=username, avatar_url=avatar_url)
        save_state(state)
        print("[OK] Sent")

    if interval > 0:
        while True:
            send_once()
            time.sleep(interval)
    else:
        send_once()


if __name__ == "__main__":
    main()
