@echo off
setlocal

cd /d "%~dp0"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name PNG_Logo_Auto_Generator ^
  --icon "assets\app_icon.ico" ^
  --add-data "assets\app_icon.png;assets" ^
  --add-data "assets\app_icon.ico;assets" ^
  --add-data "assets\logoplanet_mark.png;assets" ^
  --add-data "assets\logoplanet_mark_soft.png;assets" ^
  main.py

echo.
echo Build finished.
echo EXE path: %~dp0dist\PNG_Logo_Auto_Generator.exe
pause
