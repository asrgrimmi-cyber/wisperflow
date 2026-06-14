@echo off
REM Development launcher for Speech-to-Text Dictation Tool

echo Creating/activating virtual environment...
if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

echo Starting Speech-to-Text Dictation Tool...
python src/main.py

pause
