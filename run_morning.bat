@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Claude\Projects\新聞整理專家"
echo [%date% %time%] 開始執行盤前新聞整理...
python -X utf8 news_tg.py
if errorlevel 1 (
    echo [ERROR] news_tg.py 執行失敗，嘗試 python3...
    python3 -X utf8 news_tg.py
)
echo [%date% %time%] 執行完成
