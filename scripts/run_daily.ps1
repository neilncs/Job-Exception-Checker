# Unattended daily run (Windows). Called by Task Scheduler - see README "Scheduling".
#
# Claude Code runs headless (-p) with a locked-down permission set:
#   allowed  : read files, run the checker script, write inside output/
#   denied   : everything else (dontAsk mode refuses any tool not listed) - so it
#              cannot send email, edit data/ or config/, or run other commands.
#
# Reliability (an early-morning run must be finished before the working day starts):
#   - keeps the PC awake while running (a laptop dropping into standby froze one test run for 96 minutes)
#   - waits for the network before calling Claude
#   - each attempt is stopped after $AttemptMinutes, and retried up to $MaxAttempts times
#   - if every attempt fails, the deterministic checks still run and RUN_FAILED.md explains what is missing
param(
    [int]$MaxAttempts = 3,
    [int]$AttemptMinutes = 15,
    [int]$NetworkWaitMinutes = 10
)
$ErrorActionPreference = "Continue"
$SkillDir = Split-Path -Parent $PSScriptRoot
Set-Location $SkillDir

$date    = Get-Date -Format "yyyy-MM-dd"
$runDir  = Join-Path $SkillDir "output\$date"
$logDir  = Join-Path $SkillDir "output\logs"
$log     = Join-Path $logDir "$date.log"
$report  = Join-Path $runDir "exceptions_report.md"
New-Item -ItemType Directory -Force $logDir | Out-Null
function Write-Log($msg) { "$(Get-Date -Format 'HH:mm:ss')  $msg" | Add-Content -Path $log -Encoding utf8 }
# Run a Python script, appending its output to the log as UTF-8 (PowerShell 5.1's own redirection writes UTF-16)
$env:PYTHONIOENCODING = "utf-8"
function Invoke-Py($script) {
    cmd /c "python scripts\$script >> `"$log`" 2>&1"
    return $LASTEXITCODE
}

# --- Keep the PC awake until this script ends -------------------------------------------
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
$ES_CONTINUOUS = [uint32]"0x80000000"; $ES_SYSTEM_REQUIRED = [uint32]"0x00000001"
[void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)

Write-Log "Run started (max $MaxAttempts attempts, $AttemptMinutes min each)"

# --- Wait for the network ------------------------------------------------------------------
function Test-Api {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("api.anthropic.com", 443); $c.Close(); return $true }
    catch { return $false }
}
$deadline = (Get-Date).AddMinutes($NetworkWaitMinutes)
while (-not (Test-Api) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 15 }
if (Test-Api) { Write-Log "Network OK" } else { Write-Log "WARNING: api.anthropic.com not reachable after $NetworkWaitMinutes min - trying anyway" }

# --- Deterministic checks first: if the inputs are broken there is no point calling Claude -
$checkCode = Invoke-Py "run_checks.py"
if ($checkCode -ne 0) {
    Write-Log "STOPPED: checker exited with code $checkCode (2 = input error, see output\$date\INPUT_ERROR.md)"
    $null = Invoke-Py "build_dashboard.py"
    [void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS)
    exit $checkCode
}
Write-Log "Checks complete"

# --- Claude, with a time limit per attempt and retries ------------------------------------
$claude = (Get-Command claude -ErrorAction SilentlyContinue).Source
$prompt = "Run the solar job exceptions check. Follow SKILL.md in this folder exactly. " +
          "This is an unattended scheduled run: do not ask questions; put anything uncertain under Needs human review."
# Edit(path) rules cover every file-writing tool, so this is the only write permission granted.
$argLine = @(
    "-p", "`"$prompt`"",
    "--permission-mode", "dontAsk",
    "--allowedTools", "Read", "Glob", "Grep",
    "`"Bash(python scripts/run_checks.py:*)`"", "`"PowerShell(python scripts/run_checks.py:*)`"",
    "`"Edit(./output/**)`""
) -join " "

$ok = $false
for ($attempt = 1; $attempt -le $MaxAttempts -and -not $ok -and $claude; $attempt++) {
    $start = Get-Date
    $out = Join-Path $logDir "$date-attempt$attempt.out.log"
    $err = Join-Path $logDir "$date-attempt$attempt.err.log"
    Write-Log "Attempt $attempt started"
    $p = Start-Process -FilePath $claude -ArgumentList $argLine -NoNewWindow -PassThru `
                       -RedirectStandardOutput $out -RedirectStandardError $err
    $null = $p.Handle  # needed so ExitCode is available after exit (PowerShell 5.1 quirk)
    if (-not $p.WaitForExit($AttemptMinutes * 60 * 1000)) {
        & taskkill.exe /PID $p.Id /T /F | Out-Null
        Write-Log "Attempt $attempt stopped after $AttemptMinutes min (no finish)"
    } else {
        $fresh = (Test-Path $report) -and ((Get-Item $report).LastWriteTime -gt $start)
        Write-Log ("Attempt $attempt exited with code {0} in {1:n0}s; report written: {2}" -f $p.ExitCode, ((Get-Date) - $start).TotalSeconds, $fresh)
        $ok = ($p.ExitCode -eq 0) -and $fresh
    }
    if (-not $ok -and $attempt -lt $MaxAttempts) { Start-Sleep -Seconds 120 }
}

# --- Outcome --------------------------------------------------------------------------------
$failNote = Join-Path $runDir "RUN_FAILED.md"
if ($ok) {
    if (Test-Path $failNote) { Remove-Item $failNote }
    Write-Log "SUCCESS: report ready at $report"
    $code = 0
} else {
    if (-not $claude) { Write-Log "ERROR: 'claude' not found on PATH" }
    # Make sure today's facts exist even without the Claude step
    if (-not (Test-Path (Join-Path $runDir "exceptions.json")) -or (Get-Item (Join-Path $runDir "exceptions.json")).LastWriteTime.Date -ne (Get-Date).Date) {
        $null = Invoke-Py "run_checks.py"
    }
    New-Item -ItemType Directory -Force $runDir | Out-Null
    @"
# Run incomplete - $date

The Claude step did not finish after $MaxAttempts attempts, so there is no ``exceptions_report.md`` or draft emails today.

- The deterministic results are still available: ``checks_summary.md`` and ``exceptions.json`` in this folder.
- Reason and timings: ``output/logs/$date.log``
- To finish the run now, ask Claude Code in this folder to "run the solar job exceptions check",
  or run ``scripts/run_daily.ps1`` again.
"@ | Set-Content -Path $failNote -Encoding utf8
    Write-Log "FAILED: wrote $failNote"
    $code = 1
}
# --- Refresh the dashboard (works for success and failure alike) ----------------------------
$null = Invoke-Py "build_dashboard.py"
Write-Log "Dashboard updated: output\dashboard.html"
[void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS)
exit $code
