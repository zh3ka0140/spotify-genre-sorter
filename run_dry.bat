@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is not installed. Install it from python.org, tick "Add to PATH", then run this again. & pause & exit /b 1)
if not exist client_id.txt (echo Missing client_id.txt - put your Spotify Client ID in it. & pause & exit /b 1)
set /p SPOTIPY_CLIENT_ID=<client_id.txt
set PYTHONUTF8=1
set SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
python -m pip install --quiet spotipy
echo.
echo DRY RUN - this only reads your library and writes preview files. Nothing is changed.
python sort_by_genre.py --include-liked > run_log.txt 2>&1
type run_log.txt
echo.
echo Finished. Preview files are in this folder. You can close this window.
pause
