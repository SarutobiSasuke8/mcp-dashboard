<#
.SYNOPSIS
    Registers a scheduled task that runs a quiet MCP Dashboard scan, so the
    RAM trend chart accumulates and the vault notes stay current.

.DESCRIPTION
    Creates (or replaces) a Windows scheduled task that runs
    mcp_dashboard.py with --no-cli, and optionally --report, on an interval.
    The scan is read-only: it never toggles servers. Probing is off by
    default because it starts each server briefly; pass -Probe to include it.

.EXAMPLE
    .\Register-MCPDashboardScan.ps1
    Every 4 hours, quiet scan, refreshes the dashboard and MCP Directory.

.EXAMPLE
    .\Register-MCPDashboardScan.ps1 -IntervalHours 12 -Report -Probe
    Twice daily, also appends to the usage report and refreshes context cost.

.EXAMPLE
    .\Register-MCPDashboardScan.ps1 -Unregister
#>

[CmdletBinding()]
param(
    [int]$IntervalHours = 4,
    [string]$TaskName = "MCP Dashboard Scan",
    [switch]$Report,
    [switch]$Probe,
    [switch]$Tasks,
    [string]$PythonPath,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dashboard = Join-Path $scriptDir "mcp_dashboard.py"

if ($Unregister) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'."
    } else {
        Write-Host "No scheduled task named '$TaskName'."
    }
    return
}

if (-not (Test-Path $dashboard)) {
    throw "mcp_dashboard.py not found next to this script ($dashboard)."
}

if (-not $PythonPath) {
    # `?.` is PowerShell 7+ only; keep this 5.1-compatible.
    $pyCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($pyCmd) { $PythonPath = $pyCmd.Source }
    if (-not $PythonPath) {
        $pyCmd = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($pyCmd) { $PythonPath = $pyCmd.Source }
    }
    if (-not $PythonPath) { throw "Python not found on PATH; pass -PythonPath." }
}

$argList = @("`"$dashboard`"", "--no-cli")
if ($Report) { $argList += "--report" }
if ($Probe)  { $argList += "--probe" }
if ($Tasks)  { $argList += "--tasks" }

$action = New-ScheduledTaskAction -Execute $PythonPath `
    -Argument ($argList -join " ") -WorkingDirectory $scriptDir

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Quiet MCP Dashboard scan; refreshes the dashboard, MCP Directory, and RAM history." `
    -Force | Out-Null

Write-Host "Registered '$TaskName': $PythonPath $($argList -join ' ')"
Write-Host "Runs every $IntervalHours hour(s). Remove with: .\Register-MCPDashboardScan.ps1 -Unregister"
