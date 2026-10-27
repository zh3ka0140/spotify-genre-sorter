/*
 Scrape every playlist in your Spotify library (yours, saved from others, Spotify-made)
 and download playlists_scraped.json. Read-only: it only opens playlists and reads the page.

 How to use
 1. Open https://open.spotify.com in Chrome/Edge and sign in.
 2. Press F12, open the Console tab. If the browser asks, type: allow pasting
 3. Paste this whole file and press Enter. Leave the tab open and in front.
    Progress prints as  [3/60] Playlist name (123 songs). Large libraries take 10-30 minutes.
 4. When it says DONE, playlists_scraped.json lands in your Downloads folder. Move it into
    this folder and run:  python spotify_playlist_sorter_full.py
 To stop early run:  window.__stop = true   (it still downloads what it has).
 Playlists named "Genre: ..." and Liked Songs are skipped (Liked Songs come from the API).
*/
(async () => {
  window.__stop = false;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const side = document.querySelector('#Desktop_LeftSidebar_Id');
  const sc = [...side.querySelectorAll('*')].find(d => d.scrollHeight > d.clientHeight + 100 && getComputedStyle(d).overflowY !== 'visible');
  const key = r => { const l = r.innerText.split('\n').map(s => s.trim()).filter(Boolean); return { name: l[0], creator: l[l.length - 1], k: l[0] + '||' + l[l.length - 1] }; };
  const skip = k => /^Genre: /.test(k.name) || k.name === 'Liked Songs' || k.name === 'Your Episodes';
  const scroller = el => { let p = el.parentElement; while (p) { const s = getComputedStyle(p).overflowY; if ((s === 'auto' || s === 'scroll') && p.scrollHeight > p.clientHeight + 50) return p; p = p.parentElement; } return null; };
  const scrape = async () => {
    const out = new Map();
    const grab = () => document.querySelectorAll('[data-testid="tracklist-row"]').forEach(r => {
      const t = r.querySelector('a[href^="/track/"]'); if (!t) return;
      const id = t.getAttribute('href').split('/track/')[1].split('?')[0];
      if (out.has(id)) return;
      out.set(id, [t.textContent.trim(), [...r.querySelectorAll('a[href^="/artist/"]')].map(a => a.textContent.trim()).join(', ')]);
    });
    let first = null;
    for (let i = 0; i < 20 && !first; i++) { first = document.querySelector('[data-testid="tracklist-row"]'); if (!first) await sleep(250); }
    if (!first) return out;
    const sp = scroller(first);
    if (sp) {
      sp.scrollTop = 0; await sleep(500); grab();
      for (let i = 0; i < 2000; i++) {
        sp.scrollTop += Math.max(250, sp.clientHeight * 0.6); await sleep(200); grab();
        if (sp.scrollTop + sp.clientHeight >= sp.scrollHeight - 5) { await sleep(400); grab(); break; }
      }
    } else grab();
    return out;
  };
  const data = {}, visited = new Set();
  sc.scrollTop = 0; await sleep(500);
  while (!window.__stop) {
    let target = null;
    for (const r of side.querySelectorAll('[role=row]')) { const k = key(r); if (!k.name || skip(k) || visited.has(k.k)) continue; target = { r, k }; break; }
    if (!target) { if (sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 5) break; sc.scrollTop += 200; await sleep(250); continue; }
    visited.add(target.k.k);
    target.r.scrollIntoView({ block: 'center' }); await sleep(200);
    (target.r.querySelector('[role=button]') || target.r).click();
    await sleep(1800);
    const m = await scrape();
    data[target.k.k] = [...m.entries()];
    console.log(`[${visited.size}] ${target.k.name} (${m.size} songs)`);
  }
  const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'playlists_scraped.json';
  document.body.appendChild(a); a.click(); a.remove();
  console.log('DONE. playlists_scraped.json downloaded.');
})();
