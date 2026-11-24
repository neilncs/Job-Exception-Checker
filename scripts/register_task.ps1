# Register (or remove) the daily 06:30 scheduled task for this folder.
#
#   Register and start a test run now:   powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1 -RunNow
#   Register only:                        powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
#   Remove the task:                      powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1 -Remove
#
# The task runs scripts\run_daily.ps1 from wherever this folder lives, as you, while you're logged in
# (a locked screen is fine). It wakes the PC from sleep on mains power, runs at the next start-up
# if it was missed, and is stopped after 90 minutes as a last resort.
param([switch]$RunNow, [switch]$Remove, [string]$At = "6:30am")
$ErrorActionPreference = "Stop"
$name   = "Solar Job Exceptions"
$runner = Join-Path $PSScriptRoot "run_daily.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Removed scheduled task '$name'."
    exit 0
}

$action   = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$trigger  = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 90)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Force `
    -Description "Daily solar job exceptions check (Claude Code headless)" | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $name
Write-Host "Registered '$name': runs daily at $At (next: $($info.NextRunTime))."
Write-Host "Runner: $runner"

if ($RunNow) {
    Start-ScheduledTask -TaskName $name
    Write-Host "Test run started. It takes about 2 minutes; the dashboard is output\dashboard.html."
}
