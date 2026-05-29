$TaskName = "MarketingCrawlerDaily8AM"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "작업 스케줄러 삭제 완료: $TaskName"
} else {
    Write-Host "삭제할 작업이 없습니다: $TaskName"
}
