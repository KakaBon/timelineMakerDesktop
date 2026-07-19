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
  --icon=assets/images/icon.ico ^
  --add-data "assets/data/samples/test-data.csv;assets/data/samples" ^
  --add-data "assets/images/icon.ico;assets/images" ^
  --name "timelineMakerDesktop" ^
  app.py

pause