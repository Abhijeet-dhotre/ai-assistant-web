@echo off
title AI Voice Assistant

echo ========================================
echo   AI Voice Assistant
echo   Whisper + Groq + Pocket TTS
echo ========================================
echo.

REM --- Install Python dependencies ---
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt --quiet 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo       Done.
echo.

REM --- Start Pocket TTS in a new window ---
echo [2/4] Starting Pocket TTS server on port 8000...
start "Pocket TTS" cmd /k "uvx pocket-tts serve --voice alba"

REM --- Wait for Pocket TTS to load model ---
echo       Waiting for Pocket TTS to load (30s)...
timeout /t 30 /nobreak >nul

REM --- Start WebSocket server in a new window ---
echo [3/4] Starting WebSocket server on port 5051...
start "WS Server" cmd /k "python ws_server.py"

REM --- Start Flask backend in a new window ---
echo [4/4] Starting Flask server on port 5050...
start "Flask Server" cmd /k "python server.py"

echo.
echo ========================================
echo   Open http://localhost:5050
echo ========================================
echo.

REM --- Open browser after 5 seconds ---
timeout /t 5 /nobreak >nul
start http://localhost:5050
