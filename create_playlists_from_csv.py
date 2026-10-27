"""
Create private "Genre: <name>" playlists from song_genres.csv and add the songs.

Safe: never edits or deletes anything you already have.  Songs it adds are recorded in
created_state.json, so re-running adds only songs that were not added before.

  --dry               preview the playlists without creating anything
  --include-unsorted  also create a "Genre: Unsorted" playlist
  --overrides FILE    CSV with columns artist,bucket (default: manual_overrides.csv if present).
                      Songs whose FIRST artist matches get that bucket instead of the one in
                      song_genres.csv.  Use it to hand-sort songs that ended up Unsorted.
"""
import csv, json, os, sys
import spotipy
from spotipy.oauth2 import SpotifyPKCE

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

args = sys.argv[1:]
dry = "--dry" in args
include_unsorted = "--include-unsorted" in args
ov_path = "manual_overrides.csv"
if "--overrides" in args:
    ov_path = args[args.index("--overrides") + 1]

overrides = {}
if os.path.exists(ov_path):
    for r in csv.DictReader(open(ov_path, encoding="utf-8-sig")):
        if r.get("artist") and r.get("bucket"):
            overrides[r["artist"].strip().lower()] = r["bucket"].strip()
    print(f"Loaded {len(overrides)} manual overrides from {ov_path}")

state_path = "created_state.json"
state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}

rows = list(csv.DictReader(open("song_genres.csv", encoding="utf-8")))
plan = {}
for r in rows:
    if not r["uri"]:
        continue
    first = r["artists"].split(",")[0].strip().lower()
    bucket = overrides.get(first, r["bucket"])
    if bucket == "Unsorted" and not include_unsorted:
        continue
    done = set(state.get("Genre: " + bucket, []))
    if r["uri"] in done:
        continue
    plan.setdefault(bucket, []).append(r["uri"])
for b, u in sorted(plan.items(), key=lambda kv: -len(kv[1])):
    print(f"{len(u):5d}  Genre: {b}")
if not plan:
    print("Nothing new to add.")
if dry or not plan:
    print("\nDry run only - nothing created." if dry else "")
    sys.exit()

sp = spotipy.Spotify(auth_manager=SpotifyPKCE(
    scope="playlist-modify-private playlist-read-private"), requests_timeout=30, retries=5)
me = sp.current_user()["id"]
existing = {}
page = sp.current_user_playlists(limit=50)
while page:
    for p in page["items"]:
        if p["owner"]["id"] == me: existing[p["name"]] = p["id"]
    page = sp.next(page) if page.get("next") else None

for b, uris in plan.items():
    name = "Genre: " + b
    # Spotify retired POST /users/{id}/playlists for new apps; /me/playlists works.
    pid = existing.get(name) or sp._post("me/playlists", payload={
        "name": name, "public": False, "description": "Sorted by genre"})["id"]
    for i in range(0, len(uris), 100):
        chunk = uris[i:i+100]
        try:
            sp.playlist_add_items(pid, chunk)
        except Exception:
            sp._post(f"playlists/{pid}/items", payload={"uris": chunk})
        state.setdefault(name, []).extend(chunk)
        json.dump(state, open(state_path, "w", encoding="utf-8"))
    print(f"  {name}: added {len(uris)}")
print("Done.")
