#!/usr/bin/env python3
"""Trailer-stijl renderer: rijlesbeelden als filmische game-trailer.

Eigen ontwerp in de sfeer van moderne open-world trailers: paars-oranje grade, filmkorrel,
4:5-beeld met zwarte balken, snelle shots, filmische ondertitels, personagekaart en een
collage-eindkaart met getekende panelen. Geen logo's, fonts of muziek van bestaande games.

Gebruik:  python3 trailer.py <spec.json> <out.mp4> [--preview SEC ...]
"""
import json, math, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageEnhance, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import font, hexc, ease_out, ease_back, Renderer  # noqa: E402
from gta import TITLE, HUD, gradient_text, with_alpha, clamp, win, SFX_DIR  # noqa: E402

W, H, FPS = 1080, 1920, 30
VY, VH = 285, 1350          # 4:5-beeld tussen zwarte balken
SUNSET = [(255, 200, 70), (255, 92, 140), (150, 60, 220)]  # geel -> roze -> paars


def grade():
    return ("eq=contrast=1.18:saturation=1.35:gamma=0.96,"
            "colorbalance=rs=0.04:gs=-0.04:bs=0.14:rm=0.10:gm=-0.02:bm=0.06:rh=0.14:gh=0.04:bh=-0.06,"
            "curves=b='0/0.05 0.5/0.48 1/0.9',"
            "noise=alls=10:allf=t,vignette=angle=PI/4.5")


def frame_at(src, t, crop):
    g = grade().replace("noise=alls=10:allf=t,", "")
    c = crop
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1",
                          "-vf", f"crop={c[2]}:{c[3]}:{c[0]}:{c[1]},scale={W}:{VH},{g}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return Image.frombytes("RGB", (W, VH), raw)


def comic(img):
    """Getekende look: vlakken, verzadigde kleuren en donkere contourlijnen."""
    small = img.resize((img.width // 3, img.height // 3), Image.LANCZOS)
    for _ in range(3):
        small = small.filter(ImageFilter.MedianFilter(5))
    base = small.resize(img.size, Image.LANCZOS)
    base = ImageEnhance.Color(ImageOps.posterize(base, 4)).enhance(1.45)
    base = ImageEnhance.Contrast(base).enhance(1.15)
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 30 else 0)
    edges = edges.resize(img.size, Image.NEAREST).filter(ImageFilter.MaxFilter(3))
    ink = Image.new("RGB", img.size, (20, 8, 40))
    base.paste(ink, (0, 0), edges)
    return base


class Trailer:
    def __init__(self, spec, base):
        self.s, self.base = spec, base
        b = spec["brand"]
        self.primary, self.light = hexc(b["primary"]), hexc(b["light"])
        self.logo = Image.open(os.path.join(base, b["logo"])).convert("RGBA") if b.get("logo") else None
        self.cx = spec.get("safe_cx", 470)
        self._icon = Renderer._icon.__get__(type("X", (), {"primary": self.primary})())
        self.cache = {}
        src = os.path.join(base, spec["source"]["file"])
        self.collage = self._collage(src) if "end" in spec else None
        self.yaw = self._load_yaw()

    # ---------- eindkaart: collage met getekende panelen ----------
    def _collage(self, src):
        e = self.s["end"]
        bg = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(bg)
        for y in range(H):
            q = y / H
            if q < 0.5:
                a, b_, k = SUNSET[2], SUNSET[1], q / 0.5
            else:
                a, b_, k = SUNSET[1], SUNSET[0], (q - 0.5) / 0.5
            d.line([(0, y), (W, y)], fill=tuple(int(a[i] + (b_[i] - a[i]) * k) for i in range(3)) + (255,))
        # zon met strepen
        sun = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sun)
        sd.ellipse((W / 2 - 330, 1180, W / 2 + 330, 1840), fill=(255, 220, 120, 200))
        for i, y in enumerate(range(1480, 1840, 34)):
            sd.rectangle((0, y, W, y + 8 + i * 2), fill=(0, 0, 0, 0))
        bg.alpha_composite(sun)
        if not e.get("panels"):
            return bg
        # panelen (posities, kanteling) in een collage
        slots = [(40, 170, 560, 600, -3), (530, 150, 1040, 560, 2.5), (60, 590, 520, 980, 2), (500, 560, 1040, 980, -2.5)]
        crop = self.s["source"]["crop"]
        for (x0, y0, x1, y1, rot), t in zip(slots, e["panel_times"]):
            fr = comic(frame_at(src, t, crop))
            pw, ph = x1 - x0, y1 - y0
            r = max(pw / fr.width, ph / fr.height)
            fr = fr.resize((int(fr.width * r) + 1, int(fr.height * r) + 1), Image.LANCZOS)
            fr = fr.crop(((fr.width - pw) // 2, (fr.height - ph) // 2, (fr.width - pw) // 2 + pw, (fr.height - ph) // 2 + ph))
            panel = Image.new("RGBA", (pw + 24, ph + 24), (255, 255, 255, 255))
            panel.paste(fr, (12, 12))
            ImageDraw.Draw(panel).rectangle((12, 12, pw + 11, ph + 11), outline=(20, 8, 40, 255), width=6)
            panel = panel.rotate(rot, resample=Image.BICUBIC, expand=True)
            sh = Image.new("RGBA", panel.size, (0, 0, 0, 0))
            sh.paste((0, 0, 0, 140), (0, 0), panel.getchannel("A"))
            bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (x0 + 10, y0 + 18))
            bg.alpha_composite(panel, (x0, y0))
        return bg

    def text_img(self, key, text, fnt, top, bottom, stroke):
        k = (key, text)
        if k not in self.cache:
            self.cache[k] = gradient_text(text, fnt, top, bottom, stroke)
        return self.cache[k]

    def place(self, im, img, cx, cy, a=1.0, scale=1.0, rot=0, maxw=900):
        scale = min(scale, maxw / img.width) if img.width * scale > maxw else scale
        if scale != 1.0:
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        if rot:
            img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(with_alpha(img, a), (int(cx - img.width / 2), int(cy - img.height / 2)))

    # ---------- lagen ----------
    def presents(self, im, t):
        p = self.s.get("presents")
        if not p:
            return
        k = win(t, 0.15, p["end"] - 0.1, 0.35, 0.3)
        if not k:
            return
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        f = font("SemiBold", 26)
        txt = " ".join(p["text"].upper())  # ruime letterspatiëring
        d.text((self.cx, 940), txt, font=f, fill=(255, 255, 255, 255), anchor="mm")
        im.alpha_composite(with_alpha(lay, k))

    def subtitles(self, im, t):
        for s in self.s.get("subs", []):
            k = win(t, s["start"], s["end"], 0.12, 0.12)
            if not k:
                continue
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            f = font("Medium", 40)
            d.text((self.cx, 1165), s["text"], font=f, fill=(255, 255, 255, 255), anchor="mm",
                   stroke_width=3, stroke_fill=(0, 0, 0, 200))
            im.alpha_composite(with_alpha(lay, k))

    def cards(self, im, t):
        for c in self.s.get("cards", []):
            k = win(t, c["start"], c["end"], 0.25, 0.25)
            if not k:
                continue
            slide = int((1 - ease_out((t - c["start"]) / 0.5)) * 60)
            big = self.text_img("card", c["title"], TITLE(96), SUNSET[0], SUNSET[1], 8)
            self.place(im, big, 70 + big.width / 2 - slide, VY + 210, a=k, maxw=820)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.text((78 - slide, VY + 290), c["sub"].upper(), font=font("Bold", 34), fill=(255, 255, 255, 255),
                   stroke_width=3, stroke_fill=(0, 0, 0, 200))
            im.alpha_composite(with_alpha(lay, k))

    def flashes(self, im, t):
        for f in self.s.get("flashes", []):
            k = 1 - clamp((t - f) / 0.12) if t >= f else 0
            if k > 0:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 240, 230, int(200 * k))))

    # ---------- eindkaart: game-titellogo ----------
    def _palms(self, w, h):
        """Silhouetten van palmbomen: gebogen stam en hangende bladeren."""
        lay = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(lay)
        for (bx, sc, lean) in [(0.16, 1.0, 0.10), (0.27, 0.72, -0.06), (0.76, 0.95, -0.12), (0.88, 0.66, 0.08)]:
            x0 = bx * w
            H_ = h * 0.62 * sc
            trunk = []
            for i in range(11):  # licht gebogen stam
                q = i / 10
                trunk.append((x0 + lean * H_ * q * q, h - H_ * q))
            for i in range(10):
                (xa, ya), (xb, yb) = trunk[i], trunk[i + 1]
                wdt = (11 - 5 * i / 10) * sc
                d.polygon([(xa - wdt, ya), (xa + wdt, ya), (xb + wdt * 0.9, yb), (xb - wdt * 0.9, yb)], fill=255)
            tx, ty = trunk[-1]
            for k in range(8):  # hangende bladeren naar beide kanten
                side = -1 if k % 2 == 0 else 1
                spread = 0.35 + 0.65 * (k // 2) / 3
                L = (70 + 40 * (1 - abs(spread - 0.6))) * sc
                pts = []
                for j in range(9):
                    q = j / 8
                    x = tx + side * L * q * (0.6 + 0.4 * spread)
                    y = ty - 28 * sc * math.sin(q * math.pi * 0.9) * (1.2 - spread) + 46 * sc * spread * q * q
                    pts.append((x, y))
                for j in range(8):
                    wdt = int(max(2, 12 * sc * (1 - j / 8)))
                    d.line([pts[j], pts[j + 1]], fill=255, width=wdt)
            d.ellipse((tx - 10 * sc, ty - 8 * sc, tx + 10 * sc, ty + 10 * sc), fill=255)
        return lay

    def logo_mark(self):
        """BVO in de stijl van een game-titellogo: hoge letters met verloop blauw-paars-roze-oranje,
        vage palmen, oranje binnenlijn + paarse buitenrand, wit gestapeld woordmerk in het midden."""
        if "mark" in self.cache:
            return self.cache["mark"]
        e = self.s["end"]
        txt = e.get("mark", "BVO")
        f = HUD(360)
        tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
        l, t_, r, b = tmp.textbbox((0, 0), txt, font=f)
        pad = 60
        m0 = Image.new("L", (r - l + 2 * pad, b - t_ + 2 * pad), 0)
        ImageDraw.Draw(m0).text((pad - l, pad - t_), txt, font=f, fill=255)
        Wm, Hm = m0.width, int(m0.height * 1.85)
        mask = m0.resize((Wm, Hm), Image.LANCZOS)
        # verloop van boven naar beneden
        stops = [(70, 110, 235), (140, 70, 215), (225, 80, 165), (250, 125, 115), (253, 185, 95)]
        art = Image.new("RGB", (Wm, Hm))
        ad = ImageDraw.Draw(art)
        for y in range(Hm):
            q = min(0.999, y / Hm)
            seg = int(q * 4); k = q * 4 - seg
            ad.line([(0, y), (Wm, y)], fill=tuple(int(stops[seg][i] + (stops[seg + 1][i] - stops[seg][i]) * k) for i in range(3)))
        # vage, grote palmen: iets donkerder en paarser dan de achtergrond
        S = 3
        palms = Image.new("L", (Wm, Hm), 0)
        big = self._palms(Wm // 2, Hm // 2).resize((Wm, Hm), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2))
        palms.paste(big, (0, int(Hm * 0.08)))
        tint = Image.new("RGB", (Wm, Hm), (110, 40, 170))
        art = Image.composite(tint, art, palms.point(lambda v: int(v * 0.33)))
        # randen: zwart -> paarse buitenrand -> oranje binnenlijn -> vulling
        M = 40
        out = Image.new("RGBA", (Wm + 2 * M, Hm + 2 * M), (0, 0, 0, 0))
        bm = Image.new("L", out.size, 0)
        bm.paste(mask, (M, M))
        out.paste((95, 35, 160, 255), (0, 0), bm.filter(ImageFilter.MaxFilter(23)))
        out.paste((250, 175, 70, 255), (0, 0), bm.filter(ImageFilter.MaxFilter(9)))
        inner = bm.filter(ImageFilter.MinFilter(3))
        af = Image.new("RGB", out.size)
        af.paste(art, (M, M))
        out.paste(af, (0, 0), inner)
        # wit woordmerk, gestapeld, gecentreerd over de letters
        wm = e.get("wordmark", ["verkeers", "school"])
        wm = wm if isinstance(wm, list) else [wm]
        fw = HUD(96)
        lh = 100
        cy = out.height * 0.47 - (len(wm) - 1) * lh / 2
        lay = Image.new("RGBA", out.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for i, line in enumerate(wm):
            y = cy + i * lh
            ld.text((out.width / 2, y), line, font=fw, fill=(255, 255, 255, 255), anchor="mm",
                    stroke_width=16, stroke_fill=(255, 255, 255, 255))
        ring = lay.getchannel("A")
        lay2 = Image.new("RGBA", out.size, (0, 0, 0, 0))
        l2 = ImageDraw.Draw(lay2)
        for i, line in enumerate(wm):
            y = cy + i * lh
            l2.text((out.width / 2, y), line, font=fw, fill=(255, 255, 255, 255), anchor="mm",
                    stroke_width=10, stroke_fill=(30, 15, 60, 255))
        outer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        outer.paste((255, 255, 255, 255), (0, 0), ring)  # dunne witte buitenrand
        out.alpha_composite(outer)
        out.alpha_composite(lay2)
        self.cache["mark"] = out
        return out

    def end(self, im, t):
        e = self.s["end"]
        if t < e["at"]:
            return
        k = ease_out((t - e["at"]) / 0.35)
        bg = self.cache.get("endbg")
        if bg is None:
            bg = Image.new("RGBA", (W, H))
            d = ImageDraw.Draw(bg)
            for y in range(H):
                q = y / H
                c = (0, 0, 0)
                d.line([(0, y), (W, y)], fill=c + (255,))
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse((-200, 300, W + 200, 1100), fill=(120, 40, 160, 0))
            bg.alpha_composite(g.filter(ImageFilter.GaussianBlur(120)))
            self.cache["endbg"] = bg
        im.alpha_composite(with_alpha(bg, k))
        mk = ease_out(clamp((t - e["at"] - 0.15) / 0.9))
        if mk > 0:
            self.place(im, self.logo_mark(), W // 2, 720, a=mk, scale=1.06 - 0.06 * mk, maxw=900)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.text((W // 2, 1090), e.get("line2", "voor 't Gooi en omstreken").upper(), font=font("Bold", 30), fill=(255, 255, 255, 220), anchor="mm")
        d.text((W // 2, 1180), " ".join(e["sub"].upper()), font=font("ExtraBold", 34), fill=(255, 255, 255, 255), anchor="mm")
        im.alpha_composite(with_alpha(lay, clamp((t - e["at"] - 0.9) / 0.4)))
        for j, (kind, label) in enumerate(e["items"]):
            kk = ease_out((t - e["at"] - 1.4 - j * 0.15) / 0.4)
            if kk <= 0:
                continue
            R, SS = 48, 4
            big = Image.new("RGBA", (2 * R * SS + 8, 2 * R * SS + 8), (0, 0, 0, 0))
            bd = ImageDraw.Draw(big)
            bc = R * SS + 4
            bd.ellipse((4, 4, 4 + 2 * R * SS, 4 + 2 * R * SS), outline=(255, 255, 255, 255), width=5 * SS)
            self._icon(bd, kind, bc, bc, R * SS * (0.55 if kind == "like" else 0.6), (255, 255, 255, 255))
            btn = big.resize((big.width // SS, big.height // SS), Image.LANCZOS)
            cx = W // 2 + (j - 1) * 190
            self.place(im, btn, cx, 1320, a=kk, maxw=2000)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((cx, 1400), label.upper(), font=font("Bold", 26), fill=(255, 255, 255, 255), anchor="mm")
            im.alpha_composite(with_alpha(lay, kk))

    # ---------- missie-UI ----------
    def mission_card(self, im, t):
        m = self.s.get("mission")
        if not m:
            return
        k = win(t, m["start"], m["end"], 0.3, 0.4)
        if not k:
            return
        slide = int((1 - ease_out((t - m["start"]) / 0.4)) * -40)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x0, y0 = 50 + slide, VY + 90
        f1, f2 = font("Black", 50), font("SemiBold", 32)
        w = max(d.textlength(m["title"].upper(), font=f1), d.textlength(m["goal"], font=f2)) + 60
        d.rounded_rectangle((x0, y0, x0 + w, y0 + 140), 16, fill=(8, 6, 18, 190))
        d.rectangle((x0, y0 + 18, x0 + 7, y0 + 122), fill=(255, 62, 165, 255))
        d.text((x0 + 30, y0 + 22), m["title"].upper(), font=f1, fill=(255, 62, 165, 255))
        d.text((x0 + 30, y0 + 86), m["goal"], font=f2, fill=(255, 255, 255, 255))
        im.alpha_composite(with_alpha(lay, k))

    def objectives(self, im, t):
        for o in self.s.get("objectives", []):
            k = win(t, o["start"], o["end"], 0.25, 0.25)
            if not k:
                continue
            f = font("Bold", 44)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            tot = sum(d.textlength(p[0], font=f) for p in o["parts"])
            x, y = self.cx - tot / 2, 1160
            cols = {"w": (255, 255, 255), "p": (255, 62, 165), "b": (90, 190, 255)}
            for txt, c in o["parts"]:
                d.text((x, y), txt, font=f, fill=cols[c] + (255,), anchor="lm", stroke_width=4, stroke_fill=(0, 0, 0, 220))
                x += d.textlength(txt, font=f)
            im.alpha_composite(with_alpha(lay, k))

    def passed(self, im, t):
        p = self.s.get("passed")
        if not p:
            return
        k = win(t, p["at"], p["end"], 0.15, 0.3)
        if not k:
            return
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(band).rectangle((0, 820, W, 1080), fill=(0, 0, 0, 130))
        im.alpha_composite(with_alpha(band.filter(ImageFilter.GaussianBlur(28)), k))
        sc = 1.15 - 0.15 * ease_out(clamp((t - p["at"]) / 0.4))
        ttl = self.text_img("passed", p["title"], HUD(96), (255, 255, 255), (255, 255, 255), 0)
        self.place(im, ttl, self.cx, 915, a=k, scale=sc, maxw=880)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.text((self.cx, 1010), p["sub"], font=font("Bold", 40), fill=(255, 62, 165, 255), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 200))
        im.alpha_composite(with_alpha(lay, k * clamp((t - p["at"] - 0.25) / 0.3)))

    # ---------- POV-tekst (native TikTok-tekstblok) ----------
    def pov(self, im, t):
        p = self.s.get("pov")
        if not p:
            return
        k = win(t, p.get("start", 0), p["end"], 0.01, 0.3)
        if not k:
            return
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        f = font("ExtraBold", 46)
        y = VY + 80
        for l in p["lines"]:
            tw = d.textlength(l, font=f)
            d.rounded_rectangle((self.cx - tw / 2 - 24, y - 36, self.cx + tw / 2 + 24, y + 36), 14, fill=(255, 255, 255, 255))
            d.text((self.cx, y), l, font=f, fill=(10, 10, 10, 255), anchor="mm")
            y += 78
        im.alpha_composite(with_alpha(lay, k))

    # ---------- stuurrichting ----------
    def _load_yaw(self):
        h = self.s.get("hud", {})
        if not h.get("yaw"):
            return None
        y = json.load(open(os.path.join(self.base, h["yaw"])))
        import numpy as np
        hd = np.array(y["heading"], dtype=float)
        k = np.ones(15) / 15  # extra glad (1,5 s): handbewegingen eruit, bochten blijven
        pad = np.concatenate([np.full(7, hd[0]), hd, np.full(7, hd[-1])])
        hd = np.convolve(pad, k, mode="valid")
        fps = y["fps"]
        # positie op de kaart: rijden in de kijkrichting
        pos = [(700.0, 1100.0)]
        for i in range(1, len(hd)):
            r = math.radians(hd[i])
            x, yy = pos[-1]
            pos.append((x + 14 / fps * math.sin(r), yy - 14 / fps * math.cos(r)))
        return {"fps": fps, "h": hd, "pos": pos}

    def src_time(self, t):
        acc = self.s.get("presents", {}).get("end", 0)
        for a, b in self.s["shots"]:
            if t < acc + (b - a):
                return a + max(0.0, t - acc)
            acc += b - a
        return self.s["shots"][-1][1]

    def heading(self, ts):
        y = self.yaw
        i = max(0, min(len(y["h"]) - 1, int(ts * y["fps"])))
        return float(y["h"][i]), y["pos"][i]

    # ---------- HUD (opbouw: afgeronde minimap linksonder, roze route, afstand) ----------
    def hud(self, im, t):
        h = self.s.get("hud")
        if not h:
            return
        a = win(t, h["start"], h["end"], 0.4, 0.3)
        if not a:
            return
        if not hasattr(self, "_map"):
            from gta import GTA
            self._map = GTA._make_map(None)
        x0, y0, mw, mh = 50, 1225, 400, 180
        ts = self.src_time(t)
        if self.yaw:
            hdg, (cx, cy) = self.heading(ts)
            ahead, _ = self.heading(ts + 1.5)
        else:
            hdg, cx, cy, ahead = 0.0, 700, 1100 - t * 14, 0.0
        big = self._map.crop((int(cx - 320), int(cy - 320), int(cx + 320), int(cy + 320))).rotate(hdg, resample=Image.BICUBIC)
        c = big.width // 2
        m = big.crop((c - mw // 2, c - mh // 2 - 30, c + mw // 2, c + mh // 2 - 30))
        m = ImageEnhance.Brightness(m).enhance(0.8)
        md = ImageDraw.Draw(m)
        # roze route buigt mee met de bocht die eraan komt
        px, py = mw // 2, mh // 2 + 30
        bend = math.sin(math.radians(max(-80, min(80, ahead - hdg))))
        route = [(px, py), (px, py - 40), (px + 70 * bend, py - 95), (px + 150 * bend, py - 140), (px + 260 * bend, py - 170)]
        md.line(route, fill=(255, 70, 160, 255), width=9, joint="curve")
        # doel ligt buiten beeld: ruit op de rand van de kaart, waar de route het kader verlaat
        wx, wy = route[-1]
        for (xa, ya), (xb, yb) in zip(route, route[1:]):
            if not (16 <= xb <= mw - 16 and 16 <= yb <= mh - 16):
                for q in [i / 40 for i in range(41)]:
                    xx, yy = xa + (xb - xa) * q, ya + (yb - ya) * q
                    if not (16 <= xx <= mw - 16 and 16 <= yy <= mh - 16):
                        break
                    wx, wy = xx, yy
                break
        wx, wy = max(18, min(mw - 18, wx)), max(18, min(mh - 18, wy))
        md.polygon([(wx, wy - 14), (wx + 12, wy), (wx, wy + 14), (wx - 12, wy)], fill=(255, 62, 165, 255), outline=(255, 255, 255, 255))
        md.polygon([(px, py - 16), (px + 12, py + 12), (px, py + 4), (px - 12, py + 12)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        mask = Image.new("L", (mw, mh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, mw - 1, mh - 1), 28, fill=int(235 * a))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.paste(m, (x0, y0), mask)
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle((x0 - 2, y0 - 2, x0 + mw + 1, y0 + mh + 1), 30, outline=(255, 255, 255, int(150 * a)), width=3)
        k = clamp((t - h["start"]) / (h["end"] - h["start"]))
        dist = h["dist_m"] * (1 - k)
        txt = f"{dist / 1000:.1f} km".replace(".", ",") if dist >= 1000 else f"{int(dist // 10 * 10)} m"
        d.text((x0 + mw - 18, y0 + 20), txt, font=HUD(30), fill=(255, 255, 255, int(255 * a)), anchor="ra",
               stroke_width=4, stroke_fill=(0, 0, 0, int(200 * a)))
        if h.get("target"):
            d.text((x0 + 18, y0 + 20), h["target"].upper(), font=font("Bold", 22), fill=(255, 120, 190, int(255 * a)),
                   stroke_width=3, stroke_fill=(0, 0, 0, int(200 * a)))
        for i in range(5):
            sx, sy, r = 1000 - i * 40, VY + 50, 15
            pts = [(sx + (r if q % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + q * math.pi / 5),
                    sy + (r if q % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + q * math.pi / 5)) for q in range(10)]
            d.polygon(pts, fill=(0, 0, 0, int(80 * a)), outline=(255, 255, 255, int(200 * a)))
        im.alpha_composite(lay)

    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, VY), fill=(0, 0, 0, 255))
        d.rectangle((0, VY + VH, W, H), fill=(0, 0, 0, 255))
        self.presents(im, t)
        self.hud(im, t)
        self.pov(im, t)
        self.mission_card(im, t)
        self.objectives(im, t)
        self.passed(im, t)
        self.subtitles(im, t)
        self.cards(im, t)
        self.flashes(im, t)
        self.end(im, t)
        return im


def base_video(spec, src, out, tmp):
    """Zwart intro + shots (geknipt en gegrade) + zwart voor de eindkaart."""
    c = spec["source"]["crop"]
    pre, endlen = spec.get("presents", {}).get("end", 0), spec["duration"] - spec["end"]["at"]
    parts, fc = [], []
    if pre:
        fc.append(f"color=c=black:s={W}x{VH}:r={FPS}:d={pre}[pre]")
    for i, (a, b) in enumerate(spec["shots"]):
        fc.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,fps={FPS},crop={c[2]}:{c[3]}:{c[0]}:{c[1]},"
                  f"scale={W}:{VH}:flags=lanczos,{grade()},format=yuv420p[s{i}]")
        parts.append(f"[s{i}]")
    fc.append(f"color=c=black:s={W}x{VH}:r={FPS}:d={endlen}[post]")
    head = "[pre]" if pre else ""
    fc.append(f"{head}{''.join(parts)}[post]concat=n={len(parts) + 1 + (1 if pre else 0)}:v=1:a=0,format=yuv420p,"
              f"pad={W}:{H}:0:{VY}:black[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(fc), "-map", "[v]",
                    "-t", str(spec["duration"]), "-c:v", "libx264", "-crf", "14", "-preset", "fast", out], check=True)


def build_audio(spec, src, base, out_wav):
    a = spec["audio"]
    dur = spec["duration"]
    inputs = ["-i", os.path.join(base, a["music"])]
    ev = [(e["at"], os.path.join(SFX_DIR, e["file"] + ".mp3"), e.get("db", -6)) for e in a.get("sfx", [])]
    for _, f, _ in ev:
        inputs += ["-i", f]
    fc = [f"[0:a]atrim=start={a.get('music_offset', 0)},asetpts=PTS-STARTPTS,volume={a.get('music_gain', 1.0)},"
          f"afade=t=in:d=1.0,afade=t=out:st={dur - 1.8}:d=1.8,aformat=channel_layouts=stereo[m]"]
    labels = ["[m]"]
    for j, (tt, _, db) in enumerate(ev):
        ms = int(tt * 1000)
        fc.append(f"[{j + 1}:a]volume={db}dB,adelay={ms}|{ms},aformat=channel_layouts=stereo[e{j}]")
        labels.append(f"[e{j}]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]",
                    "-t", str(dur), "-ar", "48000", out_wav], check=True)


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path))
    base = os.path.dirname(os.path.abspath(spec_path))
    src = os.path.join(base, spec["source"]["file"])
    tmp = tempfile.mkdtemp()
    bv = os.path.join(tmp, "base.mp4")
    base_video(spec, src, bv, tmp)
    tr = Trailer(spec, base)
    if "--preview" in sys.argv:
        for ts in sys.argv[sys.argv.index("--preview") + 1:]:
            t = float(ts)
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", bv, "-frames:v", "1", "-f", "rawvideo",
                                  "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
            im = Image.frombytes("RGBA", (W, H), raw)
            im.alpha_composite(tr.frame(t))
            p = os.path.splitext(out)[0] + f"_t{t:05.1f}.png"
            im.convert("RGB").save(p)
            print(p)
        return
    wav = os.path.join(tmp, "a.wav")
    build_audio(spec, src, base, wav)
    n = int(spec["duration"] * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", bv, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]", "-map", "[v]", "-map", "2:a",
           "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(tr.frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
