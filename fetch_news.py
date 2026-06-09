"""
爬取財經 RSS，儲存為 news_raw.json
時間窗口：昨天收盤（13:30）→ 今天開盤前（09:00）
週末自動回溯至上週五 13:30
來源：中央社財經 / 鉅亨網 / 工商時報 / 經濟日報 / 自由財經 / Yahoo財經
"""

import json
import os
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

BASE = os.path.dirname(os.path.abspath(__file__))
TZ_TAIPEI = timezone(timedelta(hours=8))

# ── 時間窗口計算 ───────────────────────────────────────────

def get_window():
    """
    固定窗口：前一個交易日 13:30 → 當天 09:00
    無論幾點執行，窗口上限都是今天 09:00，避免把盤中新聞混入。
    週一往回取週五，週六/日同樣取週五。
    """
    now     = datetime.now(TZ_TAIPEI)
    today   = now.date()
    weekday = today.weekday()   # 0=週一 … 6=週日

    if weekday == 0:    prev = today - timedelta(days=3)   # 週一→上週五
    elif weekday >= 5:  prev = today - timedelta(days=weekday - 4)  # 週六/日→上週五
    else:               prev = today - timedelta(days=1)

    window_start = datetime(prev.year,  prev.month,  prev.day,  13, 30, tzinfo=TZ_TAIPEI)
    window_end   = datetime(today.year, today.month, today.day,  9,  0, tzinfo=TZ_TAIPEI)

    return window_start, window_end

def in_window(pub_date_str, window_start, window_end):
    """
    判斷文章是否在時間窗口內。
    無法解析 pubDate 的文章：保留（寧可多看）。
    """
    if not pub_date_str:
        return True
    try:
        dt = parsedate_to_datetime(pub_date_str.strip())
        dt_taipei = dt.astimezone(TZ_TAIPEI)
        return window_start <= dt_taipei <= window_end
    except Exception:
        return True  # 解析失敗保留

# ── RSS 來源 ───────────────────────────────────────────────

RSS_SOURCES = [
    # 中央社財經（最穩定的官方媒體）
    ("https://www.cna.com.tw/rss/afinance.aspx",            "中央社財經"),
    # 鉅亨網
    ("https://news.cnyes.com/rss/news.xml",                  "鉅亨網"),
    # 工商時報
    ("https://ctee.com.tw/news/feed",                        "工商時報"),
    # 經濟日報
    ("https://money.udn.com/rssfeed/news/2/5590?ch=money",   "經濟日報"),
    # 自由財經
    ("https://ec.ltn.com.tw/rss/market.xml",                 "自由財經"),
    # Yahoo 財經台灣
    ("https://tw.news.yahoo.com/rss/finance",                "Yahoo財經"),
]

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control":   "no-cache",
}

# ── 工具函式 ───────────────────────────────────────────────

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx

# ── 核心爬取 ───────────────────────────────────────────────

def fetch_rss(url, source_name, window_start, window_end, max_items=30):
    articles = []
    skipped  = 0
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=make_ssl_ctx()) as resp:
            raw = resp.read()
        root  = ET.fromstring(raw)
        items = root.findall(".//item")
        for item in items[:max_items]:
            pub_date = item.findtext("pubDate") or ""
            if not in_window(pub_date, window_start, window_end):
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
        print(f"[rss] {source_name}: {len(articles)} 則（過濾掉 {skipped} 則舊聞）")
    except Exception as e:
        print(f"[rss] {source_name} 失敗: {e}")
    return articles

# ── 主程式 ────────────────────────────────────────────────

def main():
    window_start, window_end = get_window()
    print(f"[fetch] 時間窗口: {window_start.strftime('%m/%d %H:%M')} → {window_end.strftime('%m/%d %H:%M')} (台北時間)")

    all_articles = []
    for url, name in RSS_SOURCES:
        arts = fetch_rss(url, name, window_start, window_end)
        all_articles.extend(arts)

    # 去重（同標題）
    seen   = set()
    unique = []
    for a in all_articles:
        key = a["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    out_path = os.path.join(BASE, "news_raw.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "fetched_at":   datetime.now(TZ_TAIPEI).strftime("%Y-%m-%d %H:%M:%S"),
            "window_start": window_start.strftime("%Y-%m-%d %H:%M"),
            "window_end":   window_end.strftime("%Y-%m-%d %H:%M"),
            "articles":     unique,
        }, f, ensure_ascii=False, indent=2)

    print(f"[fetch] 共 {len(unique)} 則未反映新聞，已存至 news_raw.json")

if __name__ == "__main__":
    main()
