@echo off
title DWG-PARSER BACKEND

echo Starting DWG-PARSER backend...

cd /d "%~dp0backend"

call ..\venv\Scripts\activate

uvicorn main:app --host 127.0.0.1 --port 8000 --reload
