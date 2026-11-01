/* ---------- feedback box + contact page (saved to Supabase, emailed to Lenny) ---------- */
async function sendMessage(row){
  await sbReady;
  if (!sb) return "offline";
  const { error } = await sb.from("messages").insert(row);
  if (!error) return "ok";
  return /slow down/.test(String(error.message || "")) ? "slow" : "error";
}
function feedbackForm(){
  let freq = "";
  const chips = ["Every issue","Sometimes","First time"].map(label => {
    const b = el("button",{type:"button",class:"fb-chip","aria-pressed":"false",text:label,onclick:() => {
      freq = freq === label ? "" : label;
      chips.forEach(x => x.setAttribute("aria-pressed", String(x.textContent === freq)));
    }});
    return b;
  });
  const ta = el("textarea",{rows:"3",maxlength:"3000",placeholder:"What should I add, cut or change?","aria-label":"What should I add, cut or change?"});
  const pitch = el("input",{type:"checkbox",id:"fb-pitch"});
  const email = el("input",{type:"email",maxlength:"254",autocomplete:"email",inputmode:"email",placeholder:"Your email (so I can reply)","aria-label":"Your email"});
  try{ if (typeof cState !== "undefined" && cState.me && cState.me.email) email.value = cState.me.email; }catch(e){}
  const msg = el("p",{class:"fb-msg","aria-live":"polite"});
  const send = el("button",{type:"submit",class:"fb-btn"},"Send feedback");
  const form = el("form",{class:"fb-form",onsubmit:async e => {
      e.preventDefault(); msg.textContent = "";
      const text = ta.value.trim(), em = email.value.trim();
      if (!freq && !text){ msg.textContent = "Pick one or write a line first."; return; }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em)){ msg.textContent = "Add your email so I know who it’s from."; email.focus(); return; }
      send.disabled = true; msg.textContent = "Sending…";
      const r = await sendMessage({kind:"feedback", read_freq:freq || null, body:text || null, pitch:pitch.checked, email:em});
      send.disabled = false;
      if (r === "ok"){ form.replaceChildren(el("p",{class:"fb-done",text:"Got it. Thank you, this shapes the next issue."})); return; }
      msg.textContent = r === "slow" ? "One at a time. Try again in a few seconds." : "That didn’t send. Try again in a moment.";
    }},
    el("p",{class:"fb-q",text:"How often do you read 20 Blok?"}),
    el("div",{class:"fb-chips",role:"group","aria-label":"How often do you read 20 Blok?"}, chips),
    ta,
    email,
    el("label",{class:"fb-check",for:"fb-pitch"}, pitch, " I’d like to pitch or collaborate"),
    el("p",{class:"fb-fine",text:"No newsletter signup needed. Your email is only for replies."}),
    el("div",{class:"fb-row"}, send, msg));
  return form;
}
function contactView(){
  const topics = ["Collaboration","Press / interview","Write for 20 Blok","Sponsorship / brand","Other"];
  const name = el("input",{type:"text",id:"ct-name",maxlength:"80",autocomplete:"name",required:"required"});
  const email = el("input",{type:"email",id:"ct-email",maxlength:"254",autocomplete:"email",inputmode:"email",required:"required"});
  const topic = el("select",{id:"ct-topic"}, topics.map(t => el("option",{value:t,text:t})));
  const body = el("textarea",{id:"ct-body",rows:"6",maxlength:"3000",required:"required"});
  try{ if (typeof cState !== "undefined" && cState.me && cState.me.email) email.value = cState.me.email; }catch(e){}
  const msg = el("p",{class:"fb-msg","aria-live":"polite"});
  const send = el("button",{type:"submit",class:"sub"},"Send");
  const field = (id, label, input) => el("div",{class:"ct-field"}, el("label",{for:id,text:label}), input);
  const form = el("form",{class:"ct-form",onsubmit:async e => {
      e.preventDefault(); msg.textContent = "";
      const n = name.value.trim(), em = email.value.trim(), b = body.value.trim();
      if (!n || !b){ msg.textContent = "Add your name and a message."; return; }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em)){ msg.textContent = "Check that email so I can reply."; email.focus(); return; }
      send.disabled = true; msg.textContent = "Sending…";
      const r = await sendMessage({kind:"inquiry", topic:topic.value, name:n, email:em, body:b});
      send.disabled = false;
      if (r === "ok"){ form.replaceChildren(el("p",{class:"fb-done",text:"Sent. I’ll reply to " + em + " soon."})); return; }
      msg.textContent = r === "slow" ? "One at a time. Try again in a few seconds." : "That didn’t send. Email lennybusinessnow@gmail.com instead.";
    }},
    field("ct-name","Your name",name), field("ct-email","Your email",email), field("ct-topic","What it’s about",topic), field("ct-body","Message",body),
    el("div",{class:"fb-row"}, send, msg));
  return [el("article",{class:"article"},
    el("a",{class:"back",href:"/",text:"← BACK TO THE GRID"}),
    el("header",{class:"art-head"}, el("p",{class:"eyebrow",text:"20 Blok"}), el("h1",{class:"art-title",text:"Contact"})),
    el("div",{class:"prose"},
      el("p",{text:"Want to collaborate, interview me, write for 20 Blok, or bring a brand on board? This goes straight to my inbox, and I reply from lennybusinessnow@gmail.com."}),
      form,
      el("p",{class:"ct-alt"}, "Rather email? ", el("b",{text:"lennybusinessnow@gmail.com"}))))];
}
