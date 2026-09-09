# ====================================================================
# GitBot - One-Command Autonomous Cloud Installation Script (Windows)
# ====================================================================

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host ">>> Initializing GitBot Installer..." -ForegroundColor Cyan

# 1. Check Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "[!] Python 3 is required to run the automated setup." -ForegroundColor Red
    Write-Host "[!] Please install Python from https://www.python.org/downloads/ or Microsoft Store." -ForegroundColor Yellow
    exit 1
}

# 2. Check Git installation
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Host "[!] Git is required to clone and operate GitBot." -ForegroundColor Red
    Write-Host "[!] Please install Git from https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# 3. Setup ~/.gitbot directory
$gitbotHome = Join-Path $env:USERPROFILE ".gitbot"
$binDir = Join-Path $gitbotHome "bin"

Write-Host ">>> Installing GitBot into $gitbotHome..." -ForegroundColor Green

if (Test-Path $gitbotHome) {
    Write-Host ">>> Updating existing GitBot installation in-place..." -ForegroundColor Cyan
    git -C $gitbotHome remote add upstream https://github.com/Dashrath175/GitBot.git 2>$null
    $dirty = git -C $gitbotHome status --porcelain
    if ($dirty) {
        Write-Host "[!] Existing installation has local changes; preserving them. Commit, stash, or resolve them before updating." -ForegroundColor Yellow
        exit 1
    }
    git -C $gitbotHome fetch upstream main
    if ($LASTEXITCODE -ne 0) { exit 1 }
    git -C $gitbotHome merge --ff-only upstream/main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Update cannot fast-forward safely; no files were overwritten." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host ">>> Cloning GitBot repository..." -ForegroundColor Cyan
    git clone https://github.com/Dashrath175/GitBot.git $gitbotHome
}

# 4. Create global command wrappers in ~/.gitbot/bin
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

$cmdWrapper = Join-Path $binDir "gitbot.cmd"
$cmdContent = "@echo off`r`npython `"%~dp0\..\cli.py`" %*"
[System.IO.File]::WriteAllText($cmdWrapper, $cmdContent)

$ps1Wrapper = Join-Path $binDir "gitbot.ps1"
$ps1Content = "& python `"`$PSScriptRoot\..\cli.py`" `$args"
[System.IO.File]::WriteAllText($ps1Wrapper, $ps1Content)

# 5. Add ~/.gitbot/bin to User PATH if not already present
$userPath = [Environment]::GetEnvironmentVariable("PATH", [EnvironmentVariableTarget]::User)
if ($userPath -notlike "*$binDir*") {
    Write-Host ">>> Adding gitbot to User PATH..." -ForegroundColor Cyan
    $newPath = "$userPath;$binDir"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, [EnvironmentVariableTarget]::User)
    $env:PATH = "$env:PATH;$binDir"
}

# 6. Run onboarding installer wizard
Write-Host ">>> Running GitBot setup wizard..." -ForegroundColor Green
$installerScript = Join-Path $gitbotHome "installer.py"
& $pythonCmd.Source $installerScript

Write-Host "`n>>> Installation Complete! You can now type 'gitbot' from any terminal.`n" -ForegroundColor Green
