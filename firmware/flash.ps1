# Buduje firmware ChocPilot i wgrywa je do Pro Micro (bootloader Caterina, avrdude).
# Użycie (PowerShell, w katalogu firmware):
#   .\flash.ps1                    – Pro Micro 5 V / 16 MHz, port wykrywany automatycznie
#   .\flash.ps1 -Board 3v3         – Pro Micro 3,3 V / 8 MHz
#   .\flash.ps1 -Port COM7         – konkretny port (działającego firmware albo bootloadera)
#   .\flash.ps1 -BuildOnly         – tylko kompilacja, bez wgrywania
#   .\flash.ps1 -CloseApp          – najpierw zamyka aplikację ChocPilot (trzyma port COM)
param(
    [ValidateSet("5v", "3v3")]
    [string]$Board = "5v",
    [string]$Port = "",
    [switch]$BuildOnly,
    [switch]$CloseApp
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$envName = if ($Board -eq "3v3") { "promicro_3v3" } else { "promicro" }

# PlatformIO: z PATH, z instalacji VS Code / instalatora (~\.platformio), albo instalujemy przez pip.
function Find-Pio {
    $cmd = Get-Command pio -ErrorAction SilentlyContinue
    if ($cmd) { return @($cmd.Source) }
    $local = Join-Path $env:USERPROFILE ".platformio\penv\Scripts\pio.exe"
    if (Test-Path $local) { return @($local) }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -m platformio --version *> $null
        if ($LASTEXITCODE -eq 0) { return @($py.Source, "-m", "platformio") }
        Write-Host "Nie znaleziono PlatformIO – instaluję (python -m pip install --user platformio)..."
        & $py.Source -m pip install --user platformio
        if ($LASTEXITCODE -ne 0) { throw "Instalacja PlatformIO nie powiodła się" }
        return @($py.Source, "-m", "platformio")
    }
    throw "Nie znaleziono PlatformIO ani Pythona. Zainstaluj PlatformIO: https://platformio.org/install"
}

$pio = @(Find-Pio)  # @(): jednoelementowa tablica nie może się „rozwinąć” do napisu
$pioExe = $pio[0]
$pioArgs = @($pio | Select-Object -Skip 1)
Write-Host "PlatformIO: $($pio -join ' ')"

# Aplikacja ChocPilot trzyma port COM – wgrywanie by się nie udało.
$app = Get-Process -Name "ChocPilot" -ErrorAction SilentlyContinue
if ($app -and -not $BuildOnly) {
    if ($CloseApp) {
        Write-Host "Zamykam aplikację ChocPilot..."
        $app | Stop-Process
        Start-Sleep -Seconds 1
    } else {
        throw "Aplikacja ChocPilot działa i trzyma port COM. Zamknij ją (zasobnik → Wyjdź) albo uruchom: .\flash.ps1 -CloseApp"
    }
}

$runArgs = $pioArgs + @("run", "-e", $envName)
if (-not $BuildOnly) {
    $runArgs += @("-t", "upload")
    if ($Port) { $runArgs += @("--upload-port", $Port) }
}
& $pioExe @runArgs
if ($LASTEXITCODE -ne 0) {
    if ($BuildOnly) { throw "Kompilacja nie powiodła się" }
    Write-Host ""
    Write-Host "Wgrywanie nie powiodło się. Jeśli płytka nie przeszła do bootloadera:" -ForegroundColor Yellow
    Write-Host "  1. zewrzyj dwa razy szybko RST z GND (płytka ma bootloader przez ok. 8 s)," -ForegroundColor Yellow
    Write-Host "  2. od razu uruchom ponownie: .\flash.ps1 -Board $Board" -ForegroundColor Yellow
    throw "pio run -e $envName -t upload zakończył się błędem"
}

if ($BuildOnly) {
    Write-Host "Gotowe: $PSScriptRoot\.pio\build\$envName\firmware.hex"
} else {
    Write-Host "Gotowe: firmware wgrane ($envName). Możesz uruchomić aplikację ChocPilot."
}
