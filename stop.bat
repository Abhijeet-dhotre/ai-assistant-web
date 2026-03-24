@echo off
echo Stopping AI Voice Assistant...
taskkill /FI "WINDOWTITLE eq Pocket TTS" /F 2>nul
taskkill /FI "WINDOWTITLE eq WS Server" /F 2>nul
taskkill /FI "WINDOWTITLE eq Flask Server" /F 2>nul
taskkill /FI "WINDOWTITLE eq AI Voice Assistant" /F 2>nul
echo Done.
timeout /t 2 /nobreak >nul
