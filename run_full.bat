@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is not installed. & pause & exit /b 1)
set /p SPOTIPY_CLIENT_ID=<client_id.txt
set SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
set PYTHONUTF8=1
python -m pip install --quiet spotipy
python spotify_playlist_sorter_full.py
pause
