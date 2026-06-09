# 盤前新聞整理 → Telegram

執行盤前新聞整理並發送到 Telegram。
**目標：只整理「上一個交易日收盤後 → 今日開盤前」尚未反映於股價的新聞。**

---

## 步驟

### 1. 計算時間窗口

用 bash 取得今天星期幾：
```bash
python3 -c "
from datetime import date, timedelta
today = date.today()
wd = today.weekday()  # 0=週一
if wd == 0:   prev = today - timedelta(days=3)
elif wd >= 5: prev = today - timedelta(days=wd-4)
else:         prev = today - timedelta(days=1)
print(f'today={today} weekday={wd} prev_close_date={prev}')
"
```

記下 `prev_close_date`（上一個交易日）和今天日期。

### 2. WebSearch 抓取時間窗口內的新聞

執行 **3~4 次** WebSearch，每次使用不同主題，搜尋條件加上日期限制 `after:YYYY-MM-DD`（填入 prev_close_date）。

建議搜尋主題：
- `台股 AI半導體 外資 after:{prev_close_date}` 
- `美股 費半 科技股 收盤 after:{prev_close_date}`
- `台積電 聯發科 財報 法說 after:{prev_close_date}`
- `總體經濟 Fed 利率 匯率 after:{prev_close_date}`

只保留發布時間在 `prev_close_date 13:30` 之後的新聞。如果搜尋結果的日期早於這個時間，明確排除它。

### 3. 分析新聞（Claude 直接做，不需呼叫外部 API）

根據步驟 2 找到的「未反映新聞」，製作以下格式的訊息。
若某個類別完全沒有相關新聞，跳過該區塊：

```
📊 盤前未反映新聞觀察 (YYYY-MM-DD)
🕐 時間窗口：MM/DD 13:30 → MM/DD 09:00（共 N 則）

【產業名稱】
• 重點：（一句話）
• 影響：⚡利多 或 ⚠️利空
• 標的：公司(代號)  ← 只有標題或摘要明確出現四位數代號才列，否則填「無」
• 來源：（來源名稱）

（重複多個產業區塊）
━━━━━━━━━━━━━━━
💡 今日盤前 200 字精華
（200字以內，說明開盤最需關注的脈絡，純文字）

📎 新聞來源
• [標題](URL)
```

**分析重點（依優先度）：**
1. 美股收盤／亞股夜盤對台股的直接連動
2. 重要財報、法說會、EPS 超預期/不如預期
3. 產業政策、關稅、出口管制等政策面
4. 外資/主力籌碼異動
5. 個別公司重大消息（合約、訴訟、人事）

### 4. 發送到 Telegram

將整段格式化好的訊息寫入 `C:\Users\user\Claude\Projects\新聞整理專家\msg.txt`（用 Write 工具），
然後用 **computer-use** 執行：

```
request_access: 檔案總管
```

在 File Explorer 開啟 `C:\Users\user\Claude\Projects\新聞整理專家`，
雙擊 `run_morning.bat` 執行（Python 讀取 msg.txt 並發送到 TG）。

等待 CMD 視窗出現「[tg] 發送成功！」後確認完成。

---

## 設定檔
`C:\Users\user\Claude\Projects\新聞整理專家\config.json`（bot_token 和 chat_id 已填好）

## 注意事項

- **時間窗口是核心**：只看收盤後的新聞，舊聞一律排除
- 週一時間窗口從上週五 13:30 起算
- WebSearch 若找不到時間窗口內的新聞，仍發送訊息說明「本時段無重大新聞」
- run_morning.bat 執行 send_tg.py，需要 Python 已安裝在系統 PATH
