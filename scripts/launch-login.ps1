#!/usr/bin/env powershell
<#
.SYNOPSIS
    Launch Chrome with the same profile and settings as the automation system for manual login.

.DESCRIPTION
    This script launches Chrome using the exact same profile directory and browser arguments
    that the automation system uses. Use this to manually login to any website
    and maintain authentication for the automation.

.PARAMETER URL
    The website URL to open for login. If not specified, Chrome opens to a blank page.

.EXAMPLE
    .\launch-login.ps1 -URL "https://www.peeks.com"
    
    Launches Chrome with automation profile for manual login to peeks.com.

.EXAMPLE
    .\launch-login.ps1 -URL "https://www.instagram.com"
    
    Launches Chrome with automation profile for manual login to Instagram.
#>

param(
    [string]$URL = ""
)

# Get the project root (parent of scripts folder)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$ProfilePath = Join-Path $ProjectRoot "automation_profile_chrome"

# Check and activate virtual environment using the project's launch script
$LaunchScript = Join-Path $ProjectRoot "launch.ps1"

if ((Test-Path $LaunchScript) -and (-not $env:VIRTUAL_ENV)) {
    Write-Host "Python: Activating virtual environment using launch.ps1..." -ForegroundColor Cyan
    try {
        Push-Location $ProjectRoot
        & $LaunchScript
        Pop-Location
        Write-Host "Virtual environment activated" -ForegroundColor Green
    }
    catch {
        Pop-Location
        Write-Host "Warning: Could not activate virtual environment: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "Continuing without virtual environment..." -ForegroundColor Gray
    }
}
elseif ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment already active: $env:VIRTUAL_ENV" -ForegroundColor Green
}

# Chrome executable paths (try common locations)
$ChromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
)

# Find Chrome executable
$ChromeExe = $null
foreach ($Path in $ChromePaths) {
    if (Test-Path $Path) {
        $ChromeExe = $Path
        break
    }
}

if (-not $ChromeExe) {
    Write-Host "Chrome executable not found in common locations:" -ForegroundColor Red
    foreach ($Path in $ChromePaths) {
        Write-Host "   - $Path" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Please install Chrome or update the script with the correct path." -ForegroundColor Yellow
    exit 1
}

# Browser arguments (matching automation config)
$BrowserArgs = @(
    "--user-data-dir=`"$ProfilePath`"",
    "--remote-debugging-port=9222",
    "--no-first-run",
    "--disable-dev-shm-usage", 
    "--disable-gpu",
    "--no-default-browser-check",
    "--no-first-run-ui",
    "--disable-default-apps",
    "--disable-popup-blocking"
)

Write-Host "Chrome: Launching Chrome for manual website authentication..." -ForegroundColor Green
Write-Host "Profile: $ProfilePath" -ForegroundColor Cyan
if ($URL) {
    Write-Host "Opening: $URL" -ForegroundColor Yellow
} else {
    Write-Host "Opening: Chrome start page (navigate to your desired site)" -ForegroundColor Yellow
}
Write-Host ""

# Create profile directory if it doesn't exist
if (-not (Test-Path $ProfilePath)) {
    New-Item -ItemType Directory -Path $ProfilePath -Force | Out-Null
    Write-Host "Created profile directory: $ProfilePath" -ForegroundColor Green
}

try {
    # Launch Chrome
    if ($URL) {
        & $ChromeExe $BrowserArgs $URL
    } else {
        & $ChromeExe $BrowserArgs
    }
    Write-Host "Chrome launched successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Instructions:" -ForegroundColor White
    Write-Host "1. Navigate to your target website (if not already there)" -ForegroundColor White
    Write-Host "2. Login and complete any required verification" -ForegroundColor White  
    Write-Host "3. Close the browser when done" -ForegroundColor White
    Write-Host "4. Your login session will be saved for automation" -ForegroundColor White
    Write-Host ""
    Write-Host "After login, run your automation scripts to use the saved session." -ForegroundColor Cyan
}
catch {
    Write-Host "Failed to launch Chrome: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}