# Spotify Genre Sorter

Sorts your Liked Songs into private "Genre: ..." playlists, one niche genre per song
(acid house, melodic house, new wave...), so each playlist holds only that genre.
It never edits or deletes anything you already have. Everything runs on your PC.

Two scripts: run_create.bat (sort_by_genre.py) sorts your Liked Songs only (steps below). spotify_playlist_sorter_full.py (run_full.bat) sorts Liked Songs AND every playlist you have: your own, ones saved from other people, and Spotify-made mixes (see "Full version" further down).

## What it can and cannot do (Spotify limits, checked October 2026)
- CAN read your Liked Songs and create new private playlists.
- CANNOT read the songs inside playlists through Spotify's API (returns nothing or 403),
  and cannot read artist genres from Spotify. So genres come from MusicBrainz instead.
  The full version works around the playlist limit by reading playlist contents from the Spotify web player with scrape_playlists.js.
- Playlists made by other people or by Spotify are blocked from the API entirely.
  Copy those by hand in the Spotify web player: open the playlist, click the first
  song, hold Shift and press Down to select all, then drag the selection onto
  your genre playlist in the left sidebar.
- Genres are per ARTIST, not per song, so some songs will land in the wrong genre.
  Check song_genres.csv and fix it before creating playlists.

## One-time setup
1. Install Python from python.org (tick "Add python.exe to PATH").
2. Go to developer.spotify.com/dashboard, Create app, any name, and add this
   Redirect URI exactly:  http://127.0.0.1:8888/callback
3. Copy client_id.txt.example to client_id.txt and put your app's Client ID on the first line.
   (The Client ID is public. No secret is needed or used.)

## Every time (double-click in this order)
1. run_dry.bat      Reads your Liked Songs (read-only) and writes preview_songs.csv.
                    The first time, a browser tab opens: click Agree.
2. run_lookup.bat   Looks up each artist's genre on MusicBrainz and writes
                    song_genres.csv and genre_summary.txt. Allow roughly an hour for
                    about 900 artists (MusicBrainz answers about one request every 3-4
                    seconds). Safe to close and re-run: it resumes from artist_genres.json.
3. Open song_genres.csv in Excel. Column "bucket" is the playlist each song goes to.
   Edit buckets you disagree with. Anything "Unsorted" is skipped by default.
4. (Optional) Hand-sort the Unsorted songs, see "Sorting leftovers by hand" below.
5. run_create.bat   Shows a preview, then asks you to type YES before creating
                    private "Genre: ..." playlists.

Re-running run_create.bat is safe: songs it already added are remembered in
created_state.json and are skipped, so you can fix more buckets later and run it again
to add only the new songs. Delete a "Genre: ..." playlist in Spotify and you should also
delete its entry in created_state.json (or the whole file) before re-running.

## Sorting leftovers by hand
Songs whose artist has no usable genre tag on MusicBrainz end up "Unsorted", and so do
genres with fewer than MIN_SONGS songs. To place them yourself:
1. Open genre_summary.txt / song_genres.csv and look at the Unsorted rows.
2. Copy manual_overrides.csv.example to manual_overrides.csv and list one artist per line
   with the playlist name you want, for example:

       artist,bucket
       Hardfloor,Acid House
       Kino,Russian Rock

   The match is on the FIRST artist of a song (case-insensitive). An override wins over
   the bucket in song_genres.csv, so you can also use it to correct wrong genres.
3. Run run_create.bat (or `python create_playlists_from_csv.py --dry` to preview).
   New genre names create new playlists automatically.

## Full version: Liked Songs AND every playlist (spotify_playlist_sorter_full.py)
The first script only sees Liked Songs. The full version also sorts your own playlists,
playlists you saved from other people, and Spotify-made mixes and radios.
Spotify's API will not hand over the songs inside playlists, so playlist contents come
from a file instead:
1. Open https://open.spotify.com in Chrome or Edge and sign in.
2. Press F12, open the Console tab (if asked, type: allow pasting), paste the whole of
   scrape_playlists.js and press Enter. Leave the tab in front. It opens each playlist in
   your library and reads the song list (read-only). About 10-30 minutes for a big library.
3. When the console says DONE, playlists_scraped.json is in your Downloads folder. Move it
   into this folder. (Your own playlists can instead come from Spotify's "Download your
   data" export: put Playlist1.json here and it is picked up automatically.)
4. Double-click run_full.bat. It reads Liked Songs through the API, merges every playlist
   (each song once, however many playlists it is in), looks up genres, shows a preview and
   asks you to type YES before creating the private "Genre: ..." playlists.
Running it again later only adds songs it has not placed before (created_state.json).
Hand-sorting leftovers with manual_overrides.csv works the same way as above.
Good to know: copied playlists are by song, not by playlist, so a song that appears in
three playlists ends up in just one genre playlist. Playlists named "Genre: ..." are skipped.

## Command line options (create_playlists_from_csv.py)
- --dry                preview only, create nothing
- --include-unsorted   also make a "Genre: Unsorted" playlist
- --overrides FILE     use a different overrides file (default: manual_overrides.csv)

## Tuning
- Minimum songs per genre playlist: MIN_SONGS near the top of lookup_genres.py
  (default 8). Smaller genres go to Unsorted. Lower it for more niche playlists.
- Add genre names to the GENRES list in lookup_genres.py to recognise more of them.

## Troubleshooting
- "Python is not installed": do setup step 1, then re-run.
- HTTP 403 when reading playlists or artists: Spotify blocks that item. It is skipped,
  nothing is damaged.
- HTTP 403 when creating a playlist: older versions used an endpoint Spotify no longer
  allows for new apps. This version creates playlists through /me/playlists. Update if
  you still see it.
- Playlists show as public: Spotify's /me/playlists endpoint can ignore the private flag.
  This version sets each playlist private right after creating it. If you made playlists
  with an older version, run make_private.py once (it sets every "Genre: ..." playlist
  you own to private).
- Login page error "INVALID_CLIENT": the Client ID is wrong, or the Redirect URI in
  the dashboard does not match exactly.
- Remove the app's access to your account any time: spotify.com/account/apps
- Delete the .cache file to force a fresh Spotify login.
- Logs: run_log.txt, lookup_log.txt, create_log.txt.

## Optional
- contact.txt: put an email or URL on one line to identify yourself to MusicBrainz
  (their API etiquette). If absent, a generic name is sent. Never committed to git.

## Privacy
This repo contains no personal data. Your Client ID, login cache, song lists, overrides
and results stay on your PC and are listed in .gitignore.

## Disclaimer
Unofficial hobby tool, not affiliated with Spotify or MusicBrainz. Use at your own risk.
Genres come from community tags on MusicBrainz and will not always be right.
