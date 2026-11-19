#!/usr/bin/env python3
"""GTA-stijl renderer voor rijlesvideo's ("game-missie"-format).

Eigen ontwerp in de sfeer van open-world games: neon-zonsondergang, letterbox-intro,
missietitel, HUD (minimap, rijpunten, sterren), doelregels met gekleurde woorden,
"MISSIE GESLAAGD" en een eind-CTA. Geen logo's, fonts of muziek van bestaande games.

Gebruik:  python3 gta.py <spec.json> <out.mp4> [--preview SEC ...]
"""
import json, math, os, random, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import font, hexc, ease_out, ease_back, Renderer  # noqa: E402

W, H, FPS = 1080, 1920, 30
SE_FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../short-editing/engine/fonts")
SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../short-editing/assets/sfx")


def dfont(name, size):
    p = os.path.join(SE_FONTS, name)
    return ImageFont.truetype(p, size) if os.path.exists(p) else font("Black", size)


TITLE = lambda s: dfont("BowlbyOneSC.ttf", s)     # dikke displayletter voor titels
HUD = lambda s: dfont("ArchivoBlack.ttf", s)      # HUD-cijfers


def clamp(x):
    return max(0.0, min(1.0, x))


def win(t, a, b, fi=0.3, fo=0.3):
    """0..1 zichtbaarheid binnen [a, b] met fade-in en fade-out."""
    if t < a or t > b:
        return 0.0
    return min(ease_out((t - a) / fi) if fi else 1, ease_out((b - t) / fo) if fo else 1)


def with_alpha(img, a):
    if a >= 1:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return img


def gradient_text(text, fnt, top, bottom, stroke=10, stroke_col=(10, 6, 30), shadow=True):
    """Tekst met verticaal kleurverloop, dikke rand en schaduw (game-titelstijl)."""
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t_, r, b = tmp.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    w, h = r - l + 40, b - t_ + 40
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((20 - l, 20 - t_), text, font=fnt, fill=255)
    smask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(smask).text((20 - l, 20 - t_), text, font=fnt, fill=255, stroke_width=stroke, stroke_fill=255)
    grad = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        k = y / max(1, h - 1)
        gd.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)) + (255,))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh.paste((0, 0, 0, 170), (0, 0), smask)
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (0, 0))
    edge = Image.new("RGBA", (w, h), stroke_col + (255,))
    out.paste(edge, (0, 0), smask)
    out.paste(grad, (0, 0), mask)
    return out


def outlined(d, xy, text, fnt, fill, stroke=6, anchor="mm"):
    d.text(xy, text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=(8, 6, 20, fill[3] if len(fill) > 3 else 255), anchor=anchor)


class GTA:
    def __init__(self, spec, base):
        self.s, self.base = spec, base
        b = spec["brand"]
        self.primary, self.light = hexc(b["primary"]), hexc(b["light"])
        self.pink, self.orange, self.yellow = hexc("#FF4FA3"), hexc("#FF9A3C"), hexc("#FFD23F")
        self.green = hexc("#7CFF6B")
        self.logo = Image.open(os.path.join(base, b["logo"])).convert("RGBA") if b.get("logo") else None
        self.cx = spec["layout"].get("safe_cx", 470)
        self.mapimg = self._make_map()
        # icoontekenaar van de standaard-renderer hergebruiken
        self._icon = Renderer._icon.__get__(type("X", (), {"primary": self.primary})())
        self.title_cache = {}

    # ---------- minimap ----------
    def _make_map(self):
        rnd = random.Random(4)
        S = 1400
        m = Image.new("RGBA", (S, S), (34, 46, 40, 255))
        d = ImageDraw.Draw(m)
        for _ in range(40):  # bouwblokken
            x, y = rnd.randrange(S), rnd.randrange(S)
            d.rectangle((x, y, x + rnd.randrange(60, 160), y + rnd.randrange(60, 160)), fill=(44, 58, 52, 255))
        d.ellipse((900, 150, 1300, 450), fill=(40, 90, 140, 255))  # water
        for x in range(100, S, 230):
            d.line([(x, 0), (x + rnd.randrange(-60, 60), S)], fill=(150, 156, 160, 255), width=14)
        for y in range(60, S, 200):
            d.line([(0, y), (S, y + rnd.randrange(-50, 50))], fill=(150, 156, 160, 255), width=12)
        d.line([(700, S), (700, 0)], fill=(210, 214, 218, 255), width=22)  # hoofdweg
        return m

    def minimap(self, im, t, a):
        R = 118
        cxm, cym = 64 + R, 1150 + R
        prog = (t * 9) % 900
        cx, cy = 700, 1150 - prog
        ang = 6 * math.sin(t * 0.35)
        crop = self.mapimg.crop((int(cx - R * 1.6), int(cy - R * 1.6), int(cx + R * 1.6), int(cy + R * 1.6))).rotate(ang, resample=Image.BICUBIC)
        c = crop.width // 2
        crop = crop.crop((c - R, c - R, c + R, c + R))
        # doelmarkering (geel) boven in beeld
        dd = ImageDraw.Draw(crop)
        dd.ellipse((R - 10, 20, R + 10, 40), fill=self.yellow, outline=(0, 0, 0, 255), width=3)
        mask = Image.new("L", (2 * R, 2 * R), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * R - 1, 2 * R - 1), fill=int(235 * a))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.paste(crop, (cxm - R, cym - R), mask)
        d = ImageDraw.Draw(lay)
        d.ellipse((cxm - R - 5, cym - R - 5, cxm + R + 5, cym + R + 5), outline=(10, 10, 20, int(255 * a)), width=8)
        d.ellipse((cxm - R - 1, cym - R - 1, cxm + R + 1, cym + R + 1), outline=(255, 255, 255, int(120 * a)), width=2)
        # speler-pijl
        d.polygon([(cxm, cym - 18), (cxm + 13, cym + 14), (cxm, cym + 6), (cxm - 13, cym + 14)], fill=(255, 255, 255, int(255 * a)), outline=(0, 0, 0, int(255 * a)))
        # "N"
        outlined(d, (cxm, cym - R - 2), "N", HUD(26), (255, 255, 255, int(255 * a)), stroke=4)
        im.alpha_composite(lay)

    # ---------- HUD rechtsboven ----------
    def hud_top(self, im, t, a):
        s = self.s
        d = ImageDraw.Draw(im)
        pts = 0
        for p in s.get("points", []):
            if t >= p["at"]:
                pts += int(p["value"] * clamp((t - p["at"]) / 0.8))
        x = 1020
        outlined(d, (x, 214), f"{pts:,}".replace(",", ".") + " RP", HUD(54), self.green[:3] + (int(255 * a),), stroke=6, anchor="rm")
        outlined(d, (x, 262), "RIJPUNTEN", HUD(22), (255, 255, 255, int(220 * a)), stroke=4, anchor="rm")
        # 5 sterren, leeg = netjes gereden
        for i in range(5):
            sx, sy, r = x - 26 - i * 52, 318, 20
            pts_ = []
            for k in range(10):
                ang = -math.pi / 2 + k * math.pi / 5
                rr = r if k % 2 == 0 else r * 0.45
                pts_.append((sx + rr * math.cos(ang), sy + rr * math.sin(ang)))
            d.polygon(pts_, fill=(0, 0, 0, int(90 * a)), outline=(255, 255, 255, int(200 * a)), width=3)

    def popups(self, im, t):
        d = ImageDraw.Draw(im)
        for p in self.s.get("points", []):
            k = win(t, p["at"], p["at"] + 1.6, 0.2, 0.4)
            if k:
                y = 430 - int(40 * clamp((t - p["at"]) / 1.6))
                outlined(d, (1020, y), f"+{p['value']} RP", HUD(46), self.green[:3] + (int(255 * k),), stroke=6, anchor="rm")
                if p.get("label"):
                    outlined(d, (1020, y + 46), p["label"].upper(), HUD(24), (255, 255, 255, int(255 * k)), stroke=4, anchor="rm")

    # ---------- tekstblokken ----------
    def objective(self, im, t):
        for o in self.s.get("objectives", []):
            k = win(t, o["start"], o["end"], 0.25, 0.25)
            if not k:
                continue
            parts = o["parts"]  # [[tekst, "w"|"y"|"b"], ...]
            f = font("ExtraBold", 50)
            d0 = ImageDraw.Draw(im)
            tot = sum(d0.textlength(p[0], font=f) for p in parts)
            x = self.cx - tot / 2
            y = 1085
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            cols = {"w": (255, 255, 255), "y": self.yellow[:3], "b": self.light[:3], "p": self.pink[:3]}
            for txt, c in parts:
                d.text((x, y), txt, font=f, fill=cols[c] + (255,), stroke_width=6, stroke_fill=(8, 6, 20, 255), anchor="lm")
                x += d.textlength(txt, font=f)
            im.alpha_composite(with_alpha(lay, k))

    def helpbox(self, im, t):
        for hb in self.s.get("help", []):
            k = win(t, hb["start"], hb["end"], 0.2, 0.3)
            if not k:
                continue
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            f = font("SemiBold", 34)
            lines = hb["lines"]
            bw = max(d.textlength(l, font=f) for l in lines) + 60
            bh = 40 + 48 * len(lines)
            x0, y0 = 44, 180
            d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), 14, fill=(8, 8, 16, 200))
            for i, l in enumerate(lines):
                d.text((x0 + 30, y0 + 22 + i * 48), l, font=f, fill=(255, 255, 255, 255))
            im.alpha_composite(with_alpha(lay, k))

    def title(self, key, text, fnt, top, bottom, stroke=10):
        k = (key, text)
        if k not in self.title_cache:
            self.title_cache[k] = gradient_text(text, fnt, top, bottom, stroke)
        return self.title_cache[k]

    def place(self, im, img, cx, cy, a=1.0, scale=1.0, rot=0, maxw=900):
        scale = min(scale, maxw / img.width) if img.width * scale > maxw else scale
        if scale != 1.0:
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        if rot:
            img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(with_alpha(img, a), (int(cx - img.width / 2), int(cy - img.height / 2)))

    # ---------- intro ----------
    def intro(self, im, t):
        it = self.s["intro"]
        if t > it["end"]:
            return
        out = 1 - ease_out((t - (it["end"] - 0.4)) / 0.4) if t > it["end"] - 0.4 else 1
        # letterbox
        bh = int(250 * ease_out(t / 0.35) * out)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, bh), fill=(0, 0, 0, 255))
        d.rectangle((0, H - bh, W, H), fill=(0, 0, 0, 255))
        # POV-hook bovenin, als native TikTok-tekstblok
        hk = win(t, 0, it["end"], 0.15, 0.3)
        f = font("ExtraBold", 50)
        lines = it["hook"]
        y = 300
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for l in lines:
            tw = ld.textlength(l, font=f)
            ld.rounded_rectangle((self.cx - tw / 2 - 26, y - 38, self.cx + tw / 2 + 26, y + 38), 16, fill=(255, 255, 255, 255))
            ld.text((self.cx, y), l, font=f, fill=(10, 10, 10, 255), anchor="mm")
            y += 84
        im.alpha_composite(with_alpha(lay, hk))
        # grote titel met verloop
        tk = ease_back(clamp((t - 0.25) / 0.6))
        if tk > 0:
            ttl = self.title("intro", it["title"], TITLE(150), self.yellow[:3], self.pink[:3], 12)
            self.place(im, ttl, self.cx, 960, a=clamp(tk) * out, scale=0.85 + 0.15 * tk, rot=4)
            sub = self.title("introsub", it["sub"], TITLE(46), (255, 255, 255), self.light[:3], 6)
            self.place(im, sub, self.cx, 1110, a=clamp((t - 0.6) / 0.3) * out, rot=4)

    def mission_title(self, im, t):
        m = self.s["mission"]
        k = win(t, m["start"], m["end"], 0.35, 0.4)
        if not k:
            return
        ttl = self.title("mission", m["title"], TITLE(92), (255, 255, 255), self.yellow[:3], 9)
        self.place(im, ttl, self.cx, 800, a=k, scale=0.94 + 0.06 * ease_out((t - m["start"]) / 0.5))
        sub = self.title("missionsub", m["sub"], TITLE(40), self.light[:3], self.light[:3], 6)
        self.place(im, sub, self.cx, 905, a=k)

    def passed(self, im, t):
        p = self.s["passed"]
        if t < p["at"] or t > p["end"]:
            return
        k = win(t, p["at"], p["end"], 0.01, 0.5)
        # flits
        fl = 1 - clamp((t - p["at"]) / 0.35)
        if fl > 0:
            ov = Image.new("RGBA", (W, H), (255, 240, 220, int(170 * fl)))
            im.alpha_composite(ov)
        # band achter de tekst
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(band).rectangle((0, 700, W, 1010), fill=(0, 0, 0, int(120 * k)))
        im.alpha_composite(band.filter(ImageFilter.GaussianBlur(30)))
        sc = 1.25 - 0.25 * ease_back(clamp((t - p["at"]) / 0.5))
        ttl = self.title("passed", p["title"], TITLE(104), self.yellow[:3], self.orange[:3], 11)
        self.place(im, ttl, self.cx, 820, a=k, scale=sc)
        sub = self.title("passedsub", p["sub"], TITLE(50), (255, 255, 255), (255, 255, 255), 7)
        self.place(im, sub, self.cx, 935, a=k * clamp((t - p["at"] - 0.35) / 0.3))

    def outro(self, im, t):
        o = self.s["outro"]
        if t < o["at"]:
            return
        k = ease_out((t - o["at"]) / 0.4)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # neon-verloop over het beeld, zoals een laadscherm
        for y in range(0, H, 4):
            q = y / H
            col = tuple(int(a_ + (b_ - a_) * q) for a_, b_ in zip((40, 10, 90), (255, 80, 140)))
            d.rectangle((0, y, W, y + 4), fill=col + (int(165 * k),))
        im.alpha_composite(ov)
        small = self.title("o1", o["kicker"], TITLE(40), self.light[:3], self.light[:3], 6)
        self.place(im, small, self.cx, 420, a=k)
        big = self.title("o2", o["title"], TITLE(110), (255, 255, 255), self.yellow[:3], 11)
        self.place(im, big, self.cx, 560, a=k, scale=0.92 + 0.08 * ease_back(clamp((t - o["at"]) / 0.5)), rot=3)
        sub = self.title("o3", o["sub"], TITLE(44), (255, 255, 255), (255, 255, 255), 6)
        self.place(im, sub, self.cx, 690, a=k)
        # logo op witte kaart
        if self.logo:
            lk = ease_out((t - o["at"] - 0.3) / 0.4)
            lw = 480
            lh = int(self.logo.height * lw / self.logo.width)
            card = Image.new("RGBA", (lw + 60, lh + 50), (0, 0, 0, 0))
            ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 28, fill=(255, 255, 255, 255))
            card.alpha_composite(self.logo.resize((lw, lh), Image.LANCZOS), (30, 25))
            self.place(im, card, self.cx, 850, a=clamp(lk), rot=-2)
        # like / reageer / deel
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        im.alpha_composite(lay)
        for j, (kind, label) in enumerate(o["items"]):
            kk = ease_back((t - o["at"] - 0.7 - j * 0.2) / 0.45)
            if kk <= 0:
                continue
            a = min(1, kk)
            cx = self.cx + (j - 1) * 280
            y = 1130
            R, SS = 80, 4
            big = Image.new("RGBA", (2 * R * SS + 8, 2 * R * SS + 8), (0, 0, 0, 0))
            bd = ImageDraw.Draw(big)
            bc = R * SS + 4
            bd.ellipse((4, 4, 4 + 2 * R * SS, 4 + 2 * R * SS), fill=(255, 255, 255, 255), outline=(10, 6, 30, 255), width=6 * SS)
            self._icon(bd, kind, bc, bc, R * SS * (0.58 if kind == "like" else 0.62), self.primary[:3] + (255,))
            btn = big.resize((big.width // SS, big.height // SS), Image.LANCZOS)
            self.place(im, btn, cx, y, a=a, scale=max(0.01, kk))
            la = clamp((t - o["at"] - 0.9 - j * 0.2) / 0.25)
            d2 = ImageDraw.Draw(im)
            if la > 0:
                lab = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                outlined(ImageDraw.Draw(lab), (cx, y + 118), label.upper(), HUD(40), (255, 255, 255, 255), stroke=6)
                im.alpha_composite(with_alpha(lab, la))

    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hud = self.s["hud"]
        ha = win(t, hud["start"], hud["end"], 0.4, 0.4)
        if ha:
            self.minimap(im, t, ha)
            self.hud_top(im, t, ha)
        self.popups(im, t)
        self.helpbox(im, t)
        self.objective(im, t)
        self.mission_title(im, t)
        self.passed(im, t)
        self.outro(im, t)
        self.intro(im, t)
        return im


def vf_cam(spec):
    c = spec["source"]["crop"]
    # neon-zonsondergang: warme roze hooglichten, teal schaduwen, extra verzadiging, gloed en vignet
    return (f"crop={c[2]}:{c[3]}:{c[0]}:{c[1]},scale={W}:{H}:flags=lanczos,"
            "eq=contrast=1.22:saturation=1.5:brightness=-0.01:gamma=0.95,"
            "colorbalance=rs=-0.06:gs=0.02:bs=0.10:rm=0.06:bm=0.04:rh=0.12:gh=0.0:bh=0.06,"
            "curves=r='0/0 0.5/0.55 1/1':b='0/0.06 0.5/0.5 1/0.92',"
            "split[a][b];[b]gblur=sigma=22,eq=brightness=0.04[g];[a][g]blend=all_mode=screen:all_opacity=0.16,"
            "vignette=angle=PI/4.2")


def build_audio(spec, src, base, out_wav):
    a = spec["audio"]
    music = os.path.join(base, a["music"])
    ev = []  # (tijd, bestand, gain dB)
    for e in a.get("sfx", []):
        ev.append((e["at"], os.path.join(SFX_DIR, e["file"] + ".mp3"), e.get("db", -6)))
    inputs = ["-i", src, "-i", music]
    for _, f, _ in ev:
        inputs += ["-i", f]
    # eigen "missie geslaagd"-akkoord (C-majeur arpeggio + akkoord)
    sting = ("aevalsrc='0.22*(sin(2*PI*523.25*t)*lt(t,0.18)+sin(2*PI*659.25*t)*between(t,0.12,0.30)"
             "+sin(2*PI*783.99*t)*between(t,0.24,0.42)+(sin(2*PI*523.25*t)+sin(2*PI*659.25*t)+sin(2*PI*783.99*t)+0.6*sin(2*PI*1046.5*t))*gte(t,0.36)*exp(-1.6*(t-0.36)))'"
             ":d=2.6:s=44100")
    inputs += ["-f", "lavfi", "-i", sting]
    n_ev = len(ev)
    dur = spec["duration"]
    fc = [f"[0:a]volume={a.get('source_gain', 0.45)},aformat=channel_layouts=stereo[src]",
          f"[1:a]atrim=start={a.get('music_offset', 0)},asetpts=PTS-STARTPTS,volume={a.get('music_gain', 0.8)},"
          f"afade=t=in:d=0.6,afade=t=out:st={dur - 1.5}:d=1.5,aformat=channel_layouts=stereo[mus]"]
    labels = ["[src]", "[mus]"]
    for j, (tt, _, db) in enumerate(ev):
        ms = int(tt * 1000)
        fc.append(f"[{j + 2}:a]volume={db}dB,adelay={ms}|{ms},aformat=channel_layouts=stereo[e{j}]")
        labels.append(f"[e{j}]")
    sm = int(spec["passed"]["at"] * 1000)
    fc.append(f"[{n_ev + 2}:a]adelay={sm}|{sm},aformat=channel_layouts=stereo,volume=1.4[st]")
    labels.append("[st]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "[out]", "-t", str(dur), "-ar", "48000", out_wav], check=True)


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path))
    base = os.path.dirname(os.path.abspath(spec_path))
    src = os.path.join(base, spec["source"]["file"])
    g = GTA(spec, base)
    if "--preview" in sys.argv:
        for ts in sys.argv[sys.argv.index("--preview") + 1:]:
            t = float(ts)
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1",
                                  "-filter_complex", f"[0:v]{vf_cam(spec)}[v]", "-map", "[v]", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                                 capture_output=True, check=True).stdout
            im = Image.frombytes("RGBA", (W, H), raw)
            im.alpha_composite(g.frame(t))
            p = os.path.splitext(out)[0] + f"_t{t:05.1f}.png"
            im.convert("RGB").save(p)
            print(p)
        return
    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "a.wav")
    build_audio(spec, src, base, wav)
    n = int(spec["duration"] * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src,
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-filter_complex", f"[0:v]fps={FPS},{vf_cam(spec)}[cam];[cam][1:v]overlay=0:0:format=auto[v]",
           "-map", "[v]", "-map", "2:a", "-frames:v", str(n),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(g.frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
