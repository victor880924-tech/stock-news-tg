"""
發送文字訊息到 Telegram
用法：python send_tg.py "訊息內容"
      或從 stdin 讀取：echo "訊息" | python send_tg.py
"""

import json
import os
import sys
import urllib.request
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))

def load_config():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)

def send_tg(text, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    MAX = 4000
    for i in range(0, len(text), MAX):
        chunk = text[i:i + MAX]
        data  = urllib.parse.urlencode({
            "chat_id":                  chat_id,
            "text":                     chunk,
            "parse_mode":               "Markdown",
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if not result.get("ok"):
            print(f"[tg] 失敗: {result}")
            return False
    return True

def main():
    cfg     = load_config()
    token   = cfg["telegram"]["bot_token"]
    chat_id = cfg["telegram"]["chat_id"]

    if len(sys.argv) >= 2:
        text = sys.argv[1]
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("[tg] 無訊息內容")
        sys.exit(1)

    ok = send_tg(text, token, chat_id)
    print("[tg] 發送成功！" if ok else "[tg] 發送失敗")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
