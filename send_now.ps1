# 發送 Telegram 訊息
$msgPath = "C:\Users\user\Claude\Projects\新聞整理專家\msg.txt"
$configPath = "C:\Users\user\Claude\Projects\新聞整理專家\config.json"

$config = Get-Content $configPath | ConvertFrom-Json
$token = $config.telegram.bot_token
$chatId = $config.telegram.chat_id
$text = Get-Content $msgPath -Raw -Encoding UTF8

$url = "https://api.telegram.org/bot$token/sendMessage"
$body = @{
    chat_id = $chatId
    text = $text
    parse_mode = "Markdown"
    disable_web_page_preview = $true
} | ConvertTo-Json -Compress

$response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json; charset=utf-8"
if ($response.ok) {
    Write-Host "[tg] 發送成功！"
} else {
    Write-Host "[tg] 發送失敗: $($response | ConvertTo-Json)"
}
