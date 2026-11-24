# Buduje dist\ChocPilot.exe (PyInstaller, jeden plik).
# Użycie (PowerShell, w katalogu app):  .\build_exe.ps1
#   -NoRestart  nie uruchamiaj aplikacji po zbudowaniu (domyślnie wraca, jeśli była uruchomiona)
param([switch]$NoRestart)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$exe = Join-Path $PSScriptRoot "dist\ChocPilot.exe"

# Uruchomiony ChocPilot.exe blokuje plik – PyInstaller nie może go nadpisać (WinError 5).
# Zamykamy kopię z dist (onefile = 2 procesy: program startowy i aplikacja) i po budowie
# uruchamiamy ją z powrotem.
function Stop-BuiltApp {
    $running = @(Get-Process ChocPilot -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and ($_.Path -ieq $exe) })
    if ($running.Count -eq 0) { return $false }
    Write-Host "Zamykam uruchomiony ChocPilot.exe (PID $($running.Id -join ', ')), żeby go nadpisać..."
    $running | Stop-Process -Force
    # Plik bywa zablokowany jeszcze chwilę po zakończeniu procesu.
    for ($i = 0; $i -lt 20; $i++) {
        try {
            [IO.File]::Open($exe, 'Open', 'ReadWrite', 'None').Close()
            return $true
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "Plik $exe jest nadal zablokowany – zamknij ChocPilot ręcznie i spróbuj ponownie."
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Instalacja zależności nie powiodła się" }

& $py scripts\make_icon.py
if ($LASTEXITCODE -ne 0) { throw "Nie udało się wygenerować ikony" }

$wasRunning = $false
if (Test-Path $exe) { $wasRunning = Stop-BuiltApp }

& $py -m PyInstaller chocpilot.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller zakończył się błędem" }

Write-Host "Gotowe: $exe"
if ($wasRunning -and -not $NoRestart) {
    Write-Host "Uruchamiam ponownie ChocPilot..."
    Start-Process $exe
}
