// POST /api/notify  ← called by a Supabase Database Webhook whenever a comment is added.
// Emails Lenny: who commented, on which blok, what they said, with links to the blok and the admin page.
// Needs Vercel environment variables: RESEND_API_KEY and NOTIFY_SECRET (the same secret is set as a header on the webhook).
const TO = "lennybusinessnow@gmail.com";
const FROM = "20 Blok <hello@20blok.com>";

const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

module.exports = async (req, res) => {
  if (req.method !== "POST") { res.status(200).json({ ok: true, alive: true, hasResend: !!process.env.RESEND_API_KEY, hasSecret: !!process.env.NOTIFY_SECRET }); return; }
  const secret = String(process.env.NOTIFY_SECRET || "").trim();
  if (!secret || String(req.headers["x-notify-secret"] || "").trim() !== secret) { res.status(401).json({ ok: false, error: "auth" }); return; }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  const c = (body && body.record) || {};
  const key = String(process.env.RESEND_API_KEY || "").replace(/\s+/g, "");
  if (!key) { res.status(503).json({ ok: false, error: "setup" }); return; }
  if (body && body.table === "messages" && body.type === "INSERT") { await sendMessageMail(c, key, res); return; }
  if (!body || body.table !== "comments" || body.type !== "INSERT" || !c.blok) { res.status(200).json({ ok: true, skipped: true }); return; }
  const blokName = String(c.blok).replace(/-/g, " ").toUpperCase();
  const link = "https://20blok.com/" + (c.issue ? "issue-" + Number(c.issue) + "/" : "") + encodeURIComponent(c.blok);
  const html = `<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;color:#111">
    <p style="margin:0 0 6px;font-size:12px;letter-spacing:2px;color:#E0483B;font-weight:bold">NEW COMMENT · ${esc(blokName)} · ISSUE ${esc(c.issue)}</p>
    <p style="margin:0 0 12px"><b>${esc(c.name)}</b> wrote:</p>
    <blockquote style="margin:0 0 16px;padding:10px 14px;border-left:3px solid #E0483B;background:#f6f6f6;white-space:pre-wrap">${esc(c.body)}</blockquote>
    <p style="margin:0"><a href="${link}">See it on the blok</a> · <a href="https://20blok.com/admin">Admin page</a> (delete, block, see their email)</p>
  </div>`;
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" },
      body: JSON.stringify({ from: FROM, to: [TO], subject: `New comment on ${blokName} from ${String(c.name || "someone").slice(0, 40)}`, html, text: `${c.name} on ${blokName}:\n\n${c.body}\n\n${link}\nAdmin: https://20blok.com/admin` })
    });
    if (!r.ok) { let d = ""; try { d = (await r.text()).slice(0, 300); } catch (e) {} console.log("resend error", r.status, d); res.status(502).json({ ok: false, error: "resend", status: r.status }); return; }
    res.status(200).json({ ok: true });
  } catch (e) { res.status(502).json({ ok: false, error: "network" }); }
};

async function sendMessageMail(m, key, res) {
  const isInquiry = m.kind === "inquiry";
  const who = m.name || (m.email ? m.email : "a reader");
  const subject = isInquiry ? `New inquiry (${m.topic || "Other"}) from ${String(who).slice(0, 60)}` : `New feedback on 20 Blok${m.pitch ? " (wants to pitch)" : ""}`;
  const rows = [
    isInquiry ? ["Topic", m.topic] : ["Reads", m.read_freq],
    ["Enjoys", Array.isArray(m.bloks) && m.bloks.length ? m.bloks.join(", ") : ""], ["Name", m.name], ["Email", m.email], ["Wants to pitch/collaborate", m.pitch ? "Yes" : ""]
  ].filter(r => r[1]);
  const html = `<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;color:#111">
    <p style="margin:0 0 10px;font-size:12px;letter-spacing:2px;color:#E0483B;font-weight:bold">${isInquiry ? "NEW INQUIRY · CONTACT PAGE" : "NEW FEEDBACK · GOT A MINUTE?"}</p>
    ${rows.map(r => `<p style="margin:0 0 4px"><b>${esc(r[0])}:</b> ${esc(r[1])}</p>`).join("")}
    ${m.body ? `<blockquote style="margin:12px 0 16px;padding:10px 14px;border-left:3px solid #E0483B;background:#f6f6f6;white-space:pre-wrap">${esc(m.body)}</blockquote>` : ""}
    <p style="margin:0">${m.email ? "Hit reply to answer them directly. · " : ""}<a href="https://20blok.com/admin">Admin page → Inbox</a></p>
  </div>`;
  const payload = { from: FROM, to: [TO], subject, html, text: rows.map(r => r[0] + ": " + r[1]).join("\n") + (m.body ? "\n\n" + m.body : "") };
  if (m.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(m.email)) payload.reply_to = m.email;
  try {
    const r = await fetch("https://api.resend.com/emails", { method: "POST", headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!r.ok) { let d = ""; try { d = (await r.text()).slice(0, 300); } catch (e) {} console.log("resend error", r.status, d); res.status(502).json({ ok: false, error: "resend", status: r.status }); return; }
    res.status(200).json({ ok: true });
  } catch (e) { res.status(502).json({ ok: false, error: "network" }); }
}
