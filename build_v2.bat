@echo off
setlocal

cd /d "%~dp0"

python -m PyInstaller --noconfirm ".\PNG_Logo_Auto_Generator_V2.spec"

echo.
echo Build finished.
echo EXE path: %~dp0dist\PNG_Logo_Auto_Generator_V2\PNG_Logo_Auto_Generator_V2.exe
pause
