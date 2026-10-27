@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is not installed. & pause & exit /b 1)
set PYTHONUTF8=1
echo Looking up artist genres on MusicBrainz. This takes about 25 minutes and can be stopped and resumed.
python lookup_genres.py > lookup_log.txt 2>&1
type lookup_log.txt
pause
