---
name: rijles-oordeel
description: Maakt van een ruwe rijlesvideo (dashcam of telefoon in de lesauto) een virale verticale short in het vaste format "Handelde de leerling goed?" - hook met A/B-keuze in de eerste 2,5 s, gesegmenteerde voortgangsbalk, geanimeerde scènekaarten per moment, oordeelstempel van de instructeur, een poll "Wat doe jij?" als comment-trigger, kleurcorrectie, geluidstikken en -14 LUFS. Plus posttekst met 3 hooks. Gebruik bij rijles, lesauto, leerling, examensituatie, verkeerssituatie, rijschoolvideo, "maak hier een viral van", of als iemand een rijlesvideo aanlevert.
argument-hint: "<video> [situatienummer] [handle]"
---

# Rijles-oordeel

Eén rijlesvideo in, één afgewerkte short uit (1080x1920, 30 fps, H.264, -14 LUFS) plus `post.md`.
Engine: `<skill>/engine/render.py` (Python 3 + Pillow + ffmpeg, gratis, offline). Voorbeeld: `examples/fietser-bestelbus.json`.

Werk in het Nederlands, B1, kort. Lees eerst [references/format.md](references/format.md): daar staan de regels die het format viraal maken.

## 1. Video bekijken
```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of compact "<video>"
ffmpeg -v error -i "<video>" -vf "fps=1,scale=240:-1,tile=8x6" -frames:v 1 sheet.png
```
Bekijk de sheet. Noteer per seconde: wat gebeurt er (fietser, voetganger, kruising, voorrang) en wanneer de leerling een beslissing neemt.
- **Vraag altijd eerst om het ruwe origineel.** Dat geeft meer beeld en geen oude tekst om weg te werken.
- **Ruwe video** (geen tekst in beeld): `crop` = het hele beeld of een 3:4-uitsnede rond de voorruit.
- **Video met oude tekst erin**: meet de camerazone (rij per rij de achtergrondkleur) en zet `layout.card` precies over het oude tekstblok. Check dat met `--preview`.

## 2. Hooks
Gebruik de skill `viral-hooks` voor 3 hooks. Kies er één voor in beeld (max 4 woorden per regel, laatste regel in accentkleur) en zet de andere twee in `post.md`. Werkt het best:
- Vraag met twee kanten: "Wachten / of doorrijden?"
- Negatie: "Rijd hier niet zomaar door"
- Specifiek: "Fietser én bestelbus. Jij beslist."
Verzin nooit cijfers ("90% zakt hierop") die je niet kunt onderbouwen.

## 3. Spec schrijven
Kopieer `examples/fietser-bestelbus.json` naar `<project>/spec.json` en vul in:
- `scenes`: 4 tot 6 kaarten. Vast patroon: **Kijk mee → Moment 1 → Moment 2 → Oordeel instructeur (`kind: verdict`) → Jouw oordeel (`kind: poll`)**. `start` = de seconde waarop het moment in beeld begint. Titel max 28 tekens, sub max 45 tekens.
- `stamp`: tegelijk met de verdict-kaart. Tekst: `GOED GEHANDELD`, `TE SNEL`, `VOORRANG GEMIST`, etc.
- `poll`: start 6 tot 8 s voor het einde. Altijd twee opties A/B.
- `header.right`: doorlopende nummering ("Examensituatie #02"). Dat bouwt een serie op.
- `brand`: `primary`, `light` en `logo` van de rijschool (standaard BVO, zie format.md).
- `footer.parts`: slogan in delen met eigen kleur, `footer.line`: tweede regel.

## 4. Preview, dan render
```bash
python3 <skill>/engine/render.py spec.json out/short.mp4 --preview 1 8 26 38
```
Bekijk de PNG's. Check: oude tekst volledig bedekt, niets buiten beeld, tekst niet afgekapt. Daarna de volledige render (ca. 3 min voor 45 s):
```bash
python3 <skill>/engine/render.py spec.json out/short.mp4
```
Controleer de loudness: `ffmpeg -i out/short.mp4 -af ebur128 -f null - 2>&1 | grep " I:"` (doel -14, marge ±1).

## 5. post.md
Schrijf naast de video: 3 hooks, caption (eerste zin = vraag, max 125 tekens voor de preview), een pinned comment ("A of B? Ik reageer op iedereen"), 5 tot 8 hashtags (#rijles #rijexamen #cbr #rijbewijs #verkeersregels #rijschool + plaats), beste posttijd (17:00-20:00 doordeweeks). Optioneel: `virality_predictor` (Higgsfield) voor een score van twee hookvarianten. Dat is een indicatie, geen garantie.

## Regels
- Nooit gezichten of kentekens van derden herkenbaar uitlichten. Blur ze met `boxblur` als ze groot in beeld staan.
- Geen echte merknamen of logo's van een rijschool zonder toestemming.
- Het oordeel moet kloppen met de verkeersregels. Twijfel je, zet dan "Wat vind jij?" in plaats van een stempel.
