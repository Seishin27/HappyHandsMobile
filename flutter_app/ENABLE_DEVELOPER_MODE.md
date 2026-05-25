Enable Developer Mode for Flutter desktop builds (Windows)

Why
- Flutter creates symlinks for native plugins under `windows/flutter/ephemeral/.plugin_symlinks/`.
- Creating symlinks on Windows requires Developer Mode or administrator rights. If not enabled, `flutter run -d windows` fails with: "Building with plugins requires symlink support..."

Options
1) Recommended: Enable Developer Mode (non-admin users can create symlinks)
   - Open Settings → Developer settings → Turn on "Developer Mode"
   - Or run (as Admin) the registry command below.

2) Quick admin workaround: Run an elevated PowerShell or VS Code as Administrator before running `flutter run`.

3) Advanced (not recommended): Manually copy plugin `windows` folders into `windows/flutter/ephemeral/.plugin_symlinks/` (fragile).

Registry one-liner (requires Administrator PowerShell)

```powershell
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /v "AllowDevelopmentWithoutDevLicense" /t REG_DWORD /d 1 /f
```

Safe script (included)
- `enable_developer_mode.ps1` — prompts and sets the registry value. Run it only in an elevated PowerShell session.

How to run the script (recommended)
1. Open PowerShell as Administrator (right-click → Run as administrator).
2. Change directory to this folder:

```powershell
cd "C:\Users\Mae\Downloads\Copy-Ecom\Copy-Ecom\Happy Hands SUPER FINAL\flutter_app"
```

3. Run the script (allow it to prompt):

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; .\enable_developer_mode.ps1
```

After enabling
- Close and reopen your terminal / VS Code.
- From the `flutter_app` folder run:

```powershell
flutter clean
flutter pub get
flutter run -d windows
```

If you want, I can run the registry change here — but I will only do so with your explicit permission.
