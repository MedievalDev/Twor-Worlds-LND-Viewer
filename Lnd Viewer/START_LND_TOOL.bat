@echo off
title TW1 LND Tool
cd /d "%~dp0"

set "PYTHON="
where py >nul 2>&1 && (set "PYTHON=py -3" & goto :found)
where python >nul 2>&1 && (set "PYTHON=python" & goto :found)
where python3 >nul 2>&1 && (set "PYTHON=python3" & goto :found)
for %%V in (313 312 311 310 39 38) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto :found
    )
)
for %%V in (313 312 311 310 39 38) do (
    if exist "C:\Python%%V\python.exe" (
        set "PYTHON=C:\Python%%V\python.exe" & goto :found
    )
    if exist "%ProgramFiles%\Python%%V\python.exe" (
        set "PYTHON=%ProgramFiles%\Python%%V\python.exe" & goto :found
    )
)
echo.
echo  Python nicht gefunden!
echo  Bitte Python 3.8+ installieren: https://www.python.org/downloads/
echo  WICHTIG: Bei der Installation "Add Python to PATH" ankreuzen!
echo.
pause
exit /b

:found
echo Pruefe Abhaengigkeiten...
%PYTHON% -c "from PIL import Image" >nul 2>&1 || (
    echo Installiere Pillow...
    %PYTHON% -m pip install Pillow
)
%PYTHON% -c "import numpy" >nul 2>&1 || (
    echo Installiere numpy...
    %PYTHON% -m pip install numpy
)
%PYTHON% "%~dp0tw1_lnd_tool.py"
if errorlevel 1 pause
