# Waarom dit format werkt

| Onderdeel | Doel | Regel |
|---|---|---|
| Hook met A/B (0-2,5 s) | Duim stoppen, kijker kiest meteen een kant | Vraag in max 2 regels, nooit een leeg eerste frame |
| Voortgangsbalk in segmenten | Kijker ziet hoeveel er nog komt, dus kijkt uit | Eén segment per scène |
| Scènekaart per moment | Uitleg zonder geluid (85% kijkt zonder geluid) | Label + titel + één zin, wissel elke 5-10 s |
| Stempel bij het oordeel | Beloning: was jouw keuze goed? | Groot, schuin, dreun eronder |
| Eindscherm Like / Reageer / Deel | Interactie = bereik | Drie knoppen poppen één voor één in; stel de hookvraag niet opnieuw |

## Safe zones TikTok / Reels (1080x1920)
| Zone | Wat TikTok er toont | Regel |
|---|---|---|
| y 0-150 | Volgend / Voor jou | Niets; header begint pas op y 150 (logo 150, vraag 220) |
| y 1420-1920 | Naam, caption, muziek | Camerabeeld loopt door met donkere overgang (`layout.bottom_fade`); geen tekst |
| x 940-1080 | Like / reageer / deel-knoppen | Overlays centreren op `layout.safe_cx: 470` |

Vaste opbouw: header 0-300, video 300-1920 (bron ingezoomd tot 2:3, minder plafond), tekstkaart als blauwe balk over het beeld op 1240-1420, daaronder beeld met donkere overgang. Geen groot leeg merkvlak onderin.
## Huisstijl (standaard: BVO Verkeersschool)
- `brand.primary` #2410C4 (donkerblauw): kaarten, footer, voortgangsbalk, kopteksten.
- `brand.light` #71CEFA (lichtblauw): accenten, labels, optie A, stempel.
- Header wit met logo (`brand.logo`, `content/brand/bvo-logo.png`).
- Andere rijschool? Zet alleen `primary`, `light` en `logo` in de spec. Alle andere kleuren worden daaruit afgeleid (en zijn los te overschrijven: `header_bg`, `card`, `option_a`, `option_b`, `stamp_bg`, ...).
- Geen felgroen of rood: het format blijft rustig en herkenbaar in de merkkleuren.
- Font Inter: Black voor koppen, ExtraBold voor titels, Medium voor uitleg.
- Animaties: ease-out 0,35-0,4 s, alleen de stempel heeft een kleine overshoot.

## Header (compact)
- Wit, 166 px hoog: logo (60 px) met daaronder de vaste vraag. Geen voortgangsbalk, geen label rechtsboven.
