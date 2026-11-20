#!/usr/bin/env python3
"""Trailer-stijl renderer: rijlesbeelden als filmische game-trailer.

Eigen ontwerp in de sfeer van moderne open-world trailers: paars-oranje grade, filmkorrel,
4:5-beeld met zwarte balken, snelle shots, filmische ondertitels, personagekaart en een
collage-eindkaart met getekende panelen. Geen logo's, fonts of muziek van bestaande games.

Gebruik:  python3 trailer.py <spec.json> <out.mp4> [--preview SEC ...]
"""
import json, math, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageEnhance

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

    def logo_mark(self):
        """BVO als game-titellogo: dikke letters met diagonaal zonsondergang-verloop, L-plaatje ervoor."""
        if "mark" in self.cache:
            return self.cache["mark"]
        e = self.s["end"]
        f = HUD(330)
        txt = e.get("mark", "BVO")
        tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
        l, t_, r, b = tmp.textbbox((0, 0), txt, font=f)
        tw, th = r - l, b - t_
        lw = int(th * 0.62)  # L-plaatje
        W2, H2 = lw + 30 + tw + 40, th + 40
        mask = Image.new("L", (W2, H2), 0)
        ImageDraw.Draw(mask).text((lw + 30 - l + 20, 20 - t_), txt, font=f, fill=255)
        grad = Image.new("RGBA", (W2, H2))
        gp = grad.load()
        stops = [(120, 50, 230), (255, 70, 150), (255, 150, 70), (255, 214, 90)]
        for y in range(H2):
            for x in range(0, W2, 2):
                q = max(0.0, min(1.0, (x / W2) * 0.65 + (y / H2) * 0.35))
                seg = min(2, int(q * 3)); k = q * 3 - seg
                c = tuple(int(stops[seg][i] + (stops[seg + 1][i] - stops[seg][i]) * k) for i in range(3)) + (255,)
                gp[x, y] = c
                if x + 1 < W2:
                    gp[x + 1, y] = c
        out = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        sh = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        sh.paste((20, 6, 40, 150), (0, 0), mask)
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)), (0, 10))
        out.paste(grad, (0, 0), mask)
        d = ImageDraw.Draw(out)
        y0 = 20 + (th - lw) // 2 + int(th * 0.08)
        d.rounded_rectangle((20, y0, 20 + lw, y0 + lw), int(lw * 0.14), fill=(255, 255, 255, 255))
        d.text((20 + lw / 2, y0 + lw / 2), "L", font=HUD(int(lw * 0.72)), fill=self.primary[:3] + (255,), anchor="mm")
        self.cache["mark"] = out
        return out

    def end(self, im, t):
        e = self.s["end"]
        if t < e["at"] or not self.collage:
            return
        k = ease_out((t - e["at"]) / 0.35)
        zoom = 1.0 + 0.03 * clamp((t - e["at"]) / 5)
        col = self.collage.resize((int(W * zoom), int(H * zoom)), Image.BILINEAR)
        col = col.crop(((col.width - W) // 2, (col.height - H) // 2, (col.width - W) // 2 + W, (col.height - H) // 2 + H))
        im.alpha_composite(with_alpha(col, k))
        mk = ease_back(clamp((t - e["at"] - 0.2) / 0.7))
        if mk > 0:
            self.place(im, self.logo_mark(), self.cx, 620, a=clamp(mk), scale=0.8 + 0.2 * mk, maxw=860)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.text((self.cx, 820), " ".join(e.get("line1", "VERKEERSSCHOOL")), font=font("ExtraBold", 44), fill=(255, 255, 255, 255),
               anchor="mm", stroke_width=3, stroke_fill=(40, 10, 70, 255))
        d.text((self.cx, 880), e.get("line2", "voor 't Gooi en omstreken"), font=font("SemiBold", 32), fill=(255, 255, 255, 230),
               anchor="mm", stroke_width=2, stroke_fill=(40, 10, 70, 200))
        im.alpha_composite(with_alpha(lay, clamp((t - e["at"] - 0.7) / 0.35)))
        sub = self.text_img("endsub", e["sub"], TITLE(52), (255, 255, 255), SUNSET[0], 7)
        self.place(im, sub, self.cx, 1010, a=clamp((t - e["at"] - 1.0) / 0.3), rot=2, maxw=820)
        for j, (kind, label) in enumerate(e["items"]):
            kk = ease_back((t - e["at"] - 1.3 - j * 0.18) / 0.45)
            if kk <= 0:
                continue
            R, SS = 60, 4
            big = Image.new("RGBA", (2 * R * SS + 8, 2 * R * SS + 8), (0, 0, 0, 0))
            bd = ImageDraw.Draw(big)
            bc = R * SS + 4
            bd.ellipse((4, 4, 4 + 2 * R * SS, 4 + 2 * R * SS), fill=(255, 255, 255, 255), outline=(40, 10, 70, 255), width=6 * SS)
            self._icon(bd, kind, bc, bc, R * SS * (0.58 if kind == "like" else 0.62), self.primary[:3] + (255,))
            btn = big.resize((big.width // SS, big.height // SS), Image.LANCZOS)
            cx = self.cx + (j - 1) * 210
            self.place(im, btn, cx, 1180, a=min(1, kk), scale=max(0.01, kk), maxw=2000)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((cx, 1272), label.upper(), font=HUD(30), fill=(255, 255, 255, 255), anchor="mm",
                                     stroke_width=4, stroke_fill=(40, 10, 70, 255))
            im.alpha_composite(with_alpha(lay, clamp((t - e["at"] - 1.5 - j * 0.18) / 0.25)))

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
