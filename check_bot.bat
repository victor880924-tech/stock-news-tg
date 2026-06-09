@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Claude\Projects\新聞整理專家"
python -X utf8 -c "
import urllib.request, json

token = '8561599489:AAEymG9WEk4GXRKvymJmfKwZIe2ZDq2slx4'

# getMe
with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getMe') as r:
    me = json.loads(r.read())
print('Bot:', me['result']['username'], me['result']['first_name'])

# getUpdates - last 5
with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getUpdates?limit=5&offset=-5') as r:
    upd = json.loads(r.read())
for u in upd.get('result', []):
    msg = u.get('message') or u.get('my_chat_member') or {}
    chat = msg.get('chat', {})
    frm  = msg.get('from', {})
    print(f'chat_id={chat.get(\"id\")}  from_id={frm.get(\"id\")}  username={frm.get(\"username\")}  text={msg.get(\"text\",\"\")[:40]}')
" > check_bot.txt 2>&1
echo [done] >> check_bot.txt
