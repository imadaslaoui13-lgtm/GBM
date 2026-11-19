# Waarom dit format werkt

| Onderdeel | Doel | Regel |
|---|---|---|
| Hook met A/B (0-2,5 s) | Duim stoppen, kijker kiest meteen een kant | Vraag in max 2 regels, nooit een leeg eerste frame |
| Voortgangsbalk in segmenten | Kijker ziet hoeveel er nog komt, dus kijkt uit | Eén segment per scène |
| Scènekaart per moment | Uitleg zonder geluid (85% kijkt zonder geluid) | Label + titel + één zin, wissel elke 5-10 s |
| Stempel bij het oordeel | Beloning: was jouw keuze goed? | Groot, schuin, dreun eronder |
| Poll aan het eind | Comments = bereik | Twee opties, letter A/B zodat reageren 1 teken is |
| Serienummer | Volgers terug laten komen | "Examensituatie #NN" |

## Safe zones (TikTok / Reels)
- Onderste 320 px en rechter 140 px vallen onder knoppen en caption: daar alleen sfeer (handle), geen kerninfo.
- Kaart = de balk onder de video (`layout.card_band: true`, y 1680-1920). Het camerabeeld blijft zo helemaal vrij. Let op: op TikTok valt de caption deels over deze balk; houd de titel kort.

## Huisstijl (standaard: BVO Verkeersschool)
- `brand.primary` #2410C4 (donkerblauw): kaarten, footer, voortgangsbalk, kopteksten.
- `brand.light` #71CEFA (lichtblauw): accenten, labels, optie A, stempel.
- Header wit met logo (`brand.logo`, `content/brand/bvo-logo.png`).
- Andere rijschool? Zet alleen `primary`, `light` en `logo` in de spec. Alle andere kleuren worden daaruit afgeleid (en zijn los te overschrijven: `header_bg`, `card`, `option_a`, `option_b`, `stamp_bg`, ...).
- Geen felgroen of rood: het format blijft rustig en herkenbaar in de merkkleuren.
- Font Inter: Black voor koppen, ExtraBold voor titels, Medium voor uitleg.
- Animaties: ease-out 0,35-0,4 s, alleen de stempel heeft een kleine overshoot.
