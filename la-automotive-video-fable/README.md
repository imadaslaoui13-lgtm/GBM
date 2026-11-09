# LA Automotive – motion video, versie 2 (25 s, 9:16)

- `la-automotive-9x16-fable.mp4` – eindversie, 1080x1920, 30 fps, H.264 + AAC
- `index.html` – de animatie in code (open in de browser voor een preview)
- `tools/render.js` – rendert 750 frames via Playwright
- `tools/audio.py` – maakt de beat (120 BPM) en de geluidseffecten
- `tools/frames.js` – losse frames voor controle

Verschil met versie 1: alle belangrijke beelden staan in de veilige zone van
Reels en TikTok (tussen y 660 en y 1440). Het bovenste derde is altijd leeg.

Opnieuw renderen:

```
node tools/render.js frames
python3 tools/audio.py mix.wav
ffmpeg -framerate 30 -i frames/%04d.png -i mix.wav -af loudnorm=I=-14:TP=-1.5 -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart la-automotive-9x16-fable.mp4
```

## Varianten

- `la-automotive-9x16-fable-tekst.mp4` – met tekst bovenin, zonder muziek
- `la-automotive-9x16-fable-zonder-muziek.mp4` – zonder tekst, zonder muziek
- Tekst aanpassen: de lijst `CAPS` in `index.html`. Zonder tekst renderen: `NOTEXT=1 node tools/render.js frames`
- Zonder muziek: `python3 tools/audio.py mix.wav --no-music`
- `la-automotive-9x16-fable-15s.mp4` – korte advertentieversie van 15 seconden, met koppen, zonder muziek
- 15 seconden renderen: `CUT=15 node tools/render.js frames` en `python3 tools/audio.py mix.wav --cut15`
