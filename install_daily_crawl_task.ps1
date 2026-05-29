$ErrorActionPreference = "Stop"

$TaskName = "MarketingCrawlerDaily8AM"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (& python -c "import sys; print(sys.executable)").Trim()
$Runner = Join-Path $ProjectDir "daily_crawl_with_kakao.py"
$LogDir = Join-Path $ProjectDir "logs"

if (!(Test-Path $Runner)) {
    throw "daily_crawl_with_kakao.py 파일을 찾을 수 없습니다: $Runner"
}

if (!(Test-Path $PythonExe)) {
    throw "실제 Python 실행 파일을 찾을 수 없습니다: $PythonExe"
}

if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$ActionCommand = "powershell.exe"
$ActionArgs = "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$ProjectDir'; `$env:PYTHONIOENCODING='utf-8'; & '$PythonExe' -u '$Runner' *> '$LogDir\daily_crawl_latest.log'`""

$Action = New-ScheduledTaskAction -Execute $ActionCommand -Argument $ActionArgs
$Trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "매일 오전 8시에 6개 통신 사이트를 크롤링하고 카카오톡으로 진행 상황을 전송합니다." `
    -Force | Out-Null

Write-Host "작업 스케줄러 등록 완료: $TaskName"
Write-Host "실행 시간: 매일 오전 8:00"
Write-Host "프로젝트 폴더: $ProjectDir"
Write-Host "로그 파일: $LogDir\daily_crawl_latest.log"
Write-Host ""
Write-Host "바로 테스트 실행하려면:"
Write-Host "Start-ScheduledTask -TaskName $TaskName"
