param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pythonExe = $null
$pythonPrefixArgs = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonExe = "py"
    $pythonPrefixArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
    $pythonPrefixArgs = @()
} else {
    throw "Python nebyl nalezen v PATH."
}

if (-not $SkipInstall) {
    & $pythonExe @pythonPrefixArgs -m pip install --upgrade pip
    & $pythonExe @pythonPrefixArgs -m pip install -r requirements.txt
}

$iconPath = Join-Path $root "app\assets\icon.ico"
$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "Pripominacek",
    "--add-data", "app\assets\icon.png;app\assets"
)

if (Test-Path $iconPath) {
    $pyInstallerArgs += @("--icon", $iconPath)
}

$pyInstallerArgs += "app\main.py"

& $pythonExe @pythonPrefixArgs -m PyInstaller @pyInstallerArgs

Write-Host "Build hotov. Spustitelny soubor najdes v dist\Pripominacek.exe"
