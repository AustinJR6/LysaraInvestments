@echo off
cd /d "%~dp0"
echo Activating virtual environment...
call lysara-env\Scripts\activate.bat

echo Launching Lysara Investments bot...
python launcher.py %*

pause
