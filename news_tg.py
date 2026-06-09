"""
盤前新聞整理 → Telegram
爬取「昨收盤 13:30 → 今開盤前 09:00」的財經新聞，
Gemini API 分析後推送到 TG。
週末自動回溯至上週五收盤。
"""

import json
import os
import re
import ssl
import sys
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

BASE = os.path.dirname(os.path.abspath(__file__))
TZ_TAIPEI = timezone(timedelta(hours=8))

# ── 設定 ─────────────────────────────────────────────────

def load_config():
    import os as _os
    if _os.environ.get("GEMINI_API_KEY"):
        return {
            "telegram": {
                "bot_token": _os.environ["TG_BOT_TOKEN"],
                "chat_id":   _os.environ["TG_CHAT_ID"],
            },
            "gemini":   {"api_key": _os.environ["GEMINI_API_KEY"]},
            "news":     {"max_per_source": 30},
        }
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)

# ── 時間窗口 ──────────────────────────────────────────────

def get_window():
    now     = datetime.now(TZ_TAIPEI)
    today   = now.date()
    weekday = today.weekday()

    if weekday == 0:    prev = today - timedelta(days=3)
    elif weekday >= 5:  prev = today - timedelta(days=weekday - 4)
    else:               prev = today - timedelta(days=1)

    w_start = datetime(prev.year,  prev.month,  prev.day,  13, 30, tzinfo=TZ_TAIPEI)
    w_end   = datetime(today.year, today.month, today.day,  9,  0, tzinfo=TZ_TAIPEI)
    return w_start, w_end

def in_window(pub_date_str, w_start, w_end):
    if not pub_date_str:
        return True
    try:
        dt = parsedate_to_datetime(pub_date_str.strip()).astimezone(TZ_TAIPEI)
        return w_start <= dt <= w_end
    except Exception:
        return True

# ── 新聞爬取 ──────────────────────────────────────────────

RSS_SOURCES = [
    ("https://money.udn.com/rssfeed/news/2/5590?ch=money",  "經濟日報"),
    ("https://tw.news.yahoo.com/rss/finance",               "Yahoo財經"),
    ("https://tw.stock.yahoo.com/rss",                      "Yahoo股市"),
    ("https://www.moneydj.com/KMDJ/RSS/RSSFeed.aspx?svc=cn", "MoneyDJ"),
    ("https://news.cnyes.com/rss/tw_stock_news.xml",        "鉅亨台股"),
]

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx

def fetch_rss(url, source_name, w_start, w_end, max_items=30):
    articles, skipped = [], 0
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=make_ssl_ctx()) as resp:
            raw = resp.read()
        raw = re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]', b'', raw)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            raw = raw.decode("utf-8", errors="ignore").encode("utf-8")
            root = ET.fromstring(raw)
        for item in root.findall(".//item")[:max_items]:
            pub_date = item.findtext("pubDate") or ""
            if not in_window(pub_date, w_start, w_end):
                skipped += 1
                continue
            title   = strip_html(item.findtext("title") or "")
            link    = (item.findtext("link") or "").strip()
            summary = strip_html(item.findtext("description") or "")[:300]
            if title:
                articles.append({
                    "title":    title,
                    "url":      link,
                    "summary":  summary,
                    "source":   source_name,
                    "pub_date": pub_date,
                })
        print(f"[rss] {source_name}: {len(articles)} 則（略過舊聞 {skipped} 則）")
    except Exception as e:
        print(f"[rss] {source_name} 失敗: {e}")
    return articles

def fetch_all(w_start, w_end, max_per=30):
    all_arts = []
    for url, name in RSS_SOURCES:
        all_arts.extend(fetch_rss(url, name, w_start, w_end, max_per))
    seen, unique = set(), []
    for a in all_arts:
        k = a["title"][:30]
        if k not in seen:
            seen.add(k); unique.append(a)
    return unique

# ── Gemini API 分析 ───────────────────────────────────────

PROMPT = """你是台股財經新聞分析師。以下是「{window_start} 至 {window_end}（台北時間）」之間發布的財經新聞。
這段時間是上一個交易日收盤之後、今日開盤之前，屬於尚未反映於股價的新聞。

【分析規則】
1. 依產業分類，每產業挑 1~2 則最具市場影響力的新聞
2. 優先選擇「今日開盤可能直接反映」的消息（業績、政策、國際產業鏈變動）
3. 每則判斷影響：利多⚡ 或 利空⚠️
4. 標的：只有在「標題或摘要」中明確出現四位數股票代號（如 2330、0056）才列入；僅公司名稱填「無」
5. 精華：200 字以內，說明今日開盤最需關注的脈絡，純文字

【輸出格式（嚴格遵守，不可更改標記）】
===TRENDS===
【產業名稱】
• 重點：（一句話）
• 影響：⚡利多 或 ⚠️利空
• 標的：公司(代號) 或 無
• 來源：（來源名稱）

（重複多個產業區塊）

===SUMMARY===
（200字以內精華，純文字，不含 Markdown）

===LINKS===
（每行格式：標題|||URL|||來源，每行一則）

以下是待分析新聞：
{news}"""

def build_news_text(articles):
    lines = []
    for a in articles:
        line = f"[{a['source']}] {a['title']}"
        if a.get("pub_date"):
            line += f"  ({a['pub_date'][:22]})"
        if a.get("summary"):
            line += f"\n  摘要：{a['summary']}"
        if a.get("url"):
            line += f"\n  URL：{a['url']}"
        lines.append(line)
    return "\n\n".join(lines)

def call_gemini(news_text, api_key, w_start, w_end):
    prompt  = PROMPT.format(
        window_start = w_start.strftime("%m/%d %H:%M"),
        window_end   = w_end.strftime("%m/%d %H:%M"),
        news         = news_text,
    )
    url     = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2500, "temperature": 0.3},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60, context=make_ssl_ctx()) as resp:
        result = json.loads(resp.read())
    return result["candidates"][0]["content"]["parts"][0]["text"]

# ── 格式化 TG 訊息 ────────────────────────────────────────

def parse_sections(output):
    parts = re.split(r"===(\w+)===", output)
    data  = {}
    for i in range(1, len(parts), 2):
        data[parts[i].strip()] = parts[i + 1].strip() if i + 1 < len(parts) else ""
    return data

def format_message(gemini_output, w_start, w_end, n_articles):
    d       = parse_sections(gemini_output)
    trends  = d.get("TRENDS",  "（無法取得趨勢資料）")
    summary = d.get("SUMMARY", "（無法取得精華摘要）")
    links   = d.get("LINKS",   "")
    today   = datetime.now(TZ_TAIPEI).strftime("%Y-%m-%d")

    msg  = f"📊 盤前未反映新聞觀察 ({today})\n"
    msg += f"🕐 時間窗口：{w_start.strftime('%m/%d %H:%M')} → {w_end.strftime('%m/%d %H:%M')}（共 {n_articles} 則）\n\n"
    msg += trends + "\n"
    msg += "━━━━━━━━━━━━━━━\n"
    msg += "💡 盤前 200 字精華\n"
    msg += summary + "\n"

    if links:
        msg += "\n📎 新聞來源\n"
        for line in links.split("\n"):
            line = line.strip()
            if "|||" not in line:
                continue
            parts = line.split("|||")
            title = parts[0].strip()
            url   = parts[1].strip() if len(parts) > 1 else ""
            if url:
                msg += f"• [{title}]({url})\n"

    return msg

# ── 發送 TG ──────────────────────────────────────────────

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
        with urllib.request.urlopen(req, timeout=30, context=make_ssl_ctx()) as resp:
            result = json.loads(resp.read())
        if not result.get("ok"):
            print(f"[tg] 失敗: {result}")
            return False
    return True

# ── 主程式 ───────────────────────────────────────────────

def main():
    print(f"[news_tg] {datetime.now(TZ_TAIPEI).strftime('%Y-%m-%d %H:%M:%S')}")
    cfg     = load_config()
    token   = cfg["telegram"]["bot_token"]
    chat_id = cfg["telegram"]["chat_id"]
    api_key = cfg.get("gemini", {}).get("api_key", "")

    if not api_key:
        print("[news_tg] 錯誤：缺少 Gemini API key")
        sys.exit(1)

    # 1. 時間窗口
    w_start, w_end = get_window()
    print(f"[news_tg] 窗口：{w_start.strftime('%m/%d %H:%M')} → {w_end.strftime('%m/%d %H:%M')}")

    # 2. 抓新聞
    articles = fetch_all(w_start, w_end)
    print(f"[news_tg] 未反映新聞共 {len(articles)} 則")

    # 備援：窗口內無新聞時，改抓最近 24 小時
    if not articles:
        print("[news_tg] 窗口內無新聞，備援改抓最近 24 小時...")
        fallback_start = datetime.now(TZ_TAIPEI) - timedelta(hours=24)
        articles = fetch_all(fallback_start, datetime.now(TZ_TAIPEI))
        if articles:
            w_start = fallback_start
            w_end   = datetime.now(TZ_TAIPEI)
            print(f"[news_tg] 備援取得 {len(articles)} 則")

    if not articles:
        msg = (f"📊 盤前新聞觀察 ({datetime.now(TZ_TAIPEI).strftime('%Y-%m-%d')})\n\n"
               "⚠️ 各新聞來源目前無法連線，建議手動確認財經媒體。")
        send_tg(msg, token, chat_id)
        return

    # 3. Gemini 分析
    print("[news_tg] 呼叫 Gemini API...")
    news_text     = build_news_text(articles)
    gemini_output = call_gemini(news_text, api_key, w_start, w_end)

    # 4. 格式化 & 發送
    message = format_message(gemini_output, w_start, w_end, len(articles))
    print("[news_tg] 發送 Telegram...")
    ok = send_tg(message, token, chat_id)
    print("[news_tg] 發送成功！" if ok else "[news_tg] 發送失敗")

if __name__ == "__main__":
    main()
