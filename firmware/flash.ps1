# Buduje firmware ChocPilot i wgrywa je przez bootloader USB DFU układu STM32F072.
# Użycie (PowerShell, w katalogu firmware):
#   .\flash.ps1             – kompilacja, przełączenie płytki w DFU (komenda reboot), wgranie
#   .\flash.ps1 -BuildOnly  – tylko kompilacja (wynik: .pio\build\chocpilot\firmware.bin)
#   .\flash.ps1 -CloseApp   – najpierw zamyka aplikację ChocPilot (trzyma port COM)
# Za pierwszym razem bootloader „STM32 BOOTLOADER” (0483:DF11) potrzebuje sterownika WinUSB
# (Zadig) – patrz README.md, sekcja Firmware.
param(
    [switch]$BuildOnly,
    [switch]$CloseApp
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

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

function Test-DfuDevice {
    $dev = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match "VID_0483&PID_DF11" }
    return [bool]$dev
}

function Find-ChocPilotPort {
    $dev = Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
        Where-Object { $_.PNPDeviceID -match "VID_1209&PID_0001" -and $_.Name -match "\((COM\d+)\)" } |
        Select-Object -First 1
    if ($dev -and $dev.Name -match "\((COM\d+)\)") { return $Matches[1] }
    return $null
}

$pio = @(Find-Pio)  # @(): jednoelementowa tablica nie może się „rozwinąć” do napisu
$pioExe = $pio[0]
$pioArgs = @($pio | Select-Object -Skip 1)
Write-Host "PlatformIO: $($pio -join ' ')"

& $pioExe @($pioArgs + @("run", "-e", "chocpilot"))
if ($LASTEXITCODE -ne 0) { throw "Kompilacja nie powiodła się" }
if ($BuildOnly) {
    Write-Host "Gotowe: .pio\build\chocpilot\firmware.bin"
    exit 0
}

if (-not (Test-DfuDevice)) {
    # Aplikacja ChocPilot trzyma port COM – komenda reboot by do płytki nie dotarła.
    $app = Get-Process -Name "ChocPilot" -ErrorAction SilentlyContinue
    if ($app) {
        if ($CloseApp) {
            Write-Host "Zamykam aplikację ChocPilot..."
            $app | Stop-Process
            Start-Sleep -Seconds 1
        } else {
            throw "Aplikacja ChocPilot działa i trzyma port COM. Zamknij ją albo uruchom: .\flash.ps1 -CloseApp (albo w aplikacji: Urządzenie → Tryb wgrywania firmware)"
        }
    }
    $port = Find-ChocPilotPort
    if (-not $port) {
        throw "Nie znaleziono ChocPilot (USB 1209:0001) ani bootloadera DFU. Podłącz płytkę albo wejdź do DFU ręcznie: trzymaj BOOT0, naciśnij RESET, puść BOOT0."
    }
    Write-Host "Przełączam ChocPilot na $port w tryb DFU..."
    $serial = New-Object System.IO.Ports.SerialPort $port, 115200
    $serial.DtrEnable = $true
    $serial.Open()
    $serial.Write("{`"type`":`"reboot`",`"bootloader`":true}`n")
    Start-Sleep -Milliseconds 200
    $serial.Close()
    for ($i = 0; $i -lt 40 -and -not (Test-DfuDevice); $i++) { Start-Sleep -Milliseconds 250 }
    if (-not (Test-DfuDevice)) { throw "Płytka nie pojawiła się jako STM32 BOOTLOADER (0483:DF11)" }
}

& $pioExe @($pioArgs + @("run", "-e", "chocpilot", "-t", "upload"))
if ($LASTEXITCODE -ne 0) { throw "Wgrywanie nie powiodło się" }
Write-Host "Wgrano – płytka uruchamia nowy firmware."
