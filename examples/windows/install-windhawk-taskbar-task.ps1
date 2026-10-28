# EJEMPLO para adaptar (no es parte del producto hueman).
# Que hace: instalador de una sola vez. Copia windhawk-taskbar-apply.ps1 a
# $env:ProgramData\DotfilesTheme (carpeta solo escribible por administradores)
# y registra una tarea programada de disparo manual con RunLevel Highest, para
# que hueman (desde WSL) la lance con `schtasks.exe /run /tn <NombreTarea>`
# sin prompt de UAC. Con -Uninstall elimina la tarea y la carpeta.
# Requiere elevacion: ejecutalo desde un PowerShell como Administrador, con
# windhawk-taskbar-apply.ps1 en la misma carpeta.
# Sin probar en este repo: revisa el script antes de ejecutarlo.
<#
.SYNOPSIS
  One-time installer: registers a scheduled task that applies taskbar colors
  to the Windhawk taskbar-styler mod. Run manually from an elevated PowerShell.
.PARAMETER TaskName
  Scheduled task name.
.PARAMETER DataFile
  JSON file written by `theme set` (keys: fill, text).
.PARAMETER Uninstall
  Remove the task and the ProgramData folder.
#>
[CmdletBinding()]
param(
    [string]$TaskName = 'DotfilesThemeWindhawk',
    [string]$DataFile = (Join-Path $env:LOCALAPPDATA 'DotfilesTheme\taskbar-colors.json'),
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'This installer must run from an elevated (Administrator) PowerShell.'
}

$InstallDir = Join-Path $env:ProgramData 'DotfilesTheme'
$ScriptName = 'windhawk-taskbar-apply.ps1'
$Target     = Join-Path $InstallDir $ScriptName

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "Removed scheduled task $TaskName."
    }
    if (Test-Path -LiteralPath $InstallDir) {
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
        Write-Output "Removed $InstallDir."
    }
    Write-Output "Left in place (remove manually if desired): $(Split-Path -Parent $DataFile)"
    return
}

$source = Join-Path $PSScriptRoot $ScriptName
if (-not (Test-Path -LiteralPath $source)) {
    throw "Apply script not found next to the installer: $source"
}

# Admin-only install directory: SYSTEM and Administrators full control,
# Users read/execute only, inheritance removed.
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
& icacls.exe $InstallDir /inheritance:r `
    /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "icacls failed with exit code $LASTEXITCODE." }

Copy-Item -LiteralPath $source -Destination $Target -Force

# User-writable data directory (the data file is validated strictly by the script).
$dataDir = Split-Path -Parent $DataFile
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

$arg = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -DataFile "{1}"' -f $Target, $DataFile
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
$taskPrin  = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Principal $taskPrin `
    -Settings $settings -Force | Out-Null

Write-Output "Installed apply script : $Target"
Write-Output "Registered task        : $TaskName (user $($identity.Name), RunLevel Highest, manual trigger)"
Write-Output "Data file              : $DataFile"
Write-Output "Run now                : schtasks.exe /run /tn $TaskName"
Write-Output "Uninstall              : $PSCommandPath -Uninstall -TaskName $TaskName"
