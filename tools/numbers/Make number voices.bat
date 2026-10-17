@echo off
title Maths games voices
cd /d "%~dp0"
echo Making the maths games' voice with Gemini. It takes about 5 minutes. Leave this window open.
echo.
py number_voices.py
echo.
if exist "listen.html" start "" "listen.html"
pause
