// POST /api/subscribe  { email }  → adds the reader to Lenny's Beehiiv list (Beehiiv sends its confirm email).
// POST /api/subscribe  { from: "comments" } + Authorization: Bearer <Supabase session token>
//   → adds a signed-in commenter. Their email is already verified (Google or email link), so no second confirm email.
// Needs two Vercel environment variables: BEEHIIV_API_KEY and BEEHIIV_PUBLICATION_ID.
const SB_URL = "https://kuyhymlhaifxccovamdt.supabase.co";
const SB_KEY = "sb_publishable_hK_MKPDnsGxDUTu2zRWYgg_d4WSwjIS";

async function verifiedCommenterEmail(req) {
  const auth = String(req.headers["authorization"] || "");
  if (!/^Bearer\s+\S+$/.test(auth)) return null;
  try {
    const r = await fetch(SB_URL + "/auth/v1/user", { headers: { apikey: SB_KEY, Authorization: auth } });
    if (!r.ok) return null;
    const u = await r.json();
    if (!u || u.is_anonymous || !u.email) return null;
    return String(u.email).trim().toLowerCase();
  } catch (e) { return null; }
}

module.exports = async (req, res) => {
  if (req.method !== "POST") { res.status(200).json({ ok: true, alive: true, hasKey: !!process.env.BEEHIIV_API_KEY, hasPub: !!process.env.BEEHIIV_PUBLICATION_ID, keyHasSpaces: /\s/.test(process.env.BEEHIIV_API_KEY || ""), pubHasSpaces: /\s/.test(process.env.BEEHIIV_PUBLICATION_ID || ""), pubLooksRight: /^pub_/.test(String(process.env.BEEHIIV_PUBLICATION_ID || "").trim()), node: process.version }); return; }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  const fromComments = body && body.from === "comments";
  let email;
  if (fromComments) {
    email = await verifiedCommenterEmail(req);
    if (!email) { res.status(401).json({ ok: false, error: "auth" }); return; }
  } else {
    email = String((body && body.email) || "").trim().toLowerCase();
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) { res.status(400).json({ ok: false, error: "email" }); return; }
  const key = String(process.env.BEEHIIV_API_KEY || "").replace(/\s+/g, ""), pub = String(process.env.BEEHIIV_PUBLICATION_ID || "").replace(/\s+/g, "");
  if (!key || !pub) { res.status(503).json({ ok: false, error: "setup", hasKey: !!key, hasPub: !!pub }); return; }
  const payload = { email, reactivate_existing: true, send_welcome_email: true, utm_source: "20blok.com", utm_medium: fromComments ? "comments" : "website", referring_site: "https://20blok.com" };
  if (fromComments) payload.double_opt_override = "off";
  try {
    const r = await fetch("https://api.beehiiv.com/v2/publications/" + encodeURIComponent(pub) + "/subscriptions", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!r.ok) { let detail = ""; try { detail = (await r.text()).slice(0, 300); } catch (e) {} console.log("beehiiv error", r.status, detail); res.status(502).json({ ok: false, error: "beehiiv", status: r.status, detail }); return; }
    res.status(200).json({ ok: true });
  } catch (e) { console.log("subscribe failed", e && e.message); res.status(502).json({ ok: false, error: "network", detail: String(e && e.message || e).slice(0, 200) }); }
};
