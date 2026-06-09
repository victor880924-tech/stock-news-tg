@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Claude\Projects\新聞整理專家"
echo 測試訊息 - 請確認收到 | python -X utf8 send_tg.py > test_log.txt 2>&1
if errorlevel 1 echo 測試訊息 - 請確認收到 | python3 -X utf8 send_tg.py >> test_log.txt 2>&1
echo [done] >> test_log.txt
