# LA Automotive – motion video (25 s, 9:16)

- `la-automotive-9x16.mp4` – eindversie, 1080x1920, 30 fps, H.264 + AAC, met muziek en UI-geluiden
- `index.html` – de animatie in code (open in browser = preview, `window.seek(t)` voor export)
- `tools/render.js` – rendert 750 frames via Playwright
- `tools/audio.py` – maakt de beat (120 BPM) en de geluidseffecten
- `tools/frames.js` – losse frames voor controle

Opnieuw renderen:

```
node tools/render.js frames
python3 tools/audio.py mix.wav
ffmpeg -framerate 30 -i frames/%04d.png -i mix.wav -af loudnorm=I=-14:TP=-1.5 -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart la-automotive-9x16.mp4
```
