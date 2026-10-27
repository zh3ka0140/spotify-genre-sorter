"""
Look up a genre for every artist in preview_songs.csv using MusicBrainz (free, no key).
Resumable: results are cached in artist_genres.json, so you can stop and re-run.
Writes: song_genres.csv (one niche genre per song) and genre_summary.txt.
Read-only with respect to Spotify. Takes ~25 minutes for ~1400 artists (1 request/sec limit).
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

CACHE = "artist_genres.json"
def _contact():
    # MusicBrainz asks API users to identify themselves. Optional: put a contact URL or
    # email in contact.txt (this file is git-ignored). Otherwise a generic name is used.
    try: return open("contact.txt", encoding="utf-8").read().strip() or "no-contact-given"
    except OSError: return "no-contact-given"
UA = f"spotify-genre-sorter/1.0 ({_contact()})"
MIN_SONGS = 8

# Genre vocabulary: only tags that are real genres count (MusicBrainz tags also hold junk like "american").
GENRES = """acid house;acid techno;acid trance;acid jazz;afro house;afrobeat;afrobeats;amapiano;ambient;ambient techno;
alternative rock;alternative hip hop;alternative r&b;art pop;art rock;bass house;bass music;big beat;bossa nova;breakbeat;breakcore;
brostep;chillout;chillwave;classic rock;club;cold wave;country;dance;dance-pop;dark ambient;dark wave;darkwave;deep house;disco;
downtempo;drum and bass;dub;dubstep;edm;electro;electro house;electroclash;electronic;electronica;electropop;emo;euro disco;
eurodance;europop;experimental;folk;folk rock;funk;future bass;future garage;garage;garage rock;glitch hop;goa trance;grime;grunge;
happy hardcore;hard house;hard techno;hard trance;hardcore;hardstyle;hip hop;hi-nrg;house;hyperpop;idm;indie;indie pop;indie rock;
indie folk;industrial;italo disco;jazz;jazz rap;jungle;k-pop;krautrock;latin;lo-fi;lofi;mellow;melodic house;melodic techno;
metal;minimal techno;minimal;moombahton;neo soul;new age;new wave;nu disco;pop;pop rock;post-punk;post-rock;progressive house;
progressive trance;progressive rock;psychedelic rock;psytrance;punk;punk rock;r&b;rap;reggae;reggaeton;rock;russian pop;
russian rock;samba;schranz;shoegaze;sovietwave;soviet wave;soul;synthpop;synthwave;tech house;techno;trance;trap;trip hop;
tropical house;uk garage;vaporwave;vocal trance;witch house;world;electro swing;french house;nu metal;heavy metal;hard rock;
ballad;singer-songwriter;blues;classical;soundtrack;phonk;drift phonk;riddim;melodic dubstep;chillstep;liquid drum and bass;
neurofunk;breaks;trance;uplifting trance;tech trance;dream trance;deep techno;detroit techno;dub techno;organic house;
slap house;jersey club;baile funk;cumbia;salsa;bachata;mpb;tropicalia;chanson;rai;gypsy;balkan;turkish;arabic""".replace("\n", "").split(";")
GENRES = {g.strip() for g in GENRES if g.strip()}
GENERIC = {"electronic", "pop", "rock", "dance", "house", "techno", "hip hop", "rap", "indie", "metal", "folk", "world", "club", "experimental", "electro", "latin"}

def fetch(artist):
    q = urllib.parse.quote(f'artist:"{artist}"')
    url = f"https://musicbrainz.org/ws/2/artist/?query={q}&fmt=json&limit=3"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            for a in data.get("artists", []):
                if a.get("score", 0) >= 90 and a.get("name", "").lower() == artist.lower():
                    tags = sorted(a.get("tags", []), key=lambda t: -t.get("count", 0))
                    return [(t["name"].lower(), t.get("count", 0)) for t in tags]
            return []
        except Exception as e:
            time.sleep(3 * (attempt + 1))
    return None

def pick(tags):
    cand = [(n, c) for n, c in tags if n in GENRES]
    if not cand: return None
    # most specific wins over generic, then popularity
    return max(cand, key=lambda x: (x[0] not in GENERIC, x[1], len(x[0])))[0]

def main():
    rows = list(csv.DictReader(open("preview_songs.csv", encoding="utf-8")))
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    artists = sorted({r["artists"].split(", ")[0].strip() for r in rows if r["song"] and r["artists"]})
    todo = [a for a in artists if a not in cache]
    print(f"{len(artists)} artists, {len(todo)} to look up (~{len(todo)//60 + 1} min)", flush=True)
    for i, a in enumerate(todo, 1):
        res = fetch(a)
        if res is not None: cache[a] = res
        if i % 20 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"))
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(1.1)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"))

    for r in rows:
        r["niche"] = pick(cache.get(r["artists"].split(", ")[0].strip(), [])) if r["song"] else None
    size = {}
    for r in rows: size[r["niche"]] = size.get(r["niche"], 0) + 1
    for r in rows:
        n = r["niche"]
        r["bucket"] = "Unsorted" if (n is None or size[n] < MIN_SONGS) else n.title()
    with open("song_genres.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["bucket", "song", "artists", "niche_before_rollup", "uri"])
        for r in sorted(rows, key=lambda r: (r["bucket"], r["artists"])):
            w.writerow([r["bucket"], r["song"], r["artists"], r["niche"] or "", r["uri"]])
    counts = {}
    for r in rows: counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1
    with open("genre_summary.txt", "w", encoding="utf-8") as f:
        for b, n in sorted(counts.items(), key=lambda kv: -kv[1]): f.write(f"{n:5d}  {b}\n")
    print(open("genre_summary.txt", encoding="utf-8").read())
    print("Done. Nothing in Spotify was changed.")

main()
