@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Claude\Projects\新聞整理專家"
python -X utf8 send_tg.py < msg.txt > send_log.txt 2>&1
if errorlevel 1 python3 -X utf8 send_tg.py < msg.txt >> send_log.txt 2>&1
echo. >> send_log.txt
echo [done] >> send_log.txt
