@echo off
title Wisper — Speech-to-Text

if not exist venv (
    echo Virtual environment not found. Run setup.py first:
    echo   python setup.py
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt
python src/main.py
