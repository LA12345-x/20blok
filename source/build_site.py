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

# share image per issue: a new file name each issue, so link previews never show an old cover
ISSUE_NO = int(re.search(r"const ISSUE = (\d+);", t).group(1))
COVER = "/media/cover-i%d.jpg" % ISSUE_NO   # for issue pages (coming with Issue 8)
BRAND = "/media/share_brand.png"             # 20 BLOK card: home and general pages
if "cover" in paths:
    import shutil; shutil.copyfile(os.path.join(out, paths["cover"].lstrip("/")), os.path.join(out, COVER.lstrip("/")))
# ---------- page head: real document ----------
R('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
t = t.replace('<title>20 Blok</title>', '''<title>20 Blok — Culture, creativity, and the internet.</title>
<meta name="description" content="20 Blok by Lenny Lesser: twenty stories every issue on culture, creativity and the internet. You pick the winners.">
<meta property="og:title" content="20 Blok">
<meta property="og:description" content="Culture, creativity, and the internet. Twenty stories every issue. You pick the winners.">
<meta property="og:image" content="https://20blok.com''' + BRAND + '''">
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
let sb = null, sbReadyResolve = null;
const sbReady = new Promise(r => { sbReadyResolve = r; });
async function loadVotes(){
  if (!sb) return;
  const { data, error } = await sb.from("votes").select("blok,voter").eq("issue", ISSUE).limit(100000);
  if (error) return;
  shared = true; const t = {}, m = {};
  data.forEach(v => { t[v.blok] = (t[v.blok]||0) + 1; if (v.voter === uid) m[v.blok] = 1; });
  tallies = t; mine = m; refresh();
}
async function connect(){
  if (!window.supabase || SB_URL.startsWith("__")){ sbReadyResolve(); return; }
  try{
    sb = window.supabase.createClient(SB_URL, SB_KEY);
    let { data:{ session } } = await sb.auth.getSession();
    if (!session){ const r = await sb.auth.signInAnonymously(); session = r.data && r.data.session; }
    if (!session){ sbReadyResolve(); return; }
    uid = session.user.id;
    sbReadyResolve();
    await loadVotes();
    sb.channel("votes-"+ISSUE).on("postgres_changes", {event:"*", schema:"public", table:"votes", filter:"issue=eq."+ISSUE}, () => loadVotes()).subscribe();
    document.addEventListener("visibilitychange", () => { if (!document.hidden) loadVotes(); });
  }catch(e){ sbReadyResolve(); }
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
t = t[:s] + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.js")).read() + t[e:]
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
               ('href:"#this-week"','href:"/"'),('href:"#issue-notes"','href:"/issue-notes"'),('href:"#must-see"','href:"/issue-%d/must-see"' % ISSUE_NO),('href:"#straight-up"','href:"/straight-up"'),
               ('href:"#"+','href:"/"+'),('location.hash = b.id','go(b.id)'),('x.href.startsWith("#")','x.href.startsWith("/")')]:
    assert a_ in t, a_; t = t.replace(a_, b_)
R('function curRoute(){ return (location.hash||"").replace(/^#/,"") || "this-week"; }', '''function isAuthHash(h){ return /(^|&)(access_token|refresh_token|error|error_code|error_description|type)=/.test(h); }
function curRoute(){
  const p = location.pathname.replace(/^\\/+|\\/+$/g,"");
  if (!p){ const h=(location.hash||"").replace(/^#/,""); if (h && !isAuthHash(h)) return h; }
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
(function(){ const h=(location.hash||"").replace(/^#/,""); if (h && !isAuthHash(h) && (location.pathname==="/"||location.pathname==="")) history.replaceState({}, "", "/"+(h==="this-week"?"":h)); })();''')
R('  const h = (location.hash||"").replace(/^#/,"") || "this-week";', '  const h = curRoute();')
R('  else if (commentsUnsub){', '  document.title = blok ? (blok.seo_title||blok.title+" — 20 Blok") : (TITLES[h] ? TITLES[h]+" — 20 Blok" : "20 Blok — Culture, creativity, and the internet.");\n  setTimeout(hydrateEmbeds,0);\n  if (false){}\n  else if (commentsUnsub){')
R('window.addEventListener("hashchange", ()=>render(false));', 'window.addEventListener("hashchange", ()=>{ const h=(location.hash||"").replace(/^#/,""); if (h && isAuthHash(h)) return; if (h) history.replaceState({}, "", "/"+(h==="this-week"?"":h)); render(false); });')
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
  const sec = el("section",{class:"subscribe-band",id:"subscribe-band","aria-labelledby":"sb-head"},
    el("div",{}, el("h2",{id:"sb-head",text:"Get the next issue"}), el("p",{text:"New stories every issue, straight to your inbox. Free."})),
    form, msg);
  if (!subscribeBox.open) checkSubscribed().then(em=>{ if (!em || !sec.isConnected) return;
    const known = el("section",{class:"subscribe-band sb-known",id:"subscribe-band"},
      el("p",{}, el("b",{text:"You\u2019re on the list"}), " as "+em+". New issues land in your inbox. ",
        el("button",{type:"button",class:"c-link",text:"Subscribe a different email",onclick:()=>{ subscribeBox.open=true; const n=subscribeBox(); known.replaceWith(n); const i=n.querySelector("input"); if(i) i.focus(); }})));
    sec.replaceWith(known); });
  return sec;
}
let subCheck = null;
function checkSubscribed(){
  if (subCheck) return subCheck;
  subCheck = (async()=>{ try{ await sbReady; if (!sb) return null;
    const { data:{ session } } = await sb.auth.getSession(); const u = session && session.user; if (!u || u.is_anonymous) return null;
    const r = await fetch("/api/subscribe",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+session.access_token},body:JSON.stringify({check:true})});
    const j = await r.json().catch(()=>({})); return (j.known && j.active) ? (j.email||u.email) : null; }catch(e){ return null; } })();
  return subCheck;
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
R('    upNext(idx),', '    subscribeBox(),\n    upNext(idx),')
R('  document.getElementById("view").replaceChildren(...kids);', '  const hasBand = kids.some(k=>k && k.nodeType===1 && (k.id==="subscribe-band" || k.querySelector("#subscribe-band")));\n  const extra = (!hasBand && h!=="welcome") ? [el("div",{class:"article",style:"margin-top:32px"}, subscribeBox())] : [];\n  document.getElementById("view").replaceChildren(...kids, ...extra);')
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
      P("20 Blok is a free magazine by Lenny Lesser. This page explains what the site collects and why. Last updated November 1, 2026."),
      el("h3",{text:"Email"}),
      P("If you subscribe, your email address goes to Beehiiv, the service that sends the newsletter. It's used only to send you new issues and newsletter updates. You can unsubscribe from any email."),
      el("h3",{text:"Votes"}),
      P("Uprating a blok doesn't ask for your name or email. Your browser gets an anonymous ID so each person counts once. Votes are stored with Supabase, which hosts the site's database."),
      el("h3",{text:"Comments"}),
      P("To comment, you confirm your email, either with Google sign-in or with a one-time link sent to your inbox (sent through Resend). Your sign-in is handled by Supabase. Commenting subscribes you to the 20 Blok newsletter, which you can leave any time. Your comment and the name you choose are shown publicly; your email is never shown."),
      el("h3",{text:"Feedback and contact"}),
      P("The feedback box and the contact page send what you write, plus your name and email if you give them, to Lenny. Messages are stored with Supabase and emailed to Lenny through Resend. They're never published."),
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
  const btn = el("button",{type:"button",class:"sh-btn","aria-haspopup":"true","aria-expanded":"false",onclick:e=>{ e.stopPropagation(); const open=menu.hidden; document.querySelectorAll(".sh-menu").forEach(m=>m.hidden=true); menu.hidden=!open; btn.setAttribute("aria-expanded",String(open)); if (open) requestAnimationFrame(()=>{ const r=menu.getBoundingClientRect(); if (r.bottom>innerHeight-12) scrollBy({top:r.bottom-innerHeight+24,behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"}); }); }},
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

# ---------- feedback box + contact page ----------
R('function ytId(u){', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox.js")).read() + 'function ytId(u){')
R('el("a",{class:"fb-btn",href:SURVEY,target:"_blank",rel:"noopener"},"Take the quick survey →")),', 'el("a",{class:"fb-btn",href:"/feedback"},"Share your feedback →")),')
R('<a href="https://docs.google.com/forms/d/e/1FAIpQLSedWziqsIQfv9bfBojwvFmpzItweprLQQ5XhsjvmwnBg62P3w/viewform" target="_blank" rel="noopener">Feedback</a>', '<a href="/contact">Contact</a> · <a href="/feed.xml" target="_blank" rel="noopener" title="Follow 20 Blok in a feed reader (Feedly, Inoreader, NetNewsWire)">RSS</a>')
R('h==="welcome" ? welcomeView() : gridView(false);', 'h==="welcome" ? welcomeView() : h==="contact" ? contactView() : h==="feedback" ? feedbackView() : gridView(false);')
R('const TITLES = {"welcome":"Welcome",', 'const TITLES = {"feedback":"Feedback","contact":"Contact","welcome":"Welcome",')
R('sec("Work with me",', 'sec("Work with me",\n        el("p",{},"Collaborations, interviews, writing for 20 Blok, brands → ", el("a",{href:"/contact",text:"use the contact form →"})),')

SUB_CSS = '''.fb-form{display:grid;gap:14px;margin:8px 0 20px}
.fb-q{margin:0;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);font-family:var(--sans)}
.fb-chips{display:flex;flex-wrap:wrap;gap:8px}
.fb-chip{min-height:42px;padding:0 16px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--fg);font:600 14px var(--sans);cursor:pointer}
.fb-chip[aria-pressed="true"]{border-color:var(--red);background:var(--red-deep);color:#fff}
.fb-blok{min-height:38px;padding:0 12px;font-size:12px;letter-spacing:.06em}
.fb-form textarea,.fb-form input[type=email]{width:100%;box-sizing:border-box;min-height:46px;padding:10px 14px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--fg);font:16px/1.5 var(--sans)}
.fb-form textarea{min-height:120px;resize:vertical}
.fb-check{display:flex;align-items:center;gap:8px;font:15px var(--sans);color:var(--fg-soft);cursor:pointer}
.fb-check input{width:18px;height:18px;accent-color:var(--red)}
.fb-row{display:flex;flex-wrap:wrap;align-items:center;gap:12px}
.fb-row .fb-btn{border:0;cursor:pointer}
.fb-msg{margin:0;font-size:14px}.fb-msg:empty{display:none}
.fb-fine{margin:-4px 0 0;font:13px var(--sans);color:var(--muted)}
.fb-done{margin:0;font-weight:700;font-size:17px}
.ct-form{display:grid;gap:14px;margin:8px 0 20px}
.ct-field{display:grid;gap:6px}
.ct-field label{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted)}
.ct-field input,.ct-field select,.ct-field textarea{width:100%;box-sizing:border-box;min-height:46px;padding:10px 14px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--fg);font:16px/1.5 var(--sans)}
.ct-field textarea{min-height:140px;resize:vertical}
.fb-form .fb-msg,.ct-form .fb-msg{color:var(--fg-soft);font-family:var(--sans)}
.ct-alt{color:var(--muted);font-size:14px}.ct-alt b{color:var(--fg)}
.c-form input[type=text]{width:100%;box-sizing:border-box;min-height:44px;padding:0 14px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--fg);font:16px var(--sans)}
.c-actions{flex-wrap:wrap}
.c-who{flex:1 1 220px;font-size:13px;color:var(--muted)}.c-who b{color:var(--fg)}
.c-link{border:0;background:none;padding:0;color:var(--muted);text-decoration:underline;font:inherit;cursor:pointer}
.c-status:empty{display:none}
.c-tools{margin-left:auto;display:flex;gap:6px}
.c-del.armed{border-color:var(--red);color:var(--red)}
.c-meta .c-tools .c-del{margin-left:0}
#c-gate{margin-top:4px}
.c-gate-box{display:grid;gap:12px;padding:20px;border-radius:16px;background:var(--panel);border:1px solid var(--red-deep)}
.c-gate-box h3{margin:0;font-family:var(--display);font-weight:900;font-size:24px}
.c-gate-sub{margin:-6px 0 0;color:var(--fg-soft);font-size:15px}
.c-google{display:inline-flex;align-items:center;justify-content:center;gap:10px;min-height:46px;padding:0 18px;border-radius:999px;border:0;background:#fff;color:#1f1f1f;font:600 15px var(--sans);cursor:pointer}
.c-google svg{width:20px;height:20px}
.c-or{display:flex;align-items:center;gap:10px;color:var(--muted);font-size:13px}.c-or::before,.c-or::after{content:"";flex:1;height:1px;background:var(--line)}
.c-email{display:flex;flex-wrap:wrap;gap:8px}
.c-email input{flex:1 1 200px;min-width:0;min-height:46px;padding:0 14px;border-radius:12px;border:1px solid var(--line);background:#0B0B0C;color:var(--fg);font-size:16px}
.c-fine{margin:0;font-size:12px;color:var(--muted)}
.c-namebox{display:grid;gap:6px}
.c-gmsg{margin:0;font-size:14px;color:var(--fg-soft)}.c-gmsg:empty{display:none}
.tile.top{border:1px solid var(--fg);box-shadow:0 0 0 1px var(--fg),0 6px 0 #000,0 18px 30px rgba(0,0,0,.45)}
.rank-top{position:relative;display:inline-block;width:1.2em;height:.84em;color:#fff}
.rank-top::before{content:"";position:absolute;left:50%;top:50%;width:1.75em;height:1.75em;transform:translate(-50%,-50%) rotate(-8deg);background:var(--red);clip-path:polygon(50% 0%,61% 11%,75% 7%,79% 21%,93% 25%,89% 39%,100% 50%,89% 61%,93% 75%,79% 79%,75% 93%,61% 89%,50% 100%,39% 89%,25% 93%,21% 79%,7% 75%,11% 61%,0% 50%,11% 39%,7% 25%,21% 21%,25% 7%,39% 11%)}
.rank-top .rt-num{position:absolute;left:-.3em;right:-.3em;top:50%;transform:translateY(-74%);text-align:center;font-size:.72em;line-height:1}
.rank-top .rt-tag{position:absolute;left:50%;top:50%;transform:translate(-50%,calc(.5em + 2px));font-family:var(--sans,inherit);font-weight:900;font-size:.2em;letter-spacing:.06em;white-space:nowrap}
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
.sb-known{padding:16px 20px!important}.sb-known p{color:var(--fg-soft)}.sb-known b{color:var(--fg)}
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

# ---------- back issues (backfill): 20blok.com/issue-6, /issue-6/<blok>, /issue-6/notes ----------
import glob, shutil
ARCH = {}
for f in sorted(glob.glob(os.path.join(HERE, "issues", "*.json"))):
    a = json.load(open(f, encoding="utf-8")); n = a["n"]
    if n == ISSUE_NO: continue
    mdir = os.path.join(HERE, "archive", "i%d" % n)
    os.makedirs(os.path.join(out, "media", "i%d" % n), exist_ok=True)
    for mf in sorted(os.listdir(mdir)):
        shutil.copyfile(os.path.join(mdir, mf), os.path.join(out, "media", "i%d" % n, mf))
        paths["i%d_%s" % (n, os.path.splitext(mf)[0])] = "/media/i%d/%s" % (n, mf)
    for b in a["bloks"]:
        b["slug"] = b["id"]; b["id"] = "issue-%d/%s" % (n, b["id"])
        b.setdefault("links", []); b.setdefault("media", "")
    a["coverlines"] = ["issue-%d/%s" % (n, c) for c in a["coverlines"]]
    a["covertext"] = {"issue-%d/%s" % (n, k): v for k, v in a["covertext"].items()}
    ARCH[n] = a
R('const BLOKS = __DATA__;', 'const CURRENT = __DATA__;\nlet BLOKS = CURRENT;')
R('const ISSUE = %d;' % ISSUE_NO, '''const ISSUE = %d;
let CUR = ISSUE;
const ARCHIVE = __ARCHIVE__;
const CUR_META = {n:ISSUE, title:"Retail Mindset", month:"October 2026", cover:"cover", cover_alt:"Issue 7 cover: Retail Mindset. Shoppers push carts down aisles stocked with headlines, charts and opinions. Are your opinions actually yours?"};
function meta(){ return ARCHIVE[CUR] || CUR_META; }
function idParts(id){ const m=/^issue-(\\d+)\\/(.+)$/.exec(id); return m ? [+m[1], m[2]] : [ISSUE, id]; }
function vkey(i, b){ return "issue-"+i+"/"+b; }
function normRoute(h){ if (h==="issue-"+ISSUE) return "this-week"; if (!/\\//.test(h) && CURRENT.some(b=>b.id==="issue-"+ISSUE+"/"+h)) return "issue-"+ISSUE+"/"+h; return h; }
function setIssueFor(h){ const m=/^issue-(\\d+)(?:\\/|$)/.exec(h); if (m && ARCHIVE[+m[1]]){ CUR=+m[1]; BLOKS=ARCHIVE[CUR].bloks; } else { CUR=ISSUE; BLOKS=CURRENT; } }
function gridHome(){ return CUR===ISSUE ? "/" : "/issue-"+CUR; }
function notesHref(){ return CUR===ISSUE ? "/issue-notes" : "/issue-"+CUR+"/notes"; }
let ALL_N = 20;
function allRanked(){
  const all = [...CURRENT.map((b,i)=>({...b,iss:ISSUE,i}))];
  Object.values(ARCHIVE).forEach(a => a.bloks.forEach((b,i)=>all.push({...b,iss:a.n,i})));
  return all.map(b=>({...b,score:tallies[b.id]||0})).sort((a,b)=>(b.score-a.score)||(b.iss-a.iss)||(a.i-b.i));
}''' % ISSUE_NO)
# votes: every issue stays open; keys are "must-see" (current) or "issue-6/must-see"
R('.select("blok,voter").eq("issue", ISSUE).limit(100000);', '.select("issue,blok,voter").limit(100000);')
R('data.forEach(v => { t[v.blok] = (t[v.blok]||0) + 1; if (v.voter === uid) m[v.blok] = 1; });',
  'data.forEach(v => { const k = vkey(v.issue, v.blok); t[k] = (t[k]||0) + 1; if (v.voter === uid) m[k] = 1; });')
R('sb.channel("votes-"+ISSUE).on("postgres_changes", {event:"*", schema:"public", table:"votes", filter:"issue=eq."+ISSUE}',
  'sb.channel("votes-all").on("postgres_changes", {event:"*", schema:"public", table:"votes"}')
R('insert({issue:ISSUE, blok:id, voter:uid})', 'insert({issue:idParts(id)[0], blok:idParts(id)[1], voter:uid})')
R('match({issue:ISSUE, blok:id, voter:uid})', 'match({issue:idParts(id)[0], blok:idParts(id)[1], voter:uid})')
# routing
R('function curRoute(){\n  const p', 'function curRoute(){ return normRoute(rawRoute()); }\nfunction rawRoute(){\n  const p')
R('  const h = curRoute();\n  const blok = BLOKS.find(b=>b.id===h);', '  const h = curRoute(); setIssueFor(h);\n  const blok = BLOKS.find(b=>b.id===h);')
R('h==="past-issues" ? pastView() :', 'h==="past-issues" ? pastView() : (/^issue-\\d+$/.test(h) && ARCHIVE[CUR]) ? gridView(false) : (/^issue-\\d+\\/notes$/.test(h) && ARCHIVE[CUR]) ? archNotesView() :')
R('const active = blok ? null :', 'const active = (CUR!==ISSUE) ? "past-issues" : blok ? null :')
R('  setTimeout(hydrateEmbeds,0);', '  if (CUR!==ISSUE && !blok) document.title = "Issue "+CUR+": "+meta().title+" | 20 Blok";\n  setTimeout(hydrateEmbeds,0);')
# grid + all-time
R('el("span",{class:"label",text:(all?"ISSUE 7 · ":"")+b.name})', 'el("span",{class:"label",text:(all?"ISSUE "+idParts(b.id)[0]+" · ":"")+b.name})')
R('  const list = ranked();\n  const grid = el("ol",{class:"grid","aria-label": all?"All-time ranking":"This week’s bloks, ranked"}, list.map((b,r)=>tileFor(b,r,all)));',
  '  const list = all ? allRanked() : ranked();\n  const grid = el("ol",{class:"grid","aria-label": all?"All-time ranking":"Issue "+CUR+" bloks, ranked"}, (all?list.slice(0,ALL_N):list).map((b,r)=>tileFor(b,r,all)));')
R('el("p",{text:"The most uprated pieces across every issue. Issue 7 is the first one counted."})), grid];',
  'el("p",{text:"The most uprated bloks from every issue, in one list. Every issue stays open for uprating."})), grid,\n      list.length>ALL_N ? el("div",{class:"more-wrap"}, el("button",{type:"button",class:"sb-btn more-btn",onclick:()=>{ ALL_N+=20; render(false); }},"Show more")) : null];')
R('el("p",{text:"Issue 7 · October 2026 · Edited by Lenny Lesser"}), el("p",{class:"tag",text:"Retail Mindset"})',
  'el("p",{text:"Issue "+CUR+" · "+meta().month+" · Edited by Lenny Lesser"}), el("p",{class:"tag",text:meta().title})')
R('el("a",{href:"/straight-up","aria-label":"Read Retail Mindset, the editor’s letter",style:"display:block"}, el("img",{src:IMG.cover,alt:"Issue 7 cover: Retail Mindset. Shoppers push carts down aisles stocked with headlines, charts and opinions. Are your opinions actually yours?"}))',
  'el("a",{href:"/issue-"+CUR+"/straight-up","aria-label":"Read "+meta().title+", the editor’s letter",style:"display:block"}, el("img",{src:IMG[meta().cover],alt:meta().cover_alt}))')
R('COVERLINES.map(id=> el("li",{}, el("a",{href:"/"+id}, el("span",{text:byId[id].name}), el("b",{text:COVERTEXT[id]}))))',
  '(ARCHIVE[CUR]?ARCHIVE[CUR].coverlines:COVERLINES.map(x=>"issue-"+ISSUE+"/"+x)).map(id=> el("li",{}, el("a",{href:"/"+id}, el("span",{text:byId[id].name}), el("b",{text:ARCHIVE[CUR]?ARCHIVE[CUR].covertext[id]:COVERTEXT[idParts(id)[1]]}))))')
R('    el("a",{class:"notes-link",href:"/issue-notes"}', '    el("a",{class:"notes-link",href:notesHref()}')
R('    el("div",{class:"section-head"}, el("h2",{text:"The Grid"}),', '''    CUR===ISSUE ? el("a",{class:"past-tease",href:"/past-issues"}, el("span",{class:"pt-thumbs","aria-hidden":"true"}, PAST.filter(p=>!p.here).slice(0,3).map(p=>el("img",{src:IMG[p.img],alt:"",loading:"lazy"}))), el("span",{class:"pt-copy"}, el("b",{text:"Looking for past issues?"}), " Browse every issue \u2192")) : null,
    el("div",{class:"section-head"}, el("h2",{text:"The Grid"}),''')
R('.issue-thumb{', '''.past-tease{display:flex;align-items:center;gap:14px;margin:18px 0 0;padding:10px 14px;border-radius:12px;border:1px solid var(--line);color:var(--fg-soft);text-decoration:none;font-size:14px;width:fit-content;max-width:100%;box-sizing:border-box}
.past-tease b{color:var(--fg)}
.past-tease:hover{border-color:var(--fg);color:var(--fg)}
.pt-thumbs{display:flex;flex:0 0 auto}
.pt-thumbs img{width:34px;height:34px;object-fit:cover;border-radius:7px;border:2px solid var(--bg,#0B0B0C);margin-left:-10px}
.pt-thumbs img:first-child{margin-left:0}
.issue-thumb{''')
R('el("b",{text:"Issue notes: what changed, the bonus pick and the sign-off →"})', 'el("b",{text:(ARCHIVE[CUR]&&ARCHIVE[CUR].notes.link_text)||"Issue notes: what changed, the bonus pick and the sign-off →"})')
# article
t = t.replace('el("a",{class:"back",href:"/",text:"← BACK TO THE GRID"})', 'el("a",{class:"back",href:gridHome(),text:"← BACK TO THE GRID"})')
R('" · Issue 7 · "+readTime(b)', '" · Issue "+CUR+" · "+readTime(b)')
R('el("img",{src:IMG.cover,alt:"Issue 7 cover: Retail Mindset."})', 'el("img",{src:IMG[meta().cover],alt:meta().cover_alt})')
# past issues
R('{n:6,t:"Do you have what it takes to be early?",d:"Apr 24, 2026",img:"issue6",', '{n:6,t:"Do You Have What It Takes to Be Early?",d:"Apr 24, 2026",img:"i6_cover",path:"/issue-6",')
R('p.here?{href:"/"}:', 'p.path?{href:p.path}:p.here?{href:"/"}:')
R('{n:7,t:"Retail Mindset",d:"Oct 28, 2026",here:true,', '{n:7,t:"Retail Mindset",d:"Oct 28, 2026",here:true,path:"/issue-7",')
R('p.d+(p.here?" · on this site":" · on the newsletter")', 'p.d+((p.here||p.path)?" · on this site":" · on the newsletter")')
R('"Issues 1 through 6 live on the newsletter. Tap a cover to read it. Issue 7 is the first one built as 20 Blok."',
  '"Every issue, newest first. Tap a cover to read it. Issues 1 through 5 still live on the newsletter while they move over."')
ARCH_JS = '''function archNotesView(){
  const a = ARCHIVE[CUR], N = a.notes;
  const sec=(h,...k)=>el("section",{class:"note"}, el("h3",{text:h}), ...k);
  return [el("article",{class:"article"},
    el("a",{class:"back",href:gridHome(),text:"← BACK TO THE GRID"}),
    el("div",{class:"art-head"}, el("span",{class:"art-label",text:"ISSUE "+CUR+" · THE BACK PAGE"}), el("h1",{text:"Issue Notes"}),
      el("p",{class:"art-dek",text:"The sign-off, the editor’s notes and the treasure hunt answer."})),
    el("div",{class:"prose notes"},
      sec("Sign-off", el("p",{text:N.signoff}), el("p",{class:"sign",text:"— Lenny"})),
      N.treasure ? el("section",{class:"note",id:"treasure"}, el("h3",{text:"🗺️ Treasure Hunt"}),
        el("p",{text:N.treasure.text}),
        N.treasure.gif ? figure({src:N.treasure.gif,cap:"",alt:"The 9mm Shigure Ui meme",gif:true}) : null,
        el("p",{}, el("a",{href:N.treasure.link.href,target:"_blank",rel:"noopener",text:N.treasure.link.label})),
        el("p",{}, el("a",{href:N.treasure.back.href,text:N.treasure.back.label}))) : null,
      N.editor_notes ? sec("📝 Editor notes", el("p",{text:N.editor_notes})) : null,
      sec("Work with me",
        el("p",{},"Need video ads for your brand or business? ", el("a",{href:"https://unrulyreels.com",target:"_blank",rel:"noopener",text:"UnrulyReels.com →"})),
        el("p",{},"Collaborations, interviews, writing for 20 Blok, brands → ", el("a",{href:"/contact",text:"use the contact form →"}))),
      sec("⚡️ Alpha close", el("p",{class:"pull",text:N.alpha}))))];
}
'''
R('function ytId(u){', ARCH_JS + 'function ytId(u){')
R('.fig.embed .embed-frame{', '.more-wrap{display:flex;justify-content:center;margin:28px 0 8px}\n.fig.embed .embed-frame{')

# ---------- header switch: THIS WEEK / ALL-TIME slides like a real switch (tap or drag) ----------
R('<div class="seg"><a ', '<div class="seg"><span class="seg-thumb" aria-hidden="true"></span><a ')
R('.seg a[aria-current="page"]{background:var(--fg);color:var(--ink)}', """.seg{position:relative;touch-action:pan-y;-webkit-user-select:none;user-select:none}
.seg a{position:relative;z-index:1;transition:color .28s ease;-webkit-user-drag:none}
.seg a[aria-current="page"]{color:var(--ink)}
.seg-thumb{position:absolute;z-index:0;top:3px;bottom:3px;left:0;width:0;border-radius:999px;background:var(--fg);box-shadow:0 2px 8px rgba(0,0,0,.35);transition:transform .32s cubic-bezier(.3,1.25,.5,1),width .32s cubic-bezier(.3,1.25,.5,1),opacity .2s ease;opacity:0;cursor:grab}
.seg-thumb.on{opacity:1}
.seg.dragging .seg-thumb{transition:none;cursor:grabbing}
@media (max-width:640px){.seg-thumb{top:2px;bottom:2px}}
@media (prefers-reduced-motion:reduce){.seg-thumb{transition:opacity .2s ease}}""")
R('  document.querySelectorAll("[data-route]").forEach(a=> a.dataset.route===active ? a.setAttribute("aria-current","page") : a.removeAttribute("aria-current"));',
  '  document.querySelectorAll("[data-route]").forEach(a=> a.dataset.route===active ? a.setAttribute("aria-current","page") : a.removeAttribute("aria-current"));\n  segThumb();')
SEG_JS = """function segThumb(){
  const seg=document.querySelector(".seg"), th=seg&&seg.querySelector(".seg-thumb"); if(!th) return;
  const cur=seg.querySelector('a[aria-current="page"]');
  if(!cur){ th.classList.remove("on"); return; }
  th.style.width=cur.offsetWidth+"px"; th.style.transform="translateX("+cur.offsetLeft+"px)"; th.classList.add("on");
  if(!th.dataset.ready){ th.style.transition="none"; th.offsetWidth; th.style.transition=""; th.dataset.ready="1"; }
}
(function(){
  const seg=document.querySelector(".seg"); if(!seg) return;
  const th=seg.querySelector(".seg-thumb"), links=[...seg.querySelectorAll("a")];
  let start=null, moved=false, base=0;
  seg.addEventListener("pointerdown",e=>{ if(e.button!==0||!th.classList.contains("on")) return;
    const r=th.getBoundingClientRect(); if(e.clientX<r.left||e.clientX>r.right) return;
    start=e.clientX; moved=false; base=new DOMMatrixReadOnly(getComputedStyle(th).transform).m41; seg.setPointerCapture(e.pointerId); });
  seg.addEventListener("pointermove",e=>{ if(start===null) return; const dx=e.clientX-start; if(Math.abs(dx)>4){ moved=true; seg.classList.add("dragging"); }
    if(!moved) return; const max=links[links.length-1].offsetLeft, min=links[0].offsetLeft;
    const x=Math.max(min,Math.min(max,base+dx)); th.style.transform="translateX("+x+"px)";
    const near=links.reduce((a,l)=>Math.abs(l.offsetLeft-x)<Math.abs(a.offsetLeft-x)?l:a); th.style.width=near.offsetWidth+"px"; });
  const end=e=>{ if(start===null) return; seg.classList.remove("dragging");
    if(moved){ const x=new DOMMatrixReadOnly(getComputedStyle(th).transform).m41;
      const near=links.reduce((a,l)=>Math.abs(l.offsetLeft-x)<Math.abs(a.offsetLeft-x)?l:a);
      if(near.getAttribute("aria-current")!=="page") go(near.getAttribute("href").replace(/^\/+|\/+$/g,"")||"this-week"); else segThumb();
      const stop=ev=>{ ev.preventDefault(); ev.stopPropagation(); seg.removeEventListener("click",stop,true); }; seg.addEventListener("click",stop,true); setTimeout(()=>seg.removeEventListener("click",stop,true),0); }
    start=null; };
  seg.addEventListener("pointerup",end); seg.addEventListener("pointercancel",end);
  seg.addEventListener("dragstart",e=>e.preventDefault());
  window.addEventListener("resize",segThumb);
  document.fonts && document.fonts.ready.then(segThumb);
})();
"""
R('let lastRoute = null;', SEG_JS + 'let lastRoute = null;')

R('<a href="/issue-notes">Issue notes</a>', '<a href="/issue-notes">Issue %d notes</a>' % ISSUE_NO)
# ---------- write ----------
for b in data:
    for x in b["body"]:
        if x.get("t")=="link" and x.get("href","").startswith("#"): x["href"] = "/" + x["href"][1:]
def _seo_title(b):
    who = next((p for p in b.get("people", []) if p and p.lower() not in b["title"].lower() and p.split()[0].lower() not in b["title"].lower()), None)
    return b["title"] + (" — " + who if who else "") + " | 20 Blok"
for b in data: b["seo_title"] = _seo_title(b)
for a_ in ARCH.values():
    for b in a_["bloks"]: b["seo_title"] = _seo_title(b)
for b in data:
    b["slug"] = b["id"]; b["id"] = "issue-%d/%s" % (ISSUE_NO, b["id"])
dd = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
t = t.replace('__DATA__', dd).replace('__IMAGES__', json.dumps(paths)).replace('__ARCHIVE__', json.dumps({str(k): v for k, v in ARCH.items()}, ensure_ascii=False).replace('</', '<\\/'))
t = t.replace('https://unruly-reels-apqmcno.gamma.site/', 'https://unrulyreels.com')
import html as H, datetime as DT0
SITE = "https://20blok.com"
def page(route, title, desc, img, body_html, og_title=None, canonical=None):
    p = t
    p = p.replace("<title>20 Blok — Culture, creativity, and the internet.</title>", "<title>"+H.escape(title)+"</title>", 1)
    p = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="'+H.escape(desc)+'">', p, 1)
    p = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="'+H.escape(og_title or title)+'">', p, 1)
    p = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="'+H.escape(desc)+'">', p, 1)
    p = re.sub(r'<meta property="og:image" content="[^"]*">', '<meta property="og:image" content="'+SITE+img+'">', p, 1)
    url = SITE + ("/" if route=="" else "/"+route)
    cu = url if canonical is None else SITE + "/" + canonical
    p = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="'+cu+'">\n<link rel="canonical" href="'+cu+'">', p, 1)
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
ISSUE_TITLE = next((b["title"] for b in data if b["slug"]=="straight-up"), "")
urls.append(page("", "20 Blok — Culture, creativity, and the internet.", home_desc, BRAND, '<h1>20 Blok, Issue %d: %s</h1><ul>' % (ISSUE_NO, H.escape(ISSUE_TITLE))+grid+'</ul>',
                 og_title="20 Blok · Issue %d: %s" % (ISSUE_NO, ISSUE_TITLE)))
def full_text(b):
    o = []
    for x in b["body"]:
        k = x.get("t")
        if k in ("p","q","pull","cite","cap"): o.append("<p>"+txt(x)+"</p>")
        elif k == "h": o.append("<h2>"+txt(x)+"</h2>")
        elif k == "ul": o.append("<ul>"+"".join("<li>"+H.escape(i)+"</li>" for i in x["items"])+"</ul>")
        elif k == "link": o.append('<p><a href="'+H.escape(x["href"])+'">'+H.escape(x["label"])+'</a></p>')
        elif k in ("img","clip","loop") and (x.get("cap") or x.get("alt")):
            o.append("<figure><figcaption>"+H.escape(x.get("cap") or x.get("alt"))+"</figcaption></figure>")
    for l in b.get("links", []): o.append('<p><a href="'+H.escape(l["href"])+'">'+H.escape(l["label"])+'</a></p>')
    return "".join(o)
def article_ld(b, url, n, date, img):
    ld = {"@context":"https://schema.org","@type":"Article","headline":b["title"],"author":{"@type":"Person","name":"Lenny Lesser","url":"https://lennylesser.com"},
          "publisher":{"@type":"Organization","name":"20 Blok","url":SITE},"datePublished":date,"image":SITE+img,"mainEntityOfPage":url,
          "isPartOf":{"@type":"PublicationIssue","issueNumber":str(n),"isPartOf":{"@type":"Periodical","name":"20 Blok"}},
          "keywords":", ".join(b.get("tags",[])+b.get("people",[]))}
    return '<script type="application/ld+json">'+json.dumps(ld, ensure_ascii=False).replace("</","<\\/")+'</script>'
def seo_desc(b):
    fp = first_para(b); dk = (b.get("dek") or "").strip()
    if dk and fp and dk.rstrip(".") not in fp: d = dk.rstrip(".") + ". " + fp
    else: d = fp or dk
    return short(d) or home_desc
def blok_page(route, b, n, date, canonical=None):
    img = paths.get(b.get("img") or "", BRAND) if b.get("img") else BRAND
    url = SITE+"/"+(canonical or route)
    return page(route, b["seo_title"], seo_desc(b), img,
                '<article><p>'+H.escape(b["name"])+' · Issue '+str(n)+'</p><h1>'+H.escape(b["title"])+'</h1>'+full_text(b)+'</article>'+article_ld(b, url, n, date, img), canonical=canonical)
for b in data:
    urls.append(blok_page(b["id"], b, ISSUE_NO, "2026-10-28"))
    old = os.path.join(out, b["slug"], "index.html")
    if os.path.exists(old): os.remove(old)
    try: os.rmdir(os.path.join(out, b["slug"]))
    except OSError: pass
REDIRECTS = [{"source": "/"+b["slug"], "destination": "/"+b["id"], "permanent": True} for b in data]
page("issue-%d" % ISSUE_NO, "20 Blok, Issue %d: %s" % (ISSUE_NO, ISSUE_TITLE), home_desc, BRAND, '<h1>20 Blok, Issue %d: %s</h1><ul>' % (ISSUE_NO, H.escape(ISSUE_TITLE))+grid+'</ul>', canonical="")
for n, a in sorted(ARCH.items()):
    g = "".join('<li><a href="/'+b["id"]+'">'+H.escape(b["name"])+': '+H.escape(b["title"])+'</a></li>' for b in a["bloks"])
    cov = paths.get(a["cover"], BRAND)
    urls.append(page("issue-%d" % n, "Issue %d: %s | 20 Blok" % (n, a["title"]), "20 Blok Issue %d (%s): %s %d stories on culture, creativity and the internet by Lenny Lesser, ranked by readers." % (n, a["date"], a["title"].rstrip(".")+("" if a["title"][-1] in "?!" else "."), len(a["bloks"])), cov,
                     '<h1>20 Blok, Issue %d: %s</h1><ul>' % (n, H.escape(a["title"]))+g+'</ul>'
                     + '<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"PublicationIssue","issueNumber":str(n),"name":a["title"],"datePublished":a["pub"],"image":SITE+cov,"url":SITE+"/issue-%d" % n,
                        "author":{"@type":"Person","name":"Lenny Lesser"},"isPartOf":{"@type":"Periodical","name":"20 Blok","url":SITE},
                        "hasPart":[{"@type":"Article","headline":b["title"],"url":SITE+"/"+b["id"]} for b in a["bloks"]]}, ensure_ascii=False).replace("</","<\\/")+'</script>'))
    for b in a["bloks"]:
        urls.append(blok_page(b["id"], b, n, a["pub"]))
    N = a["notes"]
    nt = "<h1>Issue %d Notes</h1><p>%s</p>" % (n, H.escape(N["signoff"]))
    if N.get("treasure"): nt += "<h2>Treasure Hunt</h2><p>%s</p>" % H.escape(N["treasure"]["text"])
    if N.get("editor_notes"): nt += "<h2>Editor notes</h2><p>%s</p>" % H.escape(N["editor_notes"])
    nt += "<h2>Alpha close</h2><p>%s</p>" % H.escape(N["alpha"])
    urls.append(page("issue-%d/notes" % n, "Issue %d Notes: the Back Page | 20 Blok" % n, "The Back Page of 20 Blok Issue %d (%s): the sign-off, the treasure hunt answer, editor notes and the Alpha Close: %s" % (n, a["title"], N["alpha"]), cov, nt))
for r_, ti in [("feedback","Feedback"),("contact","Contact"),("welcome","Welcome"),("privacy","Privacy"),("all-time","All-Time"),("past-issues","Past Issues"),("issue-notes","Issue Notes"),("bonus","Issue Notes")]:
    u = page(r_, ti+" — 20 Blok", home_desc, BRAND, "<h1>"+ti+"</h1>")
    if r_ not in ("bonus","welcome"): urls.append(u)
open(os.path.join(out, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join("  <url><loc>"+u+"</loc><lastmod>"+DT0.date.today().isoformat()+"</lastmod></url>\n" for u in urls) + "</urlset>\n")
import email.utils as EU, datetime as DT
pub = EU.format_datetime(DT.datetime(2026,10,28,9,0,tzinfo=DT.timezone.utc))
items = "".join(
  "<item><title>"+H.escape(b["name"]+": "+b["title"])+"</title><link>"+SITE+"/"+b["id"]+"</link><guid>"+SITE+"/"+b["id"]+"</guid>"
  "<pubDate>"+pub+"</pubDate><description>"+H.escape(short(first_para(b), 300))+"</description>"
  + ('<enclosure url="'+SITE+paths[b["img"]]+'" type="image/jpeg" length="0"/>' if b.get("img") in paths and paths[b["img"]].endswith(".jpg") else "")
  + "</item>\n" for b in data)
for n, a_ in sorted(ARCH.items(), reverse=True):
    pub_a = EU.format_datetime(DT.datetime.fromisoformat(a_["pub"]+"T09:00:00+00:00"))
    items += "".join("<item><title>"+H.escape(b["name"]+": "+b["title"])+"</title><link>"+SITE+"/"+b["id"]+"</link><guid>"+SITE+"/"+b["id"]+"</guid><pubDate>"+pub_a+"</pubDate><description>"+H.escape(short(b.get("dek") or first_para(b), 300))+"</description></item>\n" for b in a_["bloks"])
open(os.path.join(out, "feed.xml"), "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n<title>20 Blok</title><link>'+SITE+'/</link><description>Culture, creativity, and the internet. Twenty stories every issue by Lenny Lesser.</description><language>en-us</language>\n<atom:link href="'+SITE+'/feed.xml" rel="self" type="application/rss+xml"/>\n'+items+'</channel></rss>\n')
open(os.path.join(out, "robots.txt"), "w").write("User-agent: *\nAllow: /\nSitemap: https://20blok.com/sitemap.xml\n")
open(os.path.join(out, "vercel.json"), "w").write(json.dumps({"cleanUrls": True, "redirects": REDIRECTS, "headers": [{"source": "/media/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}]}, indent=2))
print("built", out, "media files:", len(paths))
