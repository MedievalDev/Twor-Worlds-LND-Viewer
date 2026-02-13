@echo off
cd /d "%~dp0"
pip show Pillow >nul 2>&1 || pip install Pillow
pip show numpy >nul 2>&1 || pip install numpy
python tw1_world_viewer.py
pause
