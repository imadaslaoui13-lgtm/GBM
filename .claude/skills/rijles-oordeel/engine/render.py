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
    def __init__(self, spec):
        self.s = spec
        b = spec["brand"]
        self.bg = hexc(b.get("bg", "#0E141B"))
        self.card = hexc(b.get("card", "#121B24"))
        self.acc = hexc(b.get("accent", "#C6F432"))
        self.txt = hexc("#FFFFFF")
        self.mut = hexc(b.get("muted", "#9AA7B4"))
        self.good = hexc(b.get("good", "#2BD576"))
        self.bad = hexc(b.get("bad", "#FF5A5F"))
        L = spec["layout"]
        self.vy, self.vh = L["video_y"], L["video_h"]
        self.cardbox = tuple(L["card"])
        self.scenes = spec["scenes"]
        self.dur = spec["duration"]
        self.static = self._static()

    # ---------- statische laag ----------
    def _static(self):
        s, im = self.s, Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, self.vy), fill=self.bg)
        d.rectangle((0, self.vy + self.vh, W, H), fill=self.bg)
        # pill + situatienummer
        f = font("ExtraBold", 26)
        tag = s["header"]["tag"].upper()
        tw = d.textlength(tag, font=f)
        rounded(d, (48, 40, 48 + tw + 36, 82), 21, self.acc)
        d.text((48 + 18, 61), tag, font=f, fill=self.bg, anchor="lm")
        f2 = font("SemiBold", 26)
        d.text((W - 48, 61), s["header"]["right"], font=f2, fill=self.mut, anchor="rm")
        # kopregel
        f3 = font("Black", 60)
        d.text((46, 104), s["header"]["title"], font=f3, fill=self.txt)
        # footer
        ff = font("SemiBold", 30)
        fy = self.vy + self.vh + 52
        d.text((W // 2, fy), s["footer"]["handle"], font=ff, fill=self.txt, anchor="mm")
        d.text((W // 2, fy + 44), s["footer"]["line"], font=font("Medium", 24), fill=self.mut, anchor="mm")
        return im

    # ---------- helpers ----------
    def scene_at(self, t):
        cur = 0
        for i, sc in enumerate(self.scenes):
            if t >= sc["start"]:
                cur = i
        return cur

    def progress(self, d, t):
        """Gesegmenteerde voortgangsbalk: één segment per scène."""
        x0, x1, y, gap = 48, W - 48, 198, 8
        n = len(self.scenes)
        segw = (x1 - x0 - gap * (n - 1)) / n
        for i, sc in enumerate(self.scenes):
            a = sc["start"]
            b = self.scenes[i + 1]["start"] if i + 1 < n else self.dur
            fx = x0 + i * (segw + gap)
            rounded(d, (fx, y, fx + segw, y + 8), 4, hexc("#FFFFFF", 45))
            p = max(0.0, min(1.0, (t - a) / (b - a)))
            if p > 0:
                rounded(d, (fx, y, fx + max(8, segw * p), y + 8), 4, self.acc)

    def draw_card(self, im, t):
        i = self.scene_at(t)
        sc = self.scenes[i]
        x0, y0, x1, y1 = self.cardbox
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # schaduw
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x1, y1 + 10), 28, fill=(0, 0, 0, 150))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
        rounded(d, (x0, y0, x1, y1), 28, self.card, outline=hexc("#FFFFFF", 28), width=2)
        # inhoud animeert in bij elke wissel
        k = ease_out((t - sc["start"]) / 0.38) if i > 0 or t > 0.05 else 1.0
        if i == 0:
            k = ease_out((t - 0.0) / 0.38)
        dy = int((1 - k) * 26)
        alpha = int(255 * k)
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(c)
        kind = sc.get("kind", "step")
        col = {"verdict": self.good, "poll": self.acc}.get(kind, self.acc)
        cd.rounded_rectangle((x0 + 30, y0 + 30, x0 + 38, y1 - 30), 4, fill=col)
        fl = font("ExtraBold", 26)
        cd.text((x0 + 62, y0 + 36 + dy), sc["label"].upper(), font=fl, fill=col)
        step = f"{i + 1}/{len(self.scenes)}"
        cd.text((x1 - 34, y0 + 36), step, font=font("SemiBold", 24), fill=self.mut, anchor="ra")
        ft = font("ExtraBold", 50)
        cd.text((x0 + 60, y0 + 70 + dy), sc["title"], font=ft, fill=self.txt)
        fs = font("Medium", 29)
        cd.text((x0 + 62, y0 + 132 + dy), sc["sub"], font=fs, fill=self.mut)
        if alpha < 255:
            a = c.getchannel("A").point(lambda v: v * alpha // 255)
            c.putalpha(a)
        layer.alpha_composite(c)
        im.alpha_composite(layer)

    def draw_hook(self, im, t):
        h = self.s["hook"]
        if t > h["end"]:
            return
        fade = 1 - ease_out((t - (h["end"] - 0.35)) / 0.35) if t > h["end"] - 0.35 else 1
        inn = ease_out(t / 0.3)
        a = fade * inn
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rectangle((0, self.vy, W, self.vy + self.vh), fill=(8, 12, 16, int(150 * a)))
        cy = self.vy + 330
        f1 = font("Black", 96)
        s = 0.92 + 0.08 * ease_out(t / 0.4)
        for j, line in enumerate(h["lines"]):
            fill = self.acc if j == len(h["lines"]) - 1 else self.txt
            f = font("Black", int(96 * s))
            d.text((W // 2, cy + j * 112), line, font=f, fill=fill[:3] + (int(255 * a),), anchor="mm")
        # A/B-chips
        cy2 = cy + len(h["lines"]) * 112 + 40
        for j, (lab, col) in enumerate(((h["a"], self.good), (h["b"], self.bad))):
            kk = ease_out((t - 0.25 - j * 0.12) / 0.3) * fade
            cx = W // 2 + (-205 if j == 0 else 205)
            bw, bh = 380, 92
            yy = cy2 + int((1 - kk) * 30)
            d.rounded_rectangle((cx - bw // 2, yy, cx + bw // 2, yy + bh), 46,
                                fill=hexc("#0E141B", int(230 * kk)), outline=col[:3] + (int(255 * kk),), width=4)
            d.text((cx - bw // 2 + 46, yy + bh // 2), "AB"[j], font=font("Black", 40), fill=col[:3] + (int(255 * kk),), anchor="mm")
            d.text((cx - bw // 2 + 84, yy + bh // 2), lab, font=font("Bold", 36), fill=(255, 255, 255, int(255 * kk)), anchor="lm")
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
        tw = d.textlength(txt, font=f)
        bw = int(tw + 170)
        x0 = (900 - bw) // 2
        d.rounded_rectangle((x0, 50, x0 + bw, 170), 26, fill=self.good[:3] + (235,))
        # vinkje
        cx, cy = x0 + 60, 110
        d.line([(cx - 18, cy), (cx - 4, cy + 16), (cx + 22, cy - 16)], fill=(14, 20, 27, 255), width=11, joint="curve")
        d.text((x0 + 116, 110), txt, font=f, fill=(14, 20, 27, 255), anchor="lm")
        sc = 1.6 - 0.6 * k
        tmp = tmp.resize((int(900 * sc), int(220 * sc)), Image.LANCZOS).rotate(-5, resample=Image.BICUBIC, expand=True)
        al = tmp.getchannel("A").point(lambda v: int(v * a))
        tmp.putalpha(al)
        im.alpha_composite(tmp, ((W - tmp.width) // 2, self.vy + 380 - tmp.height // 2))

    def draw_poll(self, im, t):
        p = self.s.get("poll")
        if not p or t < p["at"]:
            return
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        k0 = ease_out((t - p["at"]) / 0.35)
        d.rectangle((0, self.vy, W, self.vy + self.vh), fill=(8, 12, 16, int(120 * k0)))
        d.text((W // 2, self.vy + 230), p["question"], font=font("Black", 70), fill=(255, 255, 255, int(255 * k0)), anchor="mm")
        for j, (lab, col) in enumerate(((p["a"], self.good), (p["b"], self.bad))):
            kk = ease_out((t - p["at"] - 0.15 - j * 0.12) / 0.35)
            y = self.vy + 330 + j * 150 + int((1 - kk) * 40)
            # zachte "puls" op de knoppen om de comment uit te lokken
            pulse = 1 + 0.015 * math.sin((t - p["at"]) * 4 + j * 1.6)
            bw, bh = int(760 * pulse), int(118 * pulse)
            x0 = (W - bw) // 2
            d.rounded_rectangle((x0, y, x0 + bw, y + bh), 30, fill=hexc("#0E141B", int(235 * kk)), outline=col[:3] + (int(255 * kk),), width=5)
            d.rounded_rectangle((x0 + 18, y + 18, x0 + 18 + bh - 36, y + bh - 18), 20, fill=col[:3] + (int(255 * kk),))
            d.text((x0 + 18 + (bh - 36) // 2, y + bh // 2), "AB"[j], font=font("Black", 48), fill=(14, 20, 27, int(255 * kk)), anchor="mm")
            d.text((x0 + bh + 20, y + bh // 2), lab, font=font("ExtraBold", 46), fill=(255, 255, 255, int(255 * kk)), anchor="lm")
        im.alpha_composite(ov)

    def frame(self, t):
        im = self.static.copy()
        d = ImageDraw.Draw(im)
        self.progress(d, t)
        self.draw_hook(im, t)
        self.draw_stamp(im, t)
        self.draw_poll(im, t)
        self.draw_card(im, t)
        return im


def build_audio(spec, src, out_wav):
    """Origineel geluid + tik per scènewissel + dreun bij het oordeel, genormaliseerd naar -14 LUFS."""
    ticks = [sc["start"] for sc in spec["scenes"][1:]]
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
    r = Renderer(spec)

    if "--preview" in sys.argv:
        for ts in sys.argv[sys.argv.index("--preview") + 1:]:
            t = float(ts)
            fr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1",
                                 "-vf", vf_cam(spec), "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                                capture_output=True, check=True).stdout
            base_im = Image.new("RGBA", (W, H), r.bg)
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
           f"color=c={spec['brand'].get('bg', '#0E141B')}:s={W}x{H}:r={FPS}[bg];"
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
