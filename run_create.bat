@echo off
cd /d "%~dp0"
set /p SPOTIPY_CLIENT_ID=<client_id.txt
set SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
set PYTHONUTF8=1
python -m pip install --quiet spotipy
echo Step 1 of 2: PREVIEW of the playlists that would be created (nothing is changed yet).
python create_playlists_from_csv.py --dry
echo.
set /p GO=Type YES to create these private playlists in Spotify, anything else to cancel: 
if /i not "%GO%"=="YES" (echo Cancelled. & pause & exit /b 0)
python create_playlists_from_csv.py > create_log.txt 2>&1
type create_log.txt
pause
