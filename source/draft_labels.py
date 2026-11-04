#!/usr/bin/env python3
"""Issue 8 DRAFT branch only: relabel the built pages so the preview reads as an unpublished Issue 8.
Run after build_site.py:  python3 source/build_site.py . && python3 source/draft_labels.py .
Delete this file when Issue 8 ships (the real rollover replaces it)."""
import os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
SUBS = [('title:"Retail Mindset", month:"October 2026"', 'title:"DRAFT — not published", month:"November 2026"'),
        ('const COVERTEXT = {"chain-reaction":"The Bitcoin Crowd Lost the Plot","newsfeed":"Should We Talk About Lindsay Clancy?","must-see":"Maeve Halligan Swims Upstream","now-playing":"Prada 2 and the Hidden Cost"};', 'const COVERTEXT = {};')]
n = 0
for dp, _, fs in os.walk(root):
    if "/.git" in dp or "/source" in dp: continue
    for f in fs:
        if not f.endswith(".html"): continue
        p = os.path.join(dp, f); s = open(p, encoding="utf-8").read(); o = s
        for a, b in SUBS: s = s.replace(a, b)
        if s != o: open(p, "w", encoding="utf-8").write(s); n += 1
print("relabelled", n, "pages")
