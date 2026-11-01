/* ---------- comments (Pass 2): verified subscribers only ---------- */
const ADMINS = ["soundsoflife@gmail.com", "lennybusinessnow@gmail.com"];
const cState = { blok: null, rows: [], me: null, admin: false, ch: null };
const cDraftKey = id => "blok20-draft-" + id;
function cName(u){ const m = (u && u.user_metadata) || {}; return String(m.display_name || "").trim().slice(0, 40); }
function cSuggest(u){ const m = (u && u.user_metadata) || {}; return String(m.given_name || String(m.full_name || m.name || "").split(" ")[0] || "").trim().slice(0, 40); }
async function cUser(){
  await sbReady; if (!sb) return null;
  try{ const { data:{ session } } = await sb.auth.getSession(); const u = session && session.user; return (u && !u.is_anonymous) ? u : null; }catch(e){ return null; }
}
function twoTap(btn, label, ask, fn){
  let armed = false, t = null;
  btn.textContent = label;
  btn.addEventListener("click", async () => {
    if (!armed){ armed = true; btn.textContent = ask; btn.classList.add("armed"); t = setTimeout(() => { armed = false; btn.textContent = label; btn.classList.remove("armed"); }, 4000); return; }
    clearTimeout(t); btn.disabled = true; await fn(); btn.disabled = false; armed = false; btn.textContent = label; btn.classList.remove("armed");
  });
  return btn;
}
function googleMark(){
  const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", "0 0 48 48"); s.setAttribute("aria-hidden", "true");
  [["#EA4335","M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z"],
   ["#4285F4","M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.7 6c4.5-4.2 6.9-10.3 6.9-17.7z"],
   ["#FBBC05","M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z"],
   ["#34A853","M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.7-6c-2.1 1.4-4.9 2.3-8.2 2.3-6.2 0-11.5-4.1-13.4-9.8l-7.9 6.1C6.6 42.6 14.6 48 24 48z"]]
  .forEach(([f,d]) => { const p = document.createElementNS(NS, "path"); p.setAttribute("fill", f); p.setAttribute("d", d); s.append(p); });
  return s;
}
function commentsSection(b){
  const box = el("section",{class:"comments","aria-labelledby":"c-head"},
    el("h2",{id:"c-head"},"Comments ", el("span",{id:"comment-count"})),
    el("div",{id:"c-compose"}),
    el("ol",{id:"comment-list",class:"c-list"}, el("li",{class:"c-empty",text:"Loading comments…"})));
  setTimeout(() => cOpen(b.id), 0);
  return box;
}
async function cOpen(blokId){
  cState.blok = blokId;
  await sbReady;
  if (cState.blok !== blokId) return;
  if (!sb){ const l = document.getElementById("comment-list"); if (l) l.replaceChildren(el("li",{class:"c-empty",text:"Comments couldn’t load. Refresh to try again."})); return; }
  cState.me = await cUser();
  cState.admin = !!(cState.me && ADMINS.includes(String(cState.me.email || "").toLowerCase()));
  cCompose();
  await cLoad();
  if (cState.ch){ try{ sb.removeChannel(cState.ch); }catch(e){} }
  cState.ch = sb.channel("c-" + ISSUE + "-" + blokId)
    .on("postgres_changes", {event:"*", schema:"public", table:"comments", filter:"blok=eq." + blokId}, () => { if (cState.blok === blokId) cLoad(); })
    .subscribe();
  if (cState.me) cJoinList();
}
async function cLoad(){
  const blokId = cState.blok;
  const { data, error } = await sb.from("comments").select("id,user_id,name,body,created_at").eq("issue", ISSUE).eq("blok", blokId).order("created_at", {ascending:true}).limit(500);
  if (blokId !== cState.blok) return;
  cState.rows = error ? [] : (data || []);
  cDraw();
}
function cWhen(s){ try{ return new Date(s).toLocaleDateString(undefined,{month:"short",day:"numeric"}); }catch(e){ return ""; } }
function cDraw(){
  const list = document.getElementById("comment-list"); if (!list) return;
  const n = cState.rows.length, head = document.getElementById("comment-count");
  if (head) head.textContent = n ? "(" + n + ")" : "";
  if (!n){ list.replaceChildren(el("li",{class:"c-empty",text:"No comments yet. Start the conversation."})); return; }
  const meId = cState.me && cState.me.id;
  list.replaceChildren(...cState.rows.map(c => {
    const mine = c.user_id === meId, tools = [];
    if (mine || cState.admin) tools.push(twoTap(el("button",{type:"button",class:"c-del"}), "Delete", "Tap again to delete", async () => {
      const { error } = await sb.from("comments").delete().eq("id", c.id); if (!error) cLoad(); }));
    if (cState.admin && !mine) tools.push(twoTap(el("button",{type:"button",class:"c-del"}), "Block", "Tap again to block", async () => {
      await sb.from("blocked").upsert({user_id:c.user_id, note:c.name}); }));
    return el("li",{class:"c-item"},
      el("div",{class:"c-meta"}, el("b",{text: mine ? c.name + " (you)" : c.name}), el("span",{text:cWhen(c.created_at)}), tools.length ? el("span",{class:"c-tools"}, tools) : null),
      el("p",{class:"c-text",text:c.body||""}));
  }));
}
function cCompose(){
  const host = document.getElementById("c-compose"); if (!host) return;
  const me = cState.me, blokId = cState.blok;
  const ta = el("textarea",{id:"comment-text",name:"comment",rows:"3",maxlength:"600",placeholder:"Add your take…"});
  try{ const d = localStorage.getItem(cDraftKey(blokId)); if (d) ta.value = d; }catch(e){}
  ta.addEventListener("input", () => { try{ ta.value ? localStorage.setItem(cDraftKey(blokId), ta.value) : localStorage.removeItem(cDraftKey(blokId)); }catch(e){} });
  const needName = !!me && !cName(me);
  const nameIn = el("input",{type:"text",id:"c-name",maxlength:"40",placeholder:"Your first name",autocomplete:"nickname","aria-label":"Name shown with your comments"});
  if (me && !cName(me)) nameIn.value = cSuggest(me);
  const nameHint = el("p",{class:"c-fine",text:"Your first name is shown with your comment. Your email stays private."});
  let editingName = needName;
  const status = el("span",{class:"c-status","aria-live":"polite"});
  const post = el("button",{type:"submit",class:"c-post"},"Post");
  const gate = el("div",{id:"c-gate",hidden:"hidden"});
  const form = el("form",{class:"c-form",onsubmit:async e => {
      e.preventDefault(); status.textContent = "";
      const text = ta.value.trim(); if (!text){ ta.focus(); return; }
      if (!cState.me){ cGate(gate); return; }
      let name = editingName ? nameIn.value.trim() : cName(cState.me);
      if (!name){ status.textContent = "Add the name to show with your comment."; nameIn.focus(); return; }
      post.disabled = true;
      if (name !== cName(cState.me)){ try{ await sb.auth.updateUser({data:{display_name:name}}); const u = await cUser(); if (u) cState.me = u; }catch(err){} }
      const { error } = await sb.from("comments").insert({issue:ISSUE, blok:blokId, name:name.slice(0,40), body:text.slice(0,600)});
      post.disabled = false;
      if (error){ const m = String(error.message||""); status.textContent = /slow down/.test(m) ? "One comment every 15 seconds. Try again in a moment." : /row-level|policy/i.test(m) ? "You can’t comment right now." : "That didn’t post. Try again in a moment."; return; }
      ta.value = ""; try{ localStorage.removeItem(cDraftKey(blokId)); }catch(err){}
      if (editingName){ cCompose(); }
      cLoad();
    }},
    el("label",{for:"comment-text",class:"c-label",text:"Your comment"}), ta,
    el("div",{class:"c-namebox",hidden: needName ? null : "hidden"}, nameIn, nameHint),
    el("div",{class:"c-actions"},
      me ? el("span",{class:"c-who"}, "Commenting as ", el("b",{text: cName(me) || "you"}), " · ",
             el("button",{type:"button",class:"c-link",onclick:e => { const box = e.target.closest("form").querySelector(".c-namebox"); box.hidden = false; editingName = true; nameIn.value = cName(cState.me) || cSuggest(cState.me); nameIn.focus(); }},"Change name"), " · ",
             el("button",{type:"button",class:"c-link",onclick:async () => { try{ await sb.auth.signOut(); }catch(err){} location.reload(); }},"Sign out"))
         : el("span",{class:"c-who",text:"Comments are for 20 Blok subscribers. It’s free."}),
      status, post));
  host.replaceChildren(form, gate);
}
function cGate(gate){
  if (!gate.hidden){ const f = gate.querySelector("button"); if (f) f.focus(); return; }
  gate.hidden = false;
  const who = document.querySelector(".c-form .c-who"); if (who) who.hidden = true;
  const nudge = document.getElementById("sb-nudge"); if (nudge) nudge.remove();
  const back = location.origin + location.pathname;
  const emailIn = el("input",{type:"email",required:"required",autocomplete:"email",inputmode:"email",placeholder:"you@email.com","aria-label":"Your email"});
  const msg = el("p",{class:"c-gmsg","aria-live":"polite"});
  const useEmail = el("button",{type:"submit",class:"c-post"},"Use my email");
  gate.replaceChildren(el("div",{class:"c-gate-box"},
    el("h3",{text:"Subscribe to comment"}),
    el("p",{class:"c-gate-sub",text:"Comments are for 20 Blok subscribers. It’s free."}),
    el("button",{type:"button",class:"c-google",onclick:async () => {
        msg.textContent = "Opening Google…";
        const { error } = await sb.auth.signInWithOAuth({provider:"google", options:{redirectTo:back}});
        if (error) msg.textContent = "Google didn’t open. Try your email instead."; }},
      googleMark(), "Continue with Google"),
    el("div",{class:"c-or"}, el("span",{text:"or"})),
    el("form",{class:"c-email",onsubmit:async e => {
        e.preventDefault(); const email = emailIn.value.trim();
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){ msg.textContent = "Check that email."; return; }
        useEmail.disabled = true; msg.textContent = "Sending…";
        const captchaToken = await getTurnstileToken();
        const { error } = await sb.auth.signInWithOtp({email, options:{emailRedirectTo:back, shouldCreateUser:true, captchaToken: captchaToken || undefined}});
        useEmail.disabled = false;
        msg.textContent = error ? "That didn’t go through. Try again in a minute." : "Check your inbox to confirm it’s you. The link brings you right back here, with your comment saved.";
      }}, emailIn, useEmail),
    el("p",{class:"c-fine",text:"Already subscribed? Use the same email. Subscribing adds you to the 20 Blok list; unsubscribe any time."}),
    msg));
}
async function cJoinList(){
  const me = cState.me; if (!me) return;
  const k = "blok20-joined-" + me.id;
  try{ if (localStorage.getItem(k)) return; }catch(e){}
  try{
    const { data:{ session } } = await sb.auth.getSession(); if (!session) return;
    const r = await fetch("/api/subscribe", {method:"POST", headers:{"Content-Type":"application/json", "Authorization":"Bearer " + session.access_token}, body:JSON.stringify({from:"comments"})});
    const j = await r.json().catch(() => ({}));
    if (r.ok && j.ok){ try{ localStorage.setItem(k, "1"); }catch(e){} markSubscribed(); }
  }catch(e){}
}
