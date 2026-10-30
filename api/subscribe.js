// POST /api/subscribe  { email }  → adds the reader to Lenny's Beehiiv list.
// Needs two Vercel environment variables: BEEHIIV_API_KEY and BEEHIIV_PUBLICATION_ID.
module.exports = async (req, res) => {
  if (req.method !== "POST") { res.status(405).json({ ok: false }); return; }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  const email = String((body && body.email) || "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) { res.status(400).json({ ok: false, error: "email" }); return; }
  const key = process.env.BEEHIIV_API_KEY, pub = process.env.BEEHIIV_PUBLICATION_ID;
  if (!key || !pub) { res.status(503).json({ ok: false, error: "setup" }); return; }
  try {
    const r = await fetch("https://api.beehiiv.com/v2/publications/" + encodeURIComponent(pub) + "/subscriptions", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" },
      body: JSON.stringify({ email, reactivate_existing: false, send_welcome_email: true, utm_source: "20blok.com", utm_medium: "website", referring_site: "https://20blok.com" })
    });
    if (!r.ok) { res.status(502).json({ ok: false, error: "beehiiv" }); return; }
    res.status(200).json({ ok: true });
  } catch (e) { res.status(502).json({ ok: false, error: "network" }); }
};
