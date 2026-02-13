@echo off
cd /d "%~dp0"
echo Checking dependencies...
pip show Pillow >nul 2>&1 || (
    echo Installing Pillow...
    pip install Pillow
)
pip show numpy >nul 2>&1 || (
    echo Installing numpy...
    pip install numpy
)
python tw1_lnd_tool.py
pause
