<#
Enable Developer Mode (sets registry key AllowDevelopmentWithoutDevLicense=1).
This script MUST be run in an elevated (Administrator) PowerShell session.
It prints the current value, prompts before changing, and then sets the DWORD to 1.
#>

$RegPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock'

if (-not (Test-Path $RegPath)) {
    try {
        New-Item -Path $RegPath -Force | Out-Null
    } catch {
        Write-Error "Failed to create registry path $RegPath. Run PowerShell as Administrator."
        exit 1
    }
}

$existing = Get-ItemProperty -Path $RegPath -Name 'AllowDevelopmentWithoutDevLicense' -ErrorAction SilentlyContinue
Write-Host "Current AllowDevelopmentWithoutDevLicense value:`t" ($existing.AllowDevelopmentWithoutDevLicense -as [string]) -ForegroundColor Cyan

$confirm = Read-Host "This will set the registry value to 1 (enable Developer Mode). Type 'YES' to proceed"
if ($confirm -ne 'YES') {
    Write-Host "Aborted by user." -ForegroundColor Yellow
    exit 0
}

try {
    New-ItemProperty -Path $RegPath -Name 'AllowDevelopmentWithoutDevLicense' -PropertyType DWORD -Value 1 -Force | Out-Null
    Write-Host "Registry updated successfully. Open Settings → Developer to confirm Developer Mode is enabled." -ForegroundColor Green
    Write-Host "Restart your terminal / VS Code and run `flutter clean; flutter pub get` before building again." -ForegroundColor Green
} catch {
    Write-Error "Failed to write registry. Ensure you're running PowerShell as Administrator."
    exit 1
}
