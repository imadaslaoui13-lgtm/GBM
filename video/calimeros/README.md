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
