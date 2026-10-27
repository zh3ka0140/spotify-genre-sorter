"""
Sort every song in your Spotify playlists (and optionally Liked Songs) into a
fixed set of private "Genre: ..." playlists. Each song goes into exactly one.

Safe by design:
  * Default run is a DRY RUN: it only writes preview CSVs, changes nothing.
  * It never edits, removes or deletes anything you already have.
  * New playlists are private and named "Genre: <name>".

Usage:
  pip install spotipy
  set SPOTIPY_CLIENT_ID=...        (Windows cmd; use `export` on Mac/Linux)

  set SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
  python sort_by_genre.py                 # dry run, writes preview files
  python sort_by_genre.py --include-liked # also read Liked Songs (read-only)
  python sort_by_genre.py --apply         # actually create the playlists
"""
import argparse, csv, re, sys, time
import spotipy
from spotipy.oauth2 import SpotifyPKCE

# Order matters: the first bucket whose keywords match an artist's genres wins.
BUCKETS = [
    ("Melodic House & Techno", ["melodic house", "melodic techno", "progressive house", "organic house", "deep techno"]),
    ("Techno & Acid",          ["techno", "acid", "hard techno", "industrial"]),
    ("Trance",                 ["trance", "psytrance", "goa"]),
    ("Dubstep & Bass",         ["dubstep", "brostep", "riddim", "drum and bass", "dnb", "bass music", "trap edm", "future bass", "bass house"]),
    ("Afro, Latin & Bossa",    ["afro", "amapiano", "bossa nova", "samba", "brazilian", "mpb", "latin", "reggaeton", "salsa", "cumbia"]),
    ("Russian & Vintage",      ["russian", "soviet", "ukrainian", "belarusian", "estrada"]),
    ("House",                  ["house", "tech house", "electro house", "edm", "electro", "big room", "future house"]),
    ("Dance, Disco & Pop",     ["disco", "eurodance", "europop", "dance pop", "hi-nrg", "synthpop", "italo", "pop dance", "dance"]),
    ("Chill & Ambient",        ["ambient", "chill", "downtempo", "new age", "lo-fi", "lofi", "meditation", "sleep", "trip hop", "lounge"]),
    ("Hip-Hop & R&B",          ["hip hop", "rap", "r&b", "trap"]),
    ("Rock & Alt",             ["rock", "alternative", "indie", "punk", "metal", "grunge", "emo", "shoegaze"]),
    ("Pop",                    ["pop"]),
]
UNSORTED = "Unsorted"
PREFIX = "Genre: "

def classify(genres):
    text = " | ".join(g.lower() for g in genres)
    for name, keys in BUCKETS:
        for k in keys:
            if re.search(r"\b" + re.escape(k), text):
                return name
    return UNSORTED


GENERIC = {"pop", "rock", "dance", "electronic", "edm", "house", "techno", "hip hop", "rap",
           "indie", "alternative", "metal", "electro", "r&b", "latin", "folk", "classical"}

def niche_pick(genres, counts):
    """Pick ONE genre for a song: the most specific one its artists carry.
    Specific = not a generic one-word genre, more words, and rarer in your library."""
    if not genres:
        return None
    def score(g):
        return (0 if g in GENERIC else 1, len(g.split()), -counts.get(g, 0), g)
    return max(set(genres), key=score)

def roll_up(genre, parent_counts):
    """Broader home for a genre too small to deserve its own playlist."""
    if genre is None:
        return UNSORTED
    parent = classify([genre])
    return parent

def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]

def paged(sp, first):
    page = first
    while page:
        for it in page["items"]:
            yield it
        page = sp.next(page) if page.get("next") else None

def main():
    for stream in (sys.stdout, sys.stderr):
        try: stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="create playlists and add songs")
    ap.add_argument("--include-liked", action="store_true", help="also read Liked Songs (read-only)")
    ap.add_argument("--min-songs", type=int, default=8,
                    help="a niche genre needs this many songs to get its own playlist; "
                         "smaller ones roll up into a broader parent genre (default 8)")
    args = ap.parse_args()

    scope = "playlist-read-private playlist-read-collaborative user-library-read playlist-modify-private"
    sp = spotipy.Spotify(auth_manager=SpotifyPKCE(scope=scope), requests_timeout=30, retries=5)
    me = sp.current_user()["id"]

    tracks = {}          # uri -> dict(name, artists, artist_ids, sources)
    skipped = []         # playlists we could not read
    def add(item, source):
        t = item.get("track") if "track" in item else item
        if not t or not t.get("uri") or t.get("is_local") or t.get("type") != "track":
            return
        d = tracks.setdefault(t["uri"], {
            "name": t["name"],
            "artists": ", ".join(a["name"] for a in t["artists"]),
            "artist_ids": [a["id"] for a in t["artists"] if a.get("id")],
            "sources": [],
        })
        d["sources"].append(source)

    print("Reading your playlists...")
    for pl in paged(sp, sp.current_user_playlists(limit=50)):
        if pl["name"].startswith(PREFIX):
            continue                      # don't read our own output
        try:
            for it in paged(sp, sp.playlist_items(pl["id"], limit=100, additional_types=("track",))):
                add(it, pl["name"])
            print(f"  ok       {pl['name']}")
        except Exception as e:
            skipped.append((pl["name"], getattr(e, "http_status", "error")))
            print(f"  SKIPPED  {pl['name']} ({getattr(e, 'http_status', 'error')})")

    if args.include_liked:
        print("Reading Liked Songs (read-only)...")
        for it in paged(sp, sp.current_user_saved_tracks(limit=50)):
            add(it, "Liked Songs")

    print(f"{len(tracks)} unique songs found.")

    # Look up genres for every artist (Spotify stores genres on artists).
    artist_ids = sorted({a for d in tracks.values() for a in d["artist_ids"]})
    genres = {}
    for batch in chunks(artist_ids, 50):
        try:
            for a in sp.artists(batch)["artists"]:
                if a:
                    genres[a["id"]] = a.get("genres") or []
        except spotipy.SpotifyException as e:
            print(f"  artist lookup failed (HTTP {e.http_status}); those songs go to {UNSORTED}")
        time.sleep(0.1)

    # Count how common each micro-genre is across the library.
    counts = {}
    for d in tracks.values():
        for a in set(d["artist_ids"]):
            for g in genres.get(a, []):
                counts[g] = counts.get(g, 0) + 1

    # Pass 1: every song gets its single most specific genre.
    for uri, d in tracks.items():
        g = [x for a in d["artist_ids"] for x in genres.get(a, [])]
        d["all_genres"] = "; ".join(sorted(set(g)))
        d["niche"] = niche_pick(g, counts)

    # Pass 2: genres with too few songs roll up into a broader parent.
    size = {}
    for d in tracks.values():
        size[d["niche"]] = size.get(d["niche"], 0) + 1
    plan = {}
    for uri, d in tracks.items():
        n = d["niche"]
        if n is None:
            bucket = UNSORTED
        elif size[n] >= args.min_songs:
            bucket = n.title()
        else:
            bucket = roll_up(n, size)
        d["bucket"] = bucket
        d["genres"] = d["all_genres"]
        plan.setdefault(bucket, []).append(uri)

    with open("preview_songs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bucket", "song", "artists", "spotify_genres", "found_in", "uri"])
        for uri, d in sorted(tracks.items(), key=lambda kv: (kv[1]["bucket"], kv[1]["artists"])):
            w.writerow([d["bucket"], d["name"], d["artists"], d["genres"], " | ".join(sorted(set(d["sources"]))), uri])
    with open("preview_summary.txt", "w", encoding="utf-8") as f:
        for b, uris in sorted(plan.items(), key=lambda kv: -len(kv[1])):
            f.write(f"{len(uris):6d}  {PREFIX}{b}\n")
        if skipped:
            f.write("\nPlaylists Spotify would not let this script read:\n")
            for n, s in skipped:
                f.write(f"  {n} (HTTP {s})\n")
    print(open("preview_summary.txt", encoding="utf-8").read())

    if not args.apply:
        print("Dry run only. Review preview_songs.csv, then re-run with --apply.")
        return

    existing = {p["name"]: p["id"] for p in paged(sp, sp.current_user_playlists(limit=50)) if p["owner"]["id"] == me}
    for b, uris in plan.items():
        name = PREFIX + b
        if name in existing:
            pid = existing[name]
        else:
            pid = sp.user_playlist_create(me, name, public=False, description="Sorted by genre by script")["id"]
        for batch in chunks(uris, 100):
            sp.playlist_add_items(pid, batch)
        print(f"  {name}: added {len(uris)}")
    print("Done. Nothing you already had was changed.")

if __name__ == "__main__":
    main()
