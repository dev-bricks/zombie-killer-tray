@echo off
setlocal EnableExtensions

set "TRAY_SCRIPT=%~dp0zombie_tray.ps1"

if /I "%~1"=="--check" goto :check

if not exist "%TRAY_SCRIPT%" (
  echo FEHLER: zombie_tray.ps1 fehlt neben dieser BAT-Datei.
  echo Erwartet: "%TRAY_SCRIPT%"
  exit /b 2
)

echo Windows fragt jetzt nach Administratorrechten.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process -FilePath 'powershell.exe' -Verb RunAs -WindowStyle Hidden -ArgumentList @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','%TRAY_SCRIPT%')"

if errorlevel 1 (
  echo Der Administratorstart wurde abgebrochen oder ist fehlgeschlagen.
  exit /b 1
)

echo Zombie-Killer-Tray wurde zum Administratorstart uebergeben.
exit /b 0

:check
if not exist "%TRAY_SCRIPT%" (
  echo FEHLER: "%TRAY_SCRIPT%" fehlt.
  exit /b 2
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile('%TRAY_SCRIPT%',[ref]$tokens,[ref]$errors) | Out-Null; if($errors.Count){$errors | ForEach-Object { Write-Error $_ }; exit 1}; Write-Output 'Start-BAT und Tray-Skript sind vorhanden und parsebar.'"
exit /b %errorlevel%
