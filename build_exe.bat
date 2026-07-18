@echo off
chcp 65001 >nul
cd /d "%~dp0"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --exclude-module numpy ^
  --version-file version_info.txt ^
  --icon=icon.ico ^
  --add-data "test-data.csv;." ^
  --add-data "icon.ico;." ^
  --name "timelineMakerDesktop" ^
  app.py

pause