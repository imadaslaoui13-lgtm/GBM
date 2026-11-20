#!/usr/bin/env python3
"""Schat de stuurrichting (heading, graden) uit beeldbeweging met fasecorrelatie.

Gebruik: python3 yaw.py <video> <out.json> [--fov 70] [--rows 0.05 0.40]
Meet de horizontale verschuiving van de omgeving door de voorruit (bovenste deel van het beeld).
Omgeving schuift naar links = auto draait naar rechts (heading neemt toe).
"""
import json, subprocess, sys
import numpy as np

FPS, WS = 10, 192


def frames(src):
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h = int(info[0]), int(info[1])
    hs = int(h * WS / w)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS},scale={WS}:{hs},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, hs, WS).astype(np.float32)
    return arr


def shift(a, b):
    win = np.hanning(a.shape[1])[None, :] * np.hanning(a.shape[0])[:, None]
    A, B = np.fft.fft2((a - a.mean()) * win), np.fft.fft2((b - b.mean()) * win)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-6
    r = np.fft.ifft2(R).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    if x > a.shape[1] // 2:
        x -= a.shape[1]
    return x, r.max()


def main():
    src, out = sys.argv[1], sys.argv[2]
    fov = float(sys.argv[sys.argv.index("--fov") + 1]) if "--fov" in sys.argv else 70.0
    r0, r1 = (0.05, 0.40)
    if "--rows" in sys.argv:
        i = sys.argv.index("--rows")
        r0, r1 = float(sys.argv[i + 1]), float(sys.argv[i + 2])
    F = frames(src)
    h = F.shape[1]
    top = F[:, int(h * r0):int(h * r1), :]
    rates = [0.0]
    for i in range(1, len(top)):
        dx, conf = shift(top[i], top[i - 1])
        # outliers (schokken, ruitenwisser) dempen
        dx = float(np.clip(dx, -12, 12)) if conf > 0.05 else 0.0
        rates.append(-dx * fov / WS)
    rates = np.array(rates)
    k = np.ones(5) / 5  # glad maken (0,5 s)
    rates = np.convolve(rates, k, mode="same")
    heading = np.cumsum(rates)
    json.dump({"fps": FPS, "heading": [round(float(v), 2) for v in heading]}, open(out, "w"))
    print(f"{len(heading)} samples, heading min {heading.min():.0f} max {heading.max():.0f}")
    for s in range(0, len(heading), FPS):
        print(f"{s / FPS:4.0f}s {heading[s]:7.1f}")


if __name__ == "__main__":
    main()
