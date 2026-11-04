# Dystopique — full-album video (v1, Nov 3 2026)

Retro-futuristic player video: each track's art (framed, neon pink) + blurred art backdrop, terminal-style title, cyan waveform from the audio, pink progress bar + time, CRT scanlines. 1920x1080, 30 fps.

Rebuild (needs the 14 Suno WAVs as wav/t01.wav … wav/t14.wav next to these files):
1. `python3 layers.py N` for N in 0..13 → layer01.png … layer14.png and scan.png (reads ../album.json and the track art in ../).
2. `./seg.sh N` for N in 1..14 → seg01.mp4 … seg14.mp4 (silent video per track).
3. Concat the WAVs (album.wav) and the segments, mux with AAC 320k.
4. For sending through chat (400 MB cap) re-encode at ~950k video / 256k audio. Better: save straight to Lenny's computer via the desktop app.

Fonts: Share Tech Mono (STM.ttf) and Orbitron Bold (ORB7.ttf), OFL, from Fontsource.
