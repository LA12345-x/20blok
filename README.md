# 20 Blok

Culture, creativity, and the internet. The site behind 20blok.com.

- `index.html` — the whole site (issue content is inside it)
- `media/` — images and video loops
- `supabase/setup.sql` — the votes table (run once in Supabase)

Built and updated with Claude. Publishing = pushing to `main`; Vercel deploys automatically.

## How updates work
- `source/` holds the editable parts: `data.json` (every blok's text, links and media), `template.html` (design and behavior), `images.json` (media), `build_site.py`.
- To rebuild: `python3 source/build_site.py . <SUPABASE_URL> <SUPABASE_ANON_KEY>` from the repo root, then commit and push. Vercel publishes `main` automatically.
