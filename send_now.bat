@echo off
cd /d "C:\Users\user\Claude\Projects\新聞整理專家"
python -X utf8 send_tg.py < msg.txt
if errorlevel 1 python3 -X utf8 send_tg.py < msg.txt
pause
