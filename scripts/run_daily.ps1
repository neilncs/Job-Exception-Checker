# Unattended daily run (Windows). Called by Task Scheduler - see README "Scheduling".
#
# Claude Code runs headless (-p) with a locked-down permission set:
#   allowed  : read files, run the checker script, write inside output/
#   denied   : everything else (dontAsk mode refuses any tool not listed) - so it
#              cannot send email, edit data/ or config/, or run other commands.
#
# Reliability (an early-morning run must be finished before the working day starts):
#   - restores APPDATA/LOCALAPPDATA if Task Scheduler started us without them (Python can't find
#     per-user packages such as PyYAML without APPDATA - this broke the first scheduled test run)
#   - checks Python and PyYAML before doing anything else
#   - keeps the PC awake while running (a laptop dropping into standby froze one test run for 96 minutes)
#   - waits for the network before calling Claude
#   - each Claude attempt is stopped after $AttemptMinutes, and retried up to $MaxAttempts times
#   - ANY failure writes RUN_FAILED.md (or the checker's INPUT_ERROR.md), so the dashboard can never
#     show a stale green day
param(
    [int]$MaxAttempts = 3,
    [int]$AttemptMinutes = 15,
    [int]$NetworkWaitMinutes = 10
)
$ErrorActionPreference = "Continue"
$SkillDir = Split-Path -Parent $PSScriptRoot
Set-Location $SkillDir

# --- Environment Task Scheduler may leave out ------------------------------------------------
if (-not $env:APPDATA)      { $env:APPDATA      = [Environment]::GetFolderPath("ApplicationData") }
if (-not $env:LOCALAPPDATA) { $env:LOCALAPPDATA = [Environment]::GetFolderPath("LocalApplicationData") }
$env:PYTHONIOENCODING = "utf-8"

$date     = Get-Date -Format "yyyy-MM-dd"
$runDir   = Join-Path $SkillDir "output\$date"
$logDir   = Join-Path $SkillDir "output\logs"
$log      = Join-Path $logDir "$date.log"
$report   = Join-Path $runDir "exceptions_report.md"
$failNote = Join-Path $runDir "RUN_FAILED.md"
New-Item -ItemType Directory -Force $logDir, $runDir | Out-Null
if (Test-Path $failNote) { Remove-Item $failNote }  # a note from an earlier attempt today; rewritten if this run fails
function Write-Log($msg) { "$(Get-Date -Format 'HH:mm:ss')  $msg" | Add-Content -Path $log -Encoding utf8 }
# Run a Python script, appending its output to the log as UTF-8 (PowerShell 5.1's own redirection writes UTF-16)
function Invoke-Py($script) {
    cmd /c "python scripts\$script >> `"$log`" 2>&1"
    return $LASTEXITCODE
}

# --- Keep the PC awake until this script ends -------------------------------------------
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
$ES_CONTINUOUS = [uint32]"0x80000000"; $ES_SYSTEM_REQUIRED = [uint32]"0x00000001"
[void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)

# Stop the run, leaving a clear note for the dashboard and the person reading it at 08:00
function Stop-Run([string]$reason, [int]$code = 1) {
    @"
# Run failed - $date

$reason

- Anything else in this folder may be from an earlier run - don't rely on it for today.
- Step-by-step timings and errors: ``output/logs/$date.log``
- To try again now: double-click ``Run check now.cmd``, or ask Claude Code in this folder to
  "run the solar job exceptions check".
"@ | Set-Content -Path $failNote -Encoding utf8
    Write-Log "FAILED: $reason"
    $null = Invoke-Py "build_dashboard.py"
    Write-Log "Dashboard updated: output\dashboard.html"
    [void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS)
    exit $code
}

Write-Log "Run started (max $MaxAttempts attempts, $AttemptMinutes min each)"

# --- Python and PyYAML ------------------------------------------------------------------------
$pyInfo = cmd /c "python -c `"import sys, yaml; print(sys.executable, sys.version.split()[0], 'PyYAML', yaml.__version__)`" 2>&1"
if ($LASTEXITCODE -ne 0) {
    Stop-Run ("Python or the PyYAML package isn't available to the scheduled run, so the checks could not start. " +
              "Details: $(($pyInfo | Select-Object -Last 1)). Fix: run ``python -m pip install -r requirements.txt`` in this folder.")
}
Write-Log "Python: $pyInfo"

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
if ($checkCode -eq 2) {
    # The checker has written INPUT_ERROR.md explaining which file is broken; the dashboard shows it in red
    if (Test-Path $failNote) { Remove-Item $failNote }
    Write-Log "STOPPED: input error - see output\$date\INPUT_ERROR.md"
    $null = Invoke-Py "build_dashboard.py"
    [void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS)
    exit 2
}
if ($checkCode -ne 0) {
    Stop-Run "The deterministic checks crashed (exit code $checkCode), so there are no reliable results for today."
}
Write-Log "Checks complete"

# --- Claude, with a time limit per attempt and retries ------------------------------------
$claude = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $claude) { Stop-Run "The checks ran (see checks_summary.md), but the 'claude' command wasn't found, so there is no report or draft emails today." }
$prompt = "Run the solar job exceptions check for $date. The scheduler has already run step 1 (the deterministic checks) " +
          "for today, so start at step 2 using output/$date/exceptions.json. Follow SKILL.md in this folder exactly. " +
          "This is an unattended scheduled run: do not ask questions; put anything uncertain under Needs human review."
# Claude gets NO shell access: it may only read files and write inside output/ (Edit rules cover every
# file-writing tool). The checks above were run by this script, not by Claude.
$argLine = @(
    "-p", "`"$prompt`"",
    "--permission-mode", "dontAsk",
    "--allowedTools", "Read", "Glob", "Grep", "`"Edit(./output/**)`""
) -join " "

# Clear today's previous report and drafts, so everything in the folder comes from this run
Remove-Item $report, (Join-Path $runDir "draft_emails\*.md") -ErrorAction SilentlyContinue

$ok = $false
for ($attempt = 1; $attempt -le $MaxAttempts -and -not $ok; $attempt++) {
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
        if ($p.ExitCode -ne 0) { Write-Log ("  " + ((Get-Content $out, $err -ErrorAction SilentlyContinue | Select-Object -Last 2) -join " | ")) }
        $ok = ($p.ExitCode -eq 0) -and $fresh
    }
    if (-not $ok -and $attempt -lt $MaxAttempts) { Start-Sleep -Seconds 120 }
}

# --- Outcome --------------------------------------------------------------------------------
if (-not $ok) {
    Stop-Run ("The checks ran (see checks_summary.md and exceptions.json in this folder), but Claude's report " +
              "did not finish after $MaxAttempts attempts, so there is no up-to-date report or draft emails today.")
}
if (Test-Path $failNote) { Remove-Item $failNote }
Write-Log "SUCCESS: report ready at $report"
$null = Invoke-Py "build_dashboard.py"
Write-Log "Dashboard updated: output\dashboard.html"
[void][Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS)
exit 0
