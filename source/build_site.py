#!/usr/bin/env python3
"""Build the real 20blok.com site (static files for Vercel) from the demo template + data.
Usage: python3 -I build_site.py <out_dir> [SUPABASE_URL SUPABASE_ANON_KEY]
"""
import base64, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]
sb_url = sys.argv[2] if len(sys.argv) > 3 else "__SB_URL__"
sb_key = sys.argv[3] if len(sys.argv) > 3 else "__SB_KEY__"

t = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
IM = json.load(open(os.path.join(HERE, "images.json")))

def R(a, b, count=1):
    global t
    assert a in t, a[:80]
    t = t.replace(a, b, count)

# ---------- media files instead of data URIs ----------
os.makedirs(os.path.join(out, "media"), exist_ok=True)
paths = {}
for k, uri in IM.items():
    head, b64 = uri.split(",", 1)
    mime = head[5:].split(";")[0]
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "video/mp4": "mp4"}.get(mime, "bin")
    fn = f"media/{k}.{ext}"
    open(os.path.join(out, fn), "wb").write(base64.b64decode(b64))
    paths[k] = fn

# ---------- page head: real document ----------
R('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
t = t.replace('<title>20 Blok</title>', '''<title>20 Blok — Culture, creativity, and the internet.</title>
<meta name="description" content="20 Blok by Lenny Lesser: twenty stories every issue on culture, creativity and the internet. You pick the winners.">
<meta property="og:title" content="20 Blok">
<meta property="og:description" content="Culture, creativity, and the internet. Twenty stories every issue. You pick the winners.">
<meta property="og:image" content="https://20blok.com/media/cover.jpg">
<meta property="og:url" content="https://20blok.com/">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%230B0B0C'/%3E%3Ctext x='32' y='43' font-family='Georgia' font-weight='900' font-size='30' text-anchor='middle' fill='%23E0483B'%3E20%3C/text%3E%3C/svg%3E">''', 1)
style_end = t.index('</style>') + len('</style>')
head, body = t[:style_end], t[style_end:]
reset = '<style>html{-webkit-text-size-adjust:100%}body{margin:0}img{max-width:100%}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
t = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
     '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
     + reset + head +
     '\n<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>\n'
     '</head>\n<body>\n' + body + '\n</body>\n</html>\n')

# ---------- votes through Supabase (one per browser via anonymous sign-in) ----------
s = t.index('async function connect(){'); e = t.index('/* ---------- helpers ---------- */')
t = t[:s] + '''const SB_URL = "%s", SB_KEY = "%s";
let sb = null;
async function loadVotes(){
  if (!sb) return;
  const { data, error } = await sb.from("votes").select("blok,voter").eq("issue", ISSUE).limit(100000);
  if (error) return;
  shared = true; const t = {}, m = {};
  data.forEach(v => { t[v.blok] = (t[v.blok]||0) + 1; if (v.voter === uid) m[v.blok] = 1; });
  tallies = t; mine = m; refresh();
}
async function connect(){
  if (!window.supabase || SB_URL.startsWith("__")) return;
  try{
    sb = window.supabase.createClient(SB_URL, SB_KEY);
    let { data:{ session } } = await sb.auth.getSession();
    if (!session){ const r = await sb.auth.signInAnonymously(); session = r.data && r.data.session; }
    if (!session) return;
    uid = session.user.id;
    await loadVotes();
    sb.channel("votes-"+ISSUE).on("postgres_changes", {event:"*", schema:"public", table:"votes", filter:"issue=eq."+ISSUE}, () => loadVotes()).subscribe();
    document.addEventListener("visibilitychange", () => { if (!document.hidden) loadVotes(); });
  }catch(e){}
}
async function vote(id, dir){
  const prev = mine[id]||0, next = prev===dir ? 0 : dir;
  mine = {...mine}; if (next) mine[id]=next; else delete mine[id];
  tallies = {...tallies, [id]:(tallies[id]||0) - prev + next};
  refresh();
  if (shared && sb && uid){
    try{
      if (next) await sb.from("votes").insert({issue:ISSUE, blok:id, voter:uid});
      else await sb.from("votes").delete().match({issue:ISSUE, blok:id, voter:uid});
    }catch(e){}
  } else { lsSet(mine); }
}

''' % (sb_url, sb_key) + t[e:]

# ---------- comments: Pass 2 ----------
s = t.index('function commentsSection(b){'); e = t.index('function linkify(text){')
t = t[:s] + '''function commentsSection(b){
  return el("section",{class:"comments","aria-labelledby":"c-head"},
    el("h2",{id:"c-head"},"Comments"),
    el("p",{class:"c-empty",text:"Comments open soon. Want in early? Subscribe and you'll be first to know."}),
    el("p",{}, el("a",{class:"sub",href:NEWSLETTER,target:"_blank",rel:"noopener",text:"SUBSCRIBE"})));
}
''' + t[e:]
t = t.replace('if (blok){ drawComments(); renderComments(); }', '')

# ---------- real embeds ----------
R('function figure(x){', '''function ytId(u){ const m = u.match(/(?:youtu\\.be\\/|v=|shorts\\/|embed\\/)([A-Za-z0-9_-]{11})/); return m ? m[1] : null; }
let embedScripts = {};
function loadScript(src, done){ if (embedScripts[src]) { done && done(); return; } embedScripts[src]=1; const s=document.createElement("script"); s.src=src; s.async=true; s.onload=()=>done&&done(); document.body.append(s); }
function hydrateEmbeds(){
  if (document.querySelector(".instagram-media")) loadScript("https://www.instagram.com/embed.js", ()=>{ try{ window.instgrm && window.instgrm.Embeds.process(); }catch(e){} });
  if (document.querySelector(".twitter-tweet")) loadScript("https://platform.twitter.com/widgets.js", ()=>{ try{ window.twttr && window.twttr.widgets.load(); }catch(e){} });
  try{ window.instgrm && window.instgrm.Embeds.process(); }catch(e){}
  try{ window.twttr && window.twttr.widgets && window.twttr.widgets.load(); }catch(e){}
}
function figure(x){
  if (x.href && !x.keepThumb){
    const yt = /youtu\\.?be/.test(x.href) && ytId(x.href);
    if (yt){
      const tall = /shorts\\//.test(x.href);
      const f = el("iframe",{src:"https://www.youtube-nocookie.com/embed/"+yt+"?rel=0", title:x.cap||x.alt||"YouTube video", loading:"lazy",
        allow:"accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share", allowfullscreen:"", referrerpolicy:"strict-origin-when-cross-origin"});
      return el("figure",{class:"fig embed "+(tall?"tall":"wide")}, el("div",{class:"embed-frame"}, f), x.cap?el("figcaption",{text:x.cap.replace(/ ?Watch on YouTube\\.?$/,"").replace(/ ?Listen on YouTube\\.?$/,"")}):null);
    }
    const ig = /instagram\\.com\\/(p|reels?|tv)\\//.test(x.href);
    const tw = /(x|twitter)\\.com\\/[^/]+\\/status\\//.test(x.href);
    if (ig || tw){
      const thumb = el("a",{class:"frame",href:x.href,target:"_blank",rel:"noopener"}, el("img",{src:IMG[x.src],alt:x.alt||x.cap||"",loading:"lazy"}),
        x.nobadge?null:el("span",{class:"badge"}, icon("M7 5l12 7-12 7z",true), x.badge||"WATCH"));
      if (ig){
        const m = x.href.match(/instagram\\.com\\/(p|reels?|tv)\\/([A-Za-z0-9_-]+)/);
        const kind = m[1].startsWith("reel") ? "reel" : m[1];
        const f = el("iframe",{src:"https://www.instagram.com/"+kind+"/"+m[2]+"/embed/", title:x.cap||x.alt||"Instagram post", loading:"lazy", scrolling:"no", allowtransparency:"true", allow:"encrypted-media; picture-in-picture"});
        return el("figure",{class:"fig embed social ig"}, el("div",{class:"ig-frame"}, f), x.cap?el("figcaption",{text:x.cap}):null);
      }
      const bq = ig ? null
                    : el("blockquote",{class:"twitter-tweet","data-theme":"dark","data-dnt":"true"}, el("a",{href:x.href.replace("x.com","twitter.com"),text:" "}), thumb);
      return el("figure",{class:"fig embed social"+(x.narrow?" narrow":"")}, bq, x.cap?el("figcaption",{text:x.cap}):null);
    }
  }''')
R('.pair{display:flex;', '''.fig.embed .embed-frame{position:relative;width:100%;aspect-ratio:16/9;border-radius:14px;overflow:hidden;background:#000}
.fig.embed.tall .embed-frame{aspect-ratio:9/16;max-width:360px;margin:0 auto}
.fig.embed iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.fig.embed.social{display:flex;flex-direction:column;align-items:center}
.fig.embed.social blockquote{margin:0 auto;width:100%;max-width:540px}
.fig.embed.social .twitter-tweet{max-width:550px!important}
.fig.embed.social blockquote.instagram-media,.fig.embed.social iframe.instagram-media{max-width:400px!important;width:100%!important;min-width:0!important;margin:0 auto!important}
.fig.embed.social iframe{position:static}
.fig.embed.ig .ig-frame{width:100%;max-width:400px;margin:0 auto;height:calc(min(100vw - 32px, 400px) * 1.25 + 168px);border-radius:12px;overflow:hidden;background:#fff}
.fig.embed.ig .ig-frame iframe{position:static;display:block;width:100%;height:100%;border:0}
.pair{display:flex;''')
R('window.addEventListener("hashchange", ()=>render(false));', 'window.addEventListener("hashchange", ()=>{ render(false); setTimeout(hydrateEmbeds,0); });')
R('render(false);\nconnect();', 'render(false);\nsetTimeout(hydrateEmbeds,0);\nconnect();')

# ---------- write ----------
dd = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
t = t.replace('__DATA__', dd).replace('__IMAGES__', json.dumps(paths))
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(t)
open(os.path.join(out, "vercel.json"), "w").write(json.dumps({"cleanUrls": True, "headers": [{"source": "/media/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}]}, indent=2))
print("built", out, "media files:", len(paths))
