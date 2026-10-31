#!/usr/bin/env python3
"""Build the real 20blok.com site (static files for Vercel) from the demo template + data.
Usage: python3 -I build_site.py <out_dir> [SUPABASE_URL SUPABASE_ANON_KEY]
"""
import base64, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]
sb_url = sys.argv[2] if len(sys.argv) > 3 else "https://kuyhymlhaifxccovamdt.supabase.co"
sb_key = sys.argv[3] if len(sys.argv) > 3 else "sb_publishable_hK_MKPDnsGxDUTu2zRWYgg_d4WSwjIS"

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
    paths[k] = "/" + fn

# ---------- page head: real document ----------
R('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
t = t.replace('<title>20 Blok</title>', '''<title>20 Blok — Culture, creativity, and the internet.</title>
<meta name="description" content="20 Blok by Lenny Lesser: twenty stories every issue on culture, creativity and the internet. You pick the winners.">
<meta property="og:title" content="20 Blok">
<meta property="og:description" content="Culture, creativity, and the internet. Twenty stories every issue. You pick the winners.">
<meta property="og:image" content="https://20blok.com/media/cover.jpg">
<meta property="og:url" content="https://20blok.com/">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="20 Blok" href="/feed.xml">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%230B0B0C'/%3E%3Ctext x='32' y='43' font-family='Georgia' font-weight='900' font-size='30' text-anchor='middle' fill='%23E0483B'%3E20%3C/text%3E%3C/svg%3E">''', 1)
style_end = t.index('</style>') + len('</style>')
head, body = t[:style_end], t[style_end:]
reset = '<style>html{-webkit-text-size-adjust:100%}body{margin:0}img{max-width:100%}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
t = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
     '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
     + reset + head +
     '\n<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.57.4/dist/umd/supabase.js"></script>\n'
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
    subscribeBox());
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
# ---------- real addresses (20blok.com/based) instead of #based ----------
for a_, b_ in [('href="#this-week"','href="/"'),('href="#all-time"','href="/all-time"'),('href="#past-issues"','href="/past-issues"'),('href="#issue-notes"','href="/issue-notes"'),
               ('href:"#this-week"','href:"/"'),('href:"#issue-notes"','href:"/issue-notes"'),('href:"#must-see"','href:"/must-see"'),('href:"#straight-up"','href:"/straight-up"'),
               ('href:"#"+','href:"/"+'),('location.hash = b.id','go(b.id)'),('x.href.startsWith("#")','x.href.startsWith("/")')]:
    assert a_ in t, a_; t = t.replace(a_, b_)
R('function curRoute(){ return (location.hash||"").replace(/^#/,"") || "this-week"; }', '''function curRoute(){
  const p = location.pathname.replace(/^\\/+|\\/+$/g,"");
  if (!p){ const h=(location.hash||"").replace(/^#/,""); if (h) return h; }
  return p || "this-week";
}
const TITLES = {"all-time":"All-Time","past-issues":"Past Issues","issue-notes":"Issue Notes","bonus":"Issue Notes"};
function go(id){ const path = (!id || id==="this-week") ? "/" : "/"+id; if (location.pathname!==path || location.hash) history.pushState({}, "", path); render(false); }
document.addEventListener("click", e=>{
  if (e.defaultPrevented || e.button!==0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = e.target.closest("a[href^='/']"); if (!a || a.target) return;
  const href = a.getAttribute("href"); if (href.startsWith("/media/") || href.startsWith("/api/")) return;
  e.preventDefault(); go(href.replace(/^\/+|\/+$/g,"") || "this-week");
});
window.addEventListener("popstate", ()=>render(false));
(function(){ const h=(location.hash||"").replace(/^#/,""); if (h && (location.pathname==="/"||location.pathname==="")) history.replaceState({}, "", "/"+(h==="this-week"?"":h)); })();''')
R('  const h = (location.hash||"").replace(/^#/,"") || "this-week";', '  const h = curRoute();')
R('  else if (commentsUnsub){', '  document.title = blok ? blok.title+" — 20 Blok" : (TITLES[h] ? TITLES[h]+" — 20 Blok" : "20 Blok — Culture, creativity, and the internet.");\n  setTimeout(hydrateEmbeds,0);\n  if (false){}\n  else if (commentsUnsub){')
R('window.addEventListener("hashchange", ()=>render(false));', 'window.addEventListener("hashchange", ()=>{ const h=(location.hash||"").replace(/^#/,""); if (h) history.replaceState({}, "", "/"+(h==="this-week"?"":h)); render(false); });')
R('  window.addEventListener("hashchange",()=>{ if(root&&!root.hidden) hide(); });', '  window.addEventListener("popstate",()=>{ if(root&&!root.hidden) hide(); });')

# ---------- Beehiiv subscribe box ----------
R(' Or leave a comment on any blok.', '')
R('    el("a",{class:"notes-link",href:"/issue-notes"}', '    subscribeBox(),\n    el("a",{class:"notes-link",href:"/issue-notes"}')
SUB_JS = '''function subscribeBox(){
  const input = el("input",{type:"email",name:"email",required:"required",autocomplete:"email",inputmode:"email",placeholder:"you@email.com","aria-label":"Your email"});
  const btn = el("button",{type:"submit",class:"sb-btn"},"Subscribe");
  const msg = el("p",{class:"sb-msg","aria-live":"polite"});
  const form = el("form",{class:"sb-form",onsubmit:async e=>{
    e.preventDefault(); const email=input.value.trim(); if(!email) return;
    btn.disabled=true; msg.textContent="Signing you up…";
    try{
      const r = await fetch("/api/subscribe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})});
      const j = await r.json().catch(()=>({}));
      if (r.ok && j.ok){ rememberPage(); markSubscribed(); form.replaceChildren(el("p",{class:"sb-done",text:"Almost there. Check your inbox and tap the confirm link."})); return; }
      msg.replaceChildren(document.createTextNode(j.error==="email" ? "That email doesn’t look right. Try again." : "That didn’t go through"+(j.error?" ("+j.error+(j.status?" "+j.status:"")+")":"")+". "), j.error==="email" ? "" : el("a",{href:NEWSLETTER,target:"_blank",rel:"noopener",text:"Subscribe on the newsletter page →"}));
    }catch(err){ msg.replaceChildren("That didn’t go through. ", el("a",{href:NEWSLETTER,target:"_blank",rel:"noopener",text:"Subscribe on the newsletter page →"})); }
    btn.disabled=false; }}, input, btn);
  return el("section",{class:"subscribe-band",id:"subscribe-band","aria-labelledby":"sb-head"},
    el("div",{}, el("h2",{id:"sb-head",text:"Get the next issue"}), el("p",{text:"New stories every issue, straight to your inbox. Free."})),
    form, msg);
}
function goSubscribe(e){
  const band = document.getElementById("subscribe-band");
  if (!band) return;
  e.preventDefault();
  band.scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block:"center"});
  const i = band.querySelector("input"); if (i) setTimeout(()=>i.focus({preventScroll:true}), 500);
}
'''
R('function ytId(u){', SUB_JS + 'function ytId(u){')
R('  document.getElementById("view").replaceChildren(...kids);', '  const extra = (h==="past-issues"||h==="issue-notes"||h==="bonus") ? [el("div",{class:"article",style:"margin-top:32px"}, subscribeBox())] : [];\n  document.getElementById("view").replaceChildren(...kids, ...extra);')
R('<a class="sub" href="https://lennylesser.beehiiv.com" target="_blank" rel="noopener">SUBSCRIBE</a>',
  '<a class="sub" href="https://lennylesser.beehiiv.com" target="_blank" rel="noopener" onclick="goSubscribe(event)">SUBSCRIBE</a>')
# ---------- privacy page + Turnstile (invisible bot check before anonymous voting) ----------
TURNSTILE_SITE_KEY = "0x4AAAAAAFs0zYHiwJb4Wxa7"
R('<a href="/issue-notes">Issue notes</a> · ', '<a href="/issue-notes">Issue notes</a> · <a href="/privacy">Privacy</a> · ')
R('(h==="issue-notes"||h==="bonus") ? notesView() : gridView(false);', '(h==="issue-notes"||h==="bonus") ? notesView() : h==="privacy" ? privacyView() : h==="welcome" ? welcomeView() : gridView(false);')
PRIV_JS = '''function privacyView(){
  const P = t => el("p",{text:t});
  return [el("article",{class:"article"},
    el("a",{class:"back",href:"/",text:"← BACK TO THE GRID"}),
    el("header",{class:"art-head"}, el("p",{class:"eyebrow",text:"20 Blok"}), el("h1",{class:"art-title",text:"Privacy"})),
    el("div",{class:"prose"},
      P("20 Blok is a free magazine by Lenny Lesser. This page explains what the site collects and why. Last updated October 30, 2026."),
      el("h3",{text:"Email"}),
      P("If you subscribe, your email address goes to Beehiiv, the service that sends the newsletter. It's used only to send you new issues and newsletter updates. You can unsubscribe from any email."),
      el("h3",{text:"Votes"}),
      P("Uprating a blok doesn't ask for your name or email. Your browser gets an anonymous ID so each person counts once. Votes are stored with Supabase, which hosts the site's database."),
      el("h3",{text:"Bot protection"}),
      el("p",{}, "This site uses Cloudflare Turnstile to keep bots from faking votes. Turnstile checks your browser quietly in the background. Its handling of data is described in the ",
        el("a",{href:"https://www.cloudflare.com/turnstile-privacy-policy/",target:"_blank",rel:"noopener",text:"Cloudflare Turnstile Privacy Addendum"}), "."),
      el("h3",{text:"Embedded videos"}),
      P("Articles include videos and posts from YouTube, Instagram and X. When they load, those services may collect data under their own privacy policies. YouTube videos use YouTube's privacy-enhanced mode."),
      el("h3",{text:"Hosting"}),
      P("The site is hosted by Vercel, which keeps standard server logs. 20 Blok doesn't sell your data or run advertising trackers."),
      el("h3",{text:"Questions"}),
      el("p",{}, "Email lennybusinessnow@gmail.com.")))];
}
function getTurnstileToken(){
  return new Promise((resolve) => {
    let done = false; const finish = v => { if (!done){ done = true; resolve(v); } };
    setTimeout(() => finish(null), 15000);
    const run = () => { try{
      const box = el("div",{style:"position:fixed;left:-9999px;bottom:0;width:1px;height:1px;overflow:hidden","aria-hidden":"true"}); document.body.append(box);
      window.turnstile.render(box, {sitekey: "%s", callback: tok => finish(tok), "error-callback": () => finish(null), "expired-callback": () => finish(null)});
    }catch(e){ finish(null); } };
    if (window.turnstile) { run(); return; }
    const s = document.createElement("script"); s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"; s.async = true; s.onload = run; s.onerror = () => finish(null); document.head.append(s);
  });
}
''' % TURNSTILE_SITE_KEY
R('function ytId(u){', PRIV_JS + 'function ytId(u){')
NUDGE_JS = '''function welcomeView(){
  markSubscribed();
  return [el("article",{class:"article"},
    el("header",{class:"art-head"}, el("p",{class:"eyebrow",text:"20 Blok"}), el("h1",{class:"art-title",text:"You\\u2019re in."})),
    el("div",{class:"prose"},
      el("p",{class:"lead",text:"Thanks for subscribing. Each new issue lands in your inbox, and the full magazine lives here."}),
      el("p",{}, "Bookmark ", el("b",{text:"20blok.com"}), ". That\\u2019s where every issue goes up first."),
      el("h3",{text:"How it works"}),
      el("ul",{}, el("li",{text:"Every issue has 20 bloks: stories on culture, creativity and the internet."}), el("li",{text:"Tap the arrow on any blok to uprate it. No sign-in needed."}), el("li",{text:"The most uprated bloks rise to the top-left of the grid."}))),
    el("div",{class:"wl-actions"}, el("a",{class:"sub",href:"/",text:"CONTINUE READING \\u2192"})))];
}
function lsOK(k,v){ try{ if(v===undefined) return localStorage.getItem(k); localStorage.setItem(k,v); }catch(e){ return null; } }
function rememberPage(){ const h=curRoute(); if (BLOKS.find(b=>b.id===h)) lsOK("blok20-last", h); }
function markSubscribed(){ lsOK("blok20-subscribed","1"); const n=document.getElementById("sb-nudge"); if(n) n.remove(); }
let nudgeShown = false, bloksSeen = 0;
function maybeNudge(){
  if (nudgeShown || lsOK("blok20-subscribed")) return;
  const until = Number(lsOK("blok20-nudge-hide")||0); if (until && Date.now() < until) return;
  const band = document.getElementById("subscribe-band"); if (band && band.getBoundingClientRect().top < innerHeight) return;
  nudgeShown = true;
  const input = el("input",{type:"email",required:"required",autocomplete:"email",inputmode:"email",placeholder:"you@email.com","aria-label":"Your email"});
  const msg = el("span",{class:"nd-msg","aria-live":"polite"});
  let bar;
  const close = el("button",{type:"button",class:"nd-x","aria-label":"Close",text:"\\u00d7",onclick:()=>{ lsOK("blok20-nudge-hide", String(Date.now()+7*864e5)); bar.remove(); }});
  const form = el("form",{class:"nd-form",onsubmit:async e=>{ e.preventDefault(); const email=input.value.trim(); if(!email) return; msg.textContent="Signing you up\\u2026";
      try{ const r=await fetch("/api/subscribe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})}); const j=await r.json().catch(()=>({}));
        if(r.ok&&j.ok){ rememberPage(); lsOK("blok20-subscribed","1"); bar.replaceChildren(el("p",{class:"nd-done",text:"Almost there. Check your inbox to confirm."})); setTimeout(()=>bar.remove(),5000); return; }
        msg.textContent = j.error==="email" ? "Check that email." : "Didn\\u2019t go through. Try the form at the bottom."; }catch(err){ msg.textContent="Didn\\u2019t go through."; } }},
    input, el("button",{type:"submit",class:"sb-btn"},"Subscribe"));
  bar = el("aside",{id:"sb-nudge",class:"nudge","aria-label":"Subscribe"},
    el("div",{class:"nd-copy"}, el("b",{text:"Enjoying 20 Blok?"}), el("span",{text:" Get the next issue free."})), form, msg, close);
  document.body.append(bar);
}
function nudgeWatch(){
  const h = curRoute(); if (BLOKS.find(b=>b.id===h)) bloksSeen++;
  if (bloksSeen >= 2) setTimeout(maybeNudge, 1500);
}
window.addEventListener("scroll", ()=>{ if (nudgeShown) return; const h=curRoute(); if (!BLOKS.find(b=>b.id===h)) return;
  const d=document.documentElement; if ((scrollY+innerHeight)/d.scrollHeight > 0.6) maybeNudge(); }, {passive:true});
'''
R('function ytId(u){', NUDGE_JS + 'function ytId(u){')
SHARE_JS = '''function swoosh(){ const s=document.createElementNS(NS,"svg");
  [["width","22"],["height","22"],["viewBox","0 0 24 24"],["fill","none"],["stroke","currentColor"],["stroke-width","1.1"],["stroke-linejoin","round"],["stroke-linecap","round"],["aria-hidden","true"]].forEach(([k,v])=>s.setAttribute(k,v));
  const p=document.createElementNS(NS,"path"); p.setAttribute("d","M13.5 4.5 L21 11 L13.5 17.5 V13.7 C8.8 13.5 5.6 15.2 3 19.5 C3.5 13 7.4 8.9 13.5 8.3 Z"); s.append(p); return s; }
function shareBar(b, bottom){
  const url = "https://20blok.com/"+b.id, title = b.title+" \\u2014 20 Blok";
  const u = encodeURIComponent(url), tt = encodeURIComponent(title), both = encodeURIComponent(title+" "+url);
  const links = [["X","https://twitter.com/intent/tweet?text="+tt+"&url="+u],["Reddit","https://www.reddit.com/submit?url="+u+"&title="+tt],
    ["LinkedIn","https://www.linkedin.com/sharing/share-offsite/?url="+u],["Telegram","https://t.me/share/url?url="+u+"&text="+tt],
    ["Facebook","https://www.facebook.com/sharer/sharer.php?u="+u],["Threads","https://www.threads.net/intent/post?text="+both],["Email","mailto:?subject="+tt+"&body="+both]];
  const menu = el("div",{class:"sh-menu",role:"menu",hidden:"hidden"});
  const copy = el("button",{type:"button",class:"sh-item",role:"menuitem",text:"Copy link",onclick:async()=>{ try{ await navigator.clipboard.writeText(url); copy.textContent="Link copied"; }catch(e){ copy.textContent=url; } setTimeout(()=>copy.textContent="Copy link",2000); }});
  menu.append(copy, ...links.map(([n,h])=>el("a",{class:"sh-item",role:"menuitem",href:h,target:"_blank",rel:"noopener",text:n})));
  if (navigator.share) menu.append(el("button",{type:"button",class:"sh-item",role:"menuitem",text:"Other apps\\u2026",onclick:()=>{ navigator.share({title, url}).catch(()=>{}); }}));
  const btn = el("button",{type:"button",class:"sh-btn","aria-haspopup":"true","aria-expanded":"false",onclick:e=>{ e.stopPropagation(); const open=menu.hidden; document.querySelectorAll(".sh-menu").forEach(m=>m.hidden=true); menu.hidden=!open; btn.setAttribute("aria-expanded",String(open)); }},
    swoosh());
  btn.setAttribute("aria-label","Share this blok"); btn.setAttribute("title","Share");
  return el("div",{class:"share"+(bottom?" share-bottom":"")}, btn, menu);
}
document.addEventListener("click", e=>{ if (!e.target.closest(".share")) document.querySelectorAll(".sh-menu").forEach(m=>m.hidden=true); });
document.addEventListener("keydown", e=>{ if (e.key==="Escape") document.querySelectorAll(".sh-menu").forEach(m=>m.hidden=true); });
'''
R('function ytId(u){', SHARE_JS + 'function ytId(u){')
R('el("span",{class:"rank",text:String(r+1).padStart(2,"0")})', '(r===0 && (tallies[b.id]||0)>0 ? el("span",{class:"rank rank-top",title:"Top pick: most uprated","aria-label":"Number 1, top pick"}, el("span",{class:"rt-num",text:"01"}), el("span",{class:"rt-tag",text:"TOP PICK"})) : el("span",{class:"rank",text:String(r+1).padStart(2,"0")}))')
R('" min read"), voteBox(b))),', '" min read", shareBar(b,false)), voteBox(b))),')
R('    commentsSection(b),', '    shareBar(b,true),\n    commentsSection(b),')
R('  setTimeout(hydrateEmbeds,0);\n  if (false){}', '  setTimeout(hydrateEmbeds,0);\n  nudgeWatch();\n  if (false){}')
R('if (!session){ const r = await sb.auth.signInAnonymously(); session = r.data && r.data.session; }',
  'if (!session){ const captchaToken = await getTurnstileToken(); const r = await sb.auth.signInAnonymously(captchaToken ? {options:{captchaToken}} : undefined); session = r.data && r.data.session; }')
R('const TITLES = {"all-time":"All-Time"', 'const TITLES = {"welcome":"Welcome","privacy":"Privacy","all-time":"All-Time"')

SUB_CSS = '''.rank-top{position:relative;display:inline-grid;place-items:center;width:clamp(44px,22cqi,72px);aspect-ratio:1;color:#fff}
.rank-top::before{content:"";position:absolute;inset:0;background:var(--red);clip-path:polygon(50% 0%,61% 11%,75% 7%,79% 21%,93% 25%,89% 39%,100% 50%,89% 61%,93% 75%,79% 79%,75% 93%,61% 89%,50% 100%,39% 89%,25% 93%,21% 79%,7% 75%,11% 61%,0% 50%,11% 39%,7% 25%,21% 21%,25% 7%,39% 11%);box-shadow:none;transform:rotate(-8deg)}
.rank-top .rt-num{position:relative;font-size:clamp(17px,9cqi,30px);line-height:1;margin-top:-6%}
.rank-top .rt-tag{position:absolute;bottom:22%;font-family:var(--sans,inherit);font-weight:900;font-size:clamp(5.5px,2.6cqi,9px);letter-spacing:.08em;white-space:nowrap}
.byline-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.share{position:relative;display:inline-block}
.share-bottom{margin:28px 0 8px}
.share-bottom .sh-btn{width:44px;height:44px;border:1px solid var(--line);border-radius:12px}
.sh-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;padding:0;border-radius:10px;border:0;background:transparent;color:var(--fg);font-weight:800;font-size:12px;letter-spacing:1.5px;cursor:pointer}
.sh-btn svg{width:22px;height:22px}
.byline .share{vertical-align:middle;margin-left:6px}
.byline .sh-btn{color:var(--fg-soft)}
@media (max-width:820px){.byline{flex-wrap:nowrap}.byline p{flex:1 1 auto;min-width:0}.byline .vote{width:auto;flex:0 0 auto;justify-content:flex-start;gap:4px;padding:3px 10px 3px 3px;border-radius:12px}.byline .vote button{width:34px;height:34px}.byline p{font-size:12px;letter-spacing:.2px;white-space:nowrap}.byline .share{margin-left:2px}.byline .sh-btn{width:30px;height:30px}.byline .sh-btn svg{width:20px;height:20px}}
.sh-btn:hover,.sh-btn[aria-expanded="true"]{color:var(--red)}
.sh-menu{position:absolute;z-index:15;top:calc(100% + 8px);left:0;min-width:200px;display:grid;padding:6px;border-radius:14px;background:#151517;border:1px solid var(--line);box-shadow:0 18px 40px rgba(0,0,0,.6)}
.share-bottom .sh-menu{top:auto;bottom:calc(100% + 8px)}
.sh-item{display:block;width:100%;text-align:left;padding:10px 12px;border:0;border-radius:9px;background:none;color:var(--fg);font:600 15px var(--sans,inherit);text-decoration:none;cursor:pointer}
.sh-item:hover,.sh-item:focus-visible{background:rgba(255,255,255,.08)}
.nudge{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(env(safe-area-inset-bottom,0px) + 16px);z-index:20;width:min(720px, calc(100vw - 32px));box-sizing:border-box;display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:14px 44px 14px 18px;border-radius:16px;background:#151517;border:1px solid var(--red-deep);box-shadow:0 18px 40px rgba(0,0,0,.6);animation:ndIn .35s ease}
@keyframes ndIn{from{opacity:0;transform:translate(-50%,16px)}to{opacity:1;transform:translate(-50%,0)}}
@media (prefers-reduced-motion:reduce){.nudge{animation:none}}
.nd-copy{flex:1 1 200px;font-size:15px;color:var(--fg-soft)}.nd-copy b{color:var(--fg)}
.nd-form{display:flex;gap:8px;flex:1 1 280px;min-width:0;max-width:100%}
.nd-form input{width:0}
@media (max-width:640px){.nudge{padding:14px 14px 14px 16px}.nd-copy{padding-right:28px}.nd-form{flex-basis:100%}.nd-form .sb-btn{padding:0 12px;font-size:12px;letter-spacing:.5px}}
.nd-form input{flex:1;min-width:0;min-height:42px;padding:0 12px;border-radius:10px;border:1px solid var(--line);background:#0B0B0C;color:var(--fg);font-size:16px}
.nd-form .sb-btn{min-height:42px;padding:0 16px;box-shadow:none}
.nd-msg{flex-basis:100%;font-size:13px;color:var(--muted)}.nd-msg:empty{display:none}
.nd-x{position:absolute;top:6px;right:8px;width:32px;height:32px;border:0;background:none;color:var(--muted);font-size:22px;cursor:pointer}
.nd-done{margin:0;font-weight:700}
.wl-actions{display:grid;gap:12px;justify-items:start;margin-top:28px}
.wl-last{margin:0;font-size:14px;color:var(--muted)}
.wl-home{font-size:14px;color:var(--fg-soft)}
body:has(#sb-nudge) .float-vote{bottom:calc(env(safe-area-inset-bottom,0px) + 150px)}
.subscribe-band{display:grid;gap:14px;margin-top:24px;padding:24px;border-radius:16px;background:var(--panel);border:1px solid var(--line)}
.subscribe-band h2{margin:0 0 4px;font-family:var(--display);font-weight:900;font-size:clamp(24px,3vw,32px)}
.subscribe-band p{margin:0;color:var(--fg-soft)}
.sb-form{display:flex;flex-wrap:wrap;gap:10px;max-width:560px}
.sb-form input{flex:1 1 220px;min-width:0;min-height:48px;padding:0 16px;border-radius:12px;border:1px solid var(--line);background:#0B0B0C;color:var(--fg);font:500 16px var(--sans,inherit)}
.sb-form input::placeholder{color:var(--muted)}
.sb-form input:focus{outline:2px solid var(--red);outline-offset:1px}
.sb-btn{min-height:48px;padding:0 22px;border:0;border-radius:12px;background:var(--red-deep);color:var(--fg);font-weight:800;font-size:14px;letter-spacing:1px;text-transform:uppercase;cursor:pointer;box-shadow:0 4px 0 #4a0f0a}
.sb-btn:disabled{opacity:.6}
.sb-msg{margin:0;font-size:14px;color:var(--muted)}.sb-msg a{color:var(--fg)}
.sb-done{margin:0;font-weight:700;color:var(--fg)}
'''
R('.fig.embed .embed-frame{', SUB_CSS + '.fig.embed .embed-frame{')

# ---------- write ----------
for b in data:
    for x in b["body"]:
        if x.get("t")=="link" and x.get("href","").startswith("#"): x["href"] = "/" + x["href"][1:]
dd = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
t = t.replace('__DATA__', dd).replace('__IMAGES__', json.dumps(paths))
import html as H
SITE = "https://20blok.com"
def page(route, title, desc, img, body_html):
    p = t
    p = p.replace("<title>20 Blok — Culture, creativity, and the internet.</title>", "<title>"+H.escape(title)+"</title>", 1)
    p = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="'+H.escape(desc)+'">', p, 1)
    p = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="'+H.escape(title)+'">', p, 1)
    p = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="'+H.escape(desc)+'">', p, 1)
    p = re.sub(r'<meta property="og:image" content="[^"]*">', '<meta property="og:image" content="'+SITE+img+'">', p, 1)
    url = SITE + ("/" if route=="" else "/"+route)
    p = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="'+url+'">\n<link rel="canonical" href="'+url+'">', p, 1)
    p = p.replace('<main class="wrap" id="view" aria-live="polite"></main>', '<main class="wrap" id="view" aria-live="polite">'+body_html+'</main>', 1)
    d = os.path.join(out, route) if route else out
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(p)
    return url
def txt(x): return H.escape(x.get("text",""))
def first_para(b):
    for x in b["body"]:
        if x.get("t")=="p" and x.get("text"): return x["text"]
    return ""
def short(s, n=155):
    s = re.sub(r"\s+"," ",s).strip(); return s if len(s)<=n else s[:n-1].rsplit(" ",1)[0]+"…"
urls = []
grid = "".join('<li><a href="/'+b["id"]+'">'+H.escape(b["name"])+': '+H.escape(b["title"])+'</a></li>' for b in data)
home_desc = "20 Blok by Lenny Lesser: twenty stories every issue on culture, creativity and the internet. You pick the winners."
urls.append(page("", "20 Blok — Culture, creativity, and the internet.", home_desc, "/media/cover.jpg", '<h1>20 Blok, Issue 7: Retail Mindset</h1><ul>'+grid+'</ul>'))
for b in data:
    body = "".join("<p>"+txt(x)+"</p>" if x.get("t") in ("p","q","pull") else ("<h2>"+txt(x)+"</h2>" if x.get("t")=="h" else "") for x in b["body"])
    img = paths.get(b.get("img") or "cover", "/media/cover.jpg")
    urls.append(page(b["id"], b["title"]+" — 20 Blok", short(first_para(b)) or home_desc, img, '<article><p>'+H.escape(b["name"])+'</p><h1>'+H.escape(b["title"])+'</h1>'+body+'</article>'))
for r_, ti in [("welcome","Welcome"),("privacy","Privacy"),("all-time","All-Time"),("past-issues","Past Issues"),("issue-notes","Issue Notes"),("bonus","Issue Notes")]:
    u = page(r_, ti+" — 20 Blok", home_desc, "/media/cover.jpg", "<h1>"+ti+"</h1>")
    if r_ not in ("bonus","welcome"): urls.append(u)
open(os.path.join(out, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join("  <url><loc>"+u+"</loc></url>\n" for u in urls) + "</urlset>\n")
import email.utils as EU, datetime as DT
pub = EU.format_datetime(DT.datetime(2026,10,28,9,0,tzinfo=DT.timezone.utc))
items = "".join(
  "<item><title>"+H.escape(b["name"]+": "+b["title"])+"</title><link>"+SITE+"/"+b["id"]+"</link><guid>"+SITE+"/"+b["id"]+"</guid>"
  "<pubDate>"+pub+"</pubDate><description>"+H.escape(short(first_para(b), 300))+"</description>"
  + ('<enclosure url="'+SITE+paths[b["img"]]+'" type="image/jpeg" length="0"/>' if b.get("img") in paths and paths[b["img"]].endswith(".jpg") else "")
  + "</item>\n" for b in data)
open(os.path.join(out, "feed.xml"), "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n<title>20 Blok</title><link>'+SITE+'/</link><description>Culture, creativity, and the internet. Twenty stories every issue by Lenny Lesser.</description><language>en-us</language>\n<atom:link href="'+SITE+'/feed.xml" rel="self" type="application/rss+xml"/>\n'+items+'</channel></rss>\n')
open(os.path.join(out, "robots.txt"), "w").write("User-agent: *\nAllow: /\nSitemap: https://20blok.com/sitemap.xml\n")
open(os.path.join(out, "vercel.json"), "w").write(json.dumps({"cleanUrls": True, "headers": [{"source": "/media/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}]}, indent=2))
print("built", out, "media files:", len(paths))
