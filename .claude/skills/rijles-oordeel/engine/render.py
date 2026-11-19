#!/usr/bin/env python3
"""Rijles-oordeel renderer.

Eén spec.json in, één verticale short (1080x1920, 30 fps, -14 LUFS) uit.
Gebruik:  python3 render.py <spec.json> <out.mp4> [--preview SEC ...]

Lagen (van onder naar boven):
  1. achtergrond (merkkleur)
  2. camerabeeld, uitgesneden via spec.source.crop en geschaald naar de videozone
  3. statische UI: header, hookregel, voortgangsbalk, footer
  4. dynamische UI: hook-intro, scènekaart, oordeel-stempel, poll
Geluid: origineel, plus zachte tik bij elke scènewissel en een dreun bij het oordeel.
"""
import json, math, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT_DIR = "/usr/share/fonts/opentype/inter"


def font(weight, size):
    for name in (f"Inter-{weight}.otf", "Inter-Bold.otf"):
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def hexc(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):  # lichte overshoot voor de stempel
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.4, 2.4
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def rounded(draw, box, r, fill, outline=None, width=0):
    draw.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


class Renderer:
    """Alle kleuren komen uit spec.brand, zodat elke rijschool zijn eigen huisstijl krijgt."""

    def __init__(self, spec, base="."):
        self.s = spec
        b = spec["brand"]
        g = lambda k, d: hexc(b.get(k, d))
        self.primary = g("primary", "#2410C4")
        self.light = g("light", "#71CEFA")
        self.white = hexc("#FFFFFF")
        self.head_bg = g("header_bg", "#FFFFFF")
        self.head_txt = g("header_text", b.get("primary", "#2410C4"))
        self.head_mut = g("header_muted", "#6B66A8")
        self.track = g("track", "#E4E2F6")
        self.fill = g("fill", b.get("primary", "#2410C4"))
        self.foot_bg = g("footer_bg", b.get("primary", "#2410C4"))
        self.card = g("card", b.get("primary", "#2410C4"))
        self.card_sub = g("card_sub", "#D4DAFF")
        self.acc = g("accent", b.get("light", "#71CEFA"))
        self.ov = g("overlay", "#0B0640")
        self.opt_a = g("option_a", b.get("light", "#71CEFA"))
        self.opt_b = g("option_b", "#FFFFFF")
        self.stamp_bg = g("stamp_bg", b.get("light", "#71CEFA"))
        self.stamp_txt = g("stamp_text", b.get("primary", "#2410C4"))
        self.bg = self.head_bg
        self.logo = None
        if b.get("logo"):
            lp = b["logo"] if os.path.isabs(b["logo"]) else os.path.join(base, b["logo"])
            self.logo = Image.open(lp).convert("RGBA")
        L = spec["layout"]
        self.vy, self.vh = L["video_y"], L["video_h"]
        self.cx = L.get("safe_cx", W // 2)  # midden van het vrije gebied (TikTok-knoppen rechts)
        self.cardbox = tuple(L["card"])
        self.scenes = spec["scenes"]
        self.dur = spec["duration"]
        self.static = self._static()

    # ---------- statische laag ----------
    def _static(self):
        s, im = self.s, Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, self.vy), fill=self.head_bg)
        if self.vy + self.vh < H:
            d.rectangle((0, self.vy + self.vh, W, H), fill=self.foot_bg)
        bf = s["layout"].get("bottom_fade")
        if bf:  # donkere overgang onderin, zodat de TikTok-caption leesbaar blijft
            y0 = bf.get("from", 1420)
            for y in range(y0, H):
                a = int(bf.get("alpha", 170) * ((y - y0) / (H - y0)) ** 0.8)
                d.line([(0, y), (W, y)], fill=self.ov[:3] + (a,))
        hd = s["header"]
        # logo links, of een tag als er geen logo is
        if self.logo:
            lh = hd.get("logo_h", 76)
            lw = int(self.logo.width * lh / self.logo.height)
            im.alpha_composite(self.logo.resize((lw, lh), Image.LANCZOS), (40, hd.get("logo_y", 22)))
        else:
            f = font("ExtraBold", 26)
            tag = hd.get("tag", "Rijles").upper()
            tw = d.textlength(tag, font=f)
            rounded(d, (48, 40, 48 + tw + 36, 82), 21, self.primary)
            d.text((48 + 18, 61), tag, font=f, fill=self.white, anchor="lm")
        # situatienummer als pill rechts
        if hd.get("right"):
            self._pill(d, hd["right"])
        d.text((44, hd.get("title_y", 112)), hd["title"], font=font("Black", hd.get("title_size", 58)), fill=self.head_txt)
        return self._footer(im, d)

    def _pill(self, d, text):
        f2 = font("Bold", 24)
        rt = text.upper()
        rw = d.textlength(rt, font=f2)
        tint = tuple(int(h + (l - h) * 0.28) for h, l in zip(self.head_bg[:3], self.light[:3])) + (255,)
        rounded(d, (W - 48 - rw - 36, 41, W - 48, 81), 20, tint)
        d.text((W - 48 - 18, 61), rt, font=f2, fill=self.head_txt, anchor="rm")

    def _footer(self, im, d):
        s = self.s
        # footer: slogan in delen met eigen kleur + tweede regel
        ft = s.get("footer")
        if not ft:
            return im
        fy = self.vy + self.vh + 56
        f3 = font("ExtraBold", 36)
        parts = ft.get("parts") or [[ft.get("handle", ""), "#FFFFFF"]]
        tot = sum(d.textlength(p[0], font=f3) for p in parts)
        x = (W - tot) / 2
        for txt, col in parts:
            d.text((x, fy), txt, font=f3, fill=hexc(col), anchor="lm")
            x += d.textlength(txt, font=f3)
        d.text((W // 2, fy + 48), ft["line"], font=font("Medium", 25), fill=self.card_sub, anchor="mm")
        return im

    # ---------- helpers ----------
    def scene_at(self, t):
        cur = 0
        for i, sc in enumerate(self.scenes):
            if t >= sc["start"]:
                cur = i
        return cur

    def progress(self, d, t):
        """Gesegmenteerde voortgangsbalk: één segment per scène (uit met layout.progress: false)."""
        if not self.s["layout"].get("progress", True):
            return
        x0, x1, y, gap = 48, W - 48, 202, 8
        n = len(self.scenes)
        segw = (x1 - x0 - gap * (n - 1)) / n
        for i, sc in enumerate(self.scenes):
            a = sc["start"]
            b = self.scenes[i + 1]["start"] if i + 1 < n else self.dur
            fx = x0 + i * (segw + gap)
            rounded(d, (fx, y, fx + segw, y + 8), 4, self.track)
            p = max(0.0, min(1.0, (t - a) / (b - a)))
            if p > 0:
                rounded(d, (fx, y, fx + max(8, segw * p), y + 8), 4, self.fill)

    def draw_card(self, im, t):
        i = self.scene_at(t)
        sc = self.scenes[i]
        x0, y0, x1, y1 = self.cardbox
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if self.s["layout"].get("card_band"):
            # kaart = de balk onder de video: camerabeeld blijft helemaal vrij
            ImageDraw.Draw(layer).rectangle((x0, y0, x1, y1), fill=self.card)
            x0, x1, y0 = x0 + 18, x1 - 18, y0 + 4
        else:
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 12, x1, y1 + 12), 28, fill=(5, 2, 40, 140))
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
            rounded(ImageDraw.Draw(layer), (x0, y0, x1, y1), 28, self.card, outline=hexc("#FFFFFF", 40), width=2)
        k = ease_out((t - sc["start"]) / 0.38)
        dy = int((1 - k) * 26)
        alpha = int(255 * k)
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(c)
        cd.rounded_rectangle((x0 + 30, y0 + 30, x0 + 38, y0 + 156), 4, fill=self.acc)
        cd.text((x0 + 62, y0 + 36 + dy), sc["label"].upper(), font=font("ExtraBold", 26), fill=self.acc)
        if self.s["layout"].get("counter", True):
            cd.text((x1 - 34, y0 + 36), f"{i + 1}/{len(self.scenes)}", font=font("SemiBold", 24), fill=self.card_sub, anchor="ra")
        cd.text((x0 + 60, y0 + 70 + dy), sc["title"], font=font("ExtraBold", 50), fill=self.white)
        cd.text((x0 + 62, y0 + 132 + dy), sc["sub"], font=font("Medium", 29), fill=self.card_sub)
        if alpha < 255:
            c.putalpha(c.getchannel("A").point(lambda v: v * alpha // 255))
        layer.alpha_composite(c)
        im.alpha_composite(layer)

    def _choice(self, d, box, letter, label, col, k, big):
        x0, y0, x1, y1 = box
        h = y1 - y0
        a = int(255 * k)
        d.rounded_rectangle(box, h // 2 if not big else 30, fill=self.primary[:3] + (int(240 * k),), outline=col[:3] + (a,), width=4 if not big else 5)
        if big:
            d.rounded_rectangle((x0 + 18, y0 + 18, x0 + h - 18, y1 - 18), 20, fill=col[:3] + (a,))
            d.text((x0 + h // 2, y0 + h // 2), letter, font=font("Black", 48), fill=self.primary[:3] + (a,), anchor="mm")
            d.text((x0 + h + 20, y0 + h // 2), label, font=font("ExtraBold", 46), fill=(255, 255, 255, a), anchor="lm")
        else:
            d.text((x0 + 46, y0 + h // 2), letter, font=font("Black", 40), fill=col[:3] + (a,), anchor="mm")
            d.text((x0 + 84, y0 + h // 2), label, font=font("Bold", 36), fill=(255, 255, 255, a), anchor="lm")

    def draw_hook(self, im, t):
        h = self.s["hook"]
        if t > h["end"]:
            return
        fade = 1 - ease_out((t - (h["end"] - 0.35)) / 0.35) if t > h["end"] - 0.35 else 1
        a = fade * ease_out(t / 0.3)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rectangle((0, self.vy, W, self.vy + self.vh), fill=self.ov[:3] + (int(160 * a),))
        cy = self.vy + 330
        s = 0.92 + 0.08 * ease_out(t / 0.4)
        for j, line in enumerate(h["lines"]):
            fill = self.light if j == len(h["lines"]) - 1 else self.white
            d.text((self.cx, cy + j * 112), line, font=font("Black", int(96 * s)), fill=fill[:3] + (int(255 * a),), anchor="mm")
        cy2 = cy + len(h["lines"]) * 112 + 40
        for j, (lab, col) in enumerate(((h["a"], self.opt_a), (h["b"], self.opt_b))):
            kk = ease_out((t - 0.25 - j * 0.12) / 0.3) * fade
            cx = self.cx + (-205 if j == 0 else 205)
            yy = cy2 + int((1 - kk) * 30)
            self._choice(d, (cx - 190, yy, cx + 190, yy + 92), "AB"[j], lab, col, kk, False)
        im.alpha_composite(ov)

    def draw_stamp(self, im, t):
        st = self.s.get("stamp")
        if not st or t < st["at"] or t > st["end"]:
            return
        k = ease_back((t - st["at"]) / 0.45)
        out = 1 - ease_out((t - (st["end"] - 0.3)) / 0.3) if t > st["end"] - 0.3 else 1
        a = max(0, min(1, (t - st["at"]) / 0.12)) * out
        txt = st["text"]
        f = font("Black", 64)
        tmp = Image.new("RGBA", (900, 220), (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        bw = int(d.textlength(txt, font=f) + 170)
        x0 = (900 - bw) // 2
        d.rounded_rectangle((x0, 50, x0 + bw, 170), 26, fill=self.stamp_bg[:3] + (245,), outline=self.white, width=5)
        cx, cy = x0 + 60, 110
        d.line([(cx - 18, cy), (cx - 4, cy + 16), (cx + 22, cy - 16)], fill=self.stamp_txt, width=11, joint="curve")
        d.text((x0 + 116, 110), txt, font=f, fill=self.stamp_txt, anchor="lm")
        sc = 1.6 - 0.6 * k
        tmp = tmp.resize((int(900 * sc), int(220 * sc)), Image.LANCZOS).rotate(-5, resample=Image.BICUBIC, expand=True)
        tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * a)))
        im.alpha_composite(tmp, (self.cx - tmp.width // 2, self.vy + 380 - tmp.height // 2))

    def draw_poll(self, im, t):
        p = self.s.get("poll")
        if not p or t < p["at"]:
            return
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        k0 = ease_out((t - p["at"]) / 0.35)
        d.rectangle((0, self.vy, W, self.vy + self.vh), fill=self.ov[:3] + (int(130 * k0),))
        d.text((self.cx, self.vy + 230), p["question"], font=font("Black", 70), fill=(255, 255, 255, int(255 * k0)), anchor="mm")
        for j, (lab, col) in enumerate(((p["a"], self.opt_a), (p["b"], self.opt_b))):
            kk = ease_out((t - p["at"] - 0.15 - j * 0.12) / 0.35)
            y = self.vy + 330 + j * 150 + int((1 - kk) * 40)
            pulse = 1 + 0.015 * math.sin((t - p["at"]) * 4 + j * 1.6)  # zachte puls lokt de comment uit
            bw, bh = int(760 * pulse), int(118 * pulse)
            x0 = self.cx - bw // 2
            self._choice(d, (x0, y, x0 + bw, y + bh), "AB"[j], lab, col, kk, True)
        im.alpha_composite(ov)

    def _icon(self, d, kind, cx, cy, r, col):
        """Eenvoudige vectoriconen: hart, tekstballon, deelpijl."""
        if kind == "like":
            pts = []
            for k in range(120):
                u = 2 * math.pi * k / 120
                x = 16 * math.sin(u) ** 3
                y = -(13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u))
                pts.append((cx + x * r / 17, cy + (y + 2) * r / 17))
            d.polygon(pts, fill=col)
        elif kind == "comment":
            w, h = r * 1.5, r * 1.05
            d.rounded_rectangle((cx - w / 2, cy - h / 2 - r * 0.12, cx + w / 2, cy + h / 2 - r * 0.12), int(r * 0.3), fill=col)
            d.polygon([(cx - w * 0.28, cy + h / 2 - r * 0.2), (cx - w * 0.05, cy + h / 2 - r * 0.2), (cx - w * 0.36, cy + h / 2 + r * 0.32)], fill=col)
            for k in (-1, 0, 1):
                d.ellipse((cx + k * r * 0.38 - r * 0.1, cy - r * 0.22, cx + k * r * 0.38 + r * 0.1, cy - r * 0.02), fill=self.primary)
        else:  # share: TikTok-stijl, gevulde pijl met spitse staart linksonder
            ox, oy = cx - 0.02 * r, cy + 0.02 * r
            def bez(p0, c, p1, n=40):
                return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0],
                         (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]) for u in (k / n for k in range(n + 1))]
            pts = [(0.12, -0.78), (0.86, -0.16), (0.12, 0.44), (0.12, 0.10)]
            pts += bez((0.12, 0.10), (-0.42, 0.02), (-0.84, 0.62))[1:]   # holle onderkant naar de staart
            pts += bez((-0.84, 0.62), (-0.78, -0.44), (0.12, -0.42))[1:]  # bolle bovenkant terug
            d.polygon([(ox + x * r, oy + y * r) for x, y in pts], fill=col)

    def draw_cta(self, im, t):
        c = self.s.get("cta")
        if not c or t < c["at"]:
            return
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        k0 = ease_out((t - c["at"]) / 0.35)
        d.rectangle((0, self.vy, W, self.vy + self.vh), fill=self.ov[:3] + (int(150 * k0),))
        ty = self.vy + 250
        for j, line in enumerate(c["lines"]):
            col = self.light if j == len(c["lines"]) - 1 else self.white
            d.text((self.cx, ty + j * 92 + int((1 - k0) * 20)), line, font=font("Black", 78), fill=col[:3] + (int(255 * k0),), anchor="mm")
        n = len(c["items"])
        gap = 300
        y = ty + len(c["lines"]) * 92 + 170
        for j, (kind, label) in enumerate(c["items"]):
            kk = ease_back((t - c["at"] - 0.35 - j * 0.22) / 0.45)
            if kk <= 0:
                continue
            # eigen laag per knop: lage alpha mag geen gat slaan in de donkere laag
            im.alpha_composite(ov)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            a = int(255 * min(1, kk))
            cx = self.cx + int((j - (n - 1) / 2) * gap)
            # om de beurt een korte "tik" zodat het oog meegaat
            beat = (t - c["at"] - 1.2) % (0.6 * n)
            pop = 1 + (0.08 * math.sin(math.pi * beat / 0.6) if j * 0.6 <= beat < (j + 1) * 0.6 and t - c["at"] > 1.2 else 0)
            r = int(92 * kk * pop)
            # 4x supersampling voor gladde randen
            SS, R = 4, max(r, 1)
            big = Image.new("RGBA", (2 * R * SS + 8, 2 * R * SS + 8), (0, 0, 0, 0))
            bd = ImageDraw.Draw(big)
            bc = R * SS + 4
            bd.ellipse((4, 4, 4 + 2 * R * SS, 4 + 2 * R * SS), fill=self.light[:3] + (255,), outline=(255, 255, 255, 255), width=5 * SS)
            self._icon(bd, kind, bc, bc, R * SS * (0.58 if kind == "like" else 0.62), self.primary[:3] + (255,))
            small = big.resize((big.width // SS, big.height // SS), Image.LANCZOS)
            if a < 255:
                small.putalpha(small.getchannel("A").point(lambda v: v * a // 255))
            ov.alpha_composite(small, (cx - small.width // 2, y - small.height // 2))
            la = int(255 * max(0.0, min(1.0, (t - c["at"] - 0.55 - j * 0.22) / 0.25)))
            d.text((cx, y + 135), label, font=font("ExtraBold", 44), fill=(255, 255, 255, la), anchor="mm")
        im.alpha_composite(ov)

    def frame(self, t):
        im = self.static.copy()
        d = ImageDraw.Draw(im)
        self.progress(d, t)
        self.draw_hook(im, t)
        self.draw_stamp(im, t)
        self.draw_poll(im, t)
        self.draw_cta(im, t)
        self.draw_card(im, t)
        return im


def build_audio(spec, src, out_wav):
    """Origineel geluid + tik per scènewissel + dreun bij het oordeel, genormaliseerd naar -14 LUFS."""
    ticks = [sc["start"] for sc in spec["scenes"][1:]] if spec.get("audio", {}).get("ticks", True) else []
    parts, inputs = [], ["-i", src]
    tick = "aevalsrc='0.35*sin(2*PI*1800*t)*exp(-60*t)':d=0.12:s=44100"
    thud = "aevalsrc='0.9*sin(2*PI*(70+90*exp(-25*t))*t)*exp(-9*t)':d=0.5:s=44100"
    events = [(tt, tick) for tt in ticks]
    if spec.get("stamp"):
        events.append((spec["stamp"]["at"], thud))
    for _, e in events:
        inputs += ["-f", "lavfi", "-i", e]
    fc = [f"[0:a]volume={spec.get('audio', {}).get('source_gain', 1.0)}[a0]"]
    labels = ["[a0]"]
    for j, (tt, _) in enumerate(events, start=1):
        ms = int(tt * 1000)
        fc.append(f"[{j}:a]adelay={ms}|{ms},aformat=channel_layouts=stereo[e{j}]")
        labels.append(f"[e{j}]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "[out]", "-t", str(spec["duration"]), "-ar", "48000", out_wav], check=True)


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path))
    base = os.path.dirname(os.path.abspath(spec_path))
    src = spec["source"]["file"]
    if not os.path.isabs(src):
        src = os.path.join(base, src)
    r = Renderer(spec, base)

    if "--preview" in sys.argv:
        for ts in sys.argv[sys.argv.index("--preview") + 1:]:
            t = float(ts)
            fr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1",
                                 "-vf", vf_cam(spec), "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                                capture_output=True, check=True).stdout
            base_im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            cam = Image.frombytes("RGBA", (W, spec["layout"]["video_h"]), fr)
            base_im.paste(cam, (0, spec["layout"]["video_y"]))
            base_im.alpha_composite(r.frame(t))
            p = os.path.splitext(out)[0] + f"_t{t:05.1f}.png"
            base_im.convert("RGB").save(p)
            print(p)
        return

    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "a.wav")
    build_audio(spec, src, wav)
    n = int(spec["duration"] * FPS)
    L = spec["layout"]
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-i", src,
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-filter_complex",
           f"color=c=black:s={W}x{H}:r={FPS}[bg];"
           f"[0:v]fps={FPS},{vf_cam(spec)}[cam];"
           f"[bg][cam]overlay=0:{L['video_y']}:shortest=1[b];[b][1:v]overlay=0:0:format=auto[v]",
           "-map", "[v]", "-map", "2:a", "-frames:v", str(n),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(r.frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    if p.returncode:
        sys.exit(p.returncode)
    print(out)


def vf_cam(spec):
    c, L = spec["source"]["crop"], spec["layout"]
    g = spec.get("grade", {"contrast": 1.06, "saturation": 1.12, "brightness": 0.01})
    return (f"crop={c[2]}:{c[3]}:{c[0]}:{c[1]},scale={W}:{L['video_h']}:flags=lanczos,"
            f"eq=contrast={g['contrast']}:saturation={g['saturation']}:brightness={g['brightness']},"
            f"unsharp=5:5:0.6")


if __name__ == "__main__":
    main()
