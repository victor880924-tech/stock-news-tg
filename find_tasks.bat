@echo off
chcp 65001 > nul
powershell -NoProfile -Command "Get-ScheduledTask | Where-Object { $_.TaskName -match 'news|morning|claude|cowork' -or $_.TaskPath -match 'claude|cowork' } | Select-Object TaskName, TaskPath, State | Format-List" > find_tasks.txt 2>&1
powershell -NoProfile -Command "Get-ScheduledTask | Select-Object TaskName, TaskPath | Sort-Object TaskPath" >> find_tasks.txt 2>&1
echo [done] >> find_tasks.txt
