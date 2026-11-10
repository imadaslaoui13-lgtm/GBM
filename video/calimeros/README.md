# Calimero's Chicken – reclamevideo (16 s, 9:16)

Eindbestand: `calimeros-reclame.mp4` (1080x1920, 30 fps, met muziek).
Gemaakt met de Hypit-skill (motion graphics, geen AI-credits nodig) en de viral-hooks-skill.

## Opbouw
| Tijd | Scène | Tekst |
|---|---|---|
| 0–2 s | Hook: kippenpoot valt, KRAK!-explosie | KRAK! / 1 hap en je bent verkocht. |
| 2–4 s | Krokant | KROKANT van buiten |
| 4–6 s | Sappig | SAPPIG van binnen |
| 6–10 s | Menu | Bucket, Wings, Burger, Friet |
| 10–12 s | Delen | SAMEN smaakt 't beter |
| 12–16 s | Eindkaart + jingle | Logo, Krak. Smak. Calimero's., KOM PROEVEN |

Elke scène valt op de beat (120 BPM). Het logo komt pas aan het eind (viral-hooks: geen logo-intro).

## Aanpassen
- Teksten en timing: `calimeros.svml`
- Tekenwerk en animatie: `packages/spot/src/render.ts`
- Muziek: `assets/muziek-generator.py` → `assets/muziek.wav`

## Opnieuw renderen
```bash
npm install
(cd packages/spot && npm install && npm run build) && npm install
hypit build calimeros.svrun --runtime hypit.runtime.json --follow
hypit get <build-id> --output final.video --to calimeros-reclame.mp4
```

---

# Reel 2 – Ei breekt open (9 s, minimalistisch)

Eindbestand: `calimeros-ei-reel.mp4` (1080x1920, 30 fps, met sounddesign).

| Tijd | Wat gebeurt er |
|---|---|
| 0–4 s | Heel ei op rustige crème achtergrond. Wiebelt 3x, barst steeds verder (tik + krak) |
| 4 s | Ei breekt open: bovenkant vliegt weg, schilfers, warm licht |
| 4–5 s | Logo komt uit het ei omhoog |
| 5,4 s | VERS · KROKANT · EERLIJK, rode lijn, KOM PROEVEN |

- Teksten en timing: `calimeros-ei.svml`
- Animatie: `packages/reveal/src/render.ts`
- Geluid: `assets/ei-geluid-generator.py` → `assets/ei-geluid.wav`
- Renderen: `hypit build calimeros-ei.svrun --runtime hypit.runtime.json --follow`

---

# Short 3 – "De barst" (10 s, minimalistisch, vector)

Eindbestand: `calimeros-short.mp4` (1080x1920, gerenderd op 1440x2560 en scherp teruggeschaald).

| Tijd | Wat gebeurt er |
|---|---|
| 0–1 s | Zwart scherm, één witte barst schiet erover (hook) |
| 1 s | Scherm breekt open langs de barst → geel |
| 1–4,8 s | Krokant. · Sappig. · Eerlijk. (strakke typografie, klik op elk woord) |
| 4,8–6,3 s | Navy barst, geel breekt open, de lijn krimpt tot de rand van de eierschaal en het ei tekent zich |
| 6,3–10 s | Woordmerk bouwt op, daarna KOM PROEVEN |

Het logo is hier als vector nagebouwd (geen pixelplaatje), dus altijd scherp.

- Teksten en timing: `calimeros-short.svml`
- Animatie en vector-logo: `packages/short/src/render.ts`
- Geluid: `assets/short-geluid-generator.py`
- Renderen: `hypit build calimeros-short.svrun --runtime hypit.runtime.json --follow`, daarna
  `ffmpeg -i <export>.mp4 -vf scale=1080:1920:flags=lanczos -c:v libx264 -preset slow -crf 14 -c:a aac -b:a 192k calimeros-short.mp4`
