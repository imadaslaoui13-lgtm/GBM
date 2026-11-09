"""Synthesises the soundtrack: upbeat corporate beat (120 BPM) + UI sfx synced to index.html.
Usage: python3 audio.py out.wav [--no-music]"""
import sys, wave
import numpy as np

SR, DUR = 48000, 25.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
music = np.zeros((N, 2))
sfx = np.zeros((N, 2))
BEAT = 0.5  # 120 BPM


def tt(d):
    return np.arange(int(SR * d)) / SR


def add(buf, t0, sig, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * l * 1.414
    buf[i:i + len(sig), 1] += sig * r * 1.414


def lp(sig, a):  # one-pole low-pass
    out = np.empty_like(sig); acc = 0.0
    for i, v in enumerate(sig):
        acc += a * (v - acc); out[i] = acc
    return out


def hp(sig):
    return np.diff(sig, prepend=0.0)


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ---------- instruments ----------
def kick():
    t = tt(0.4); f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7.5) + 0.25 * np.exp(-t * 300) * rng.standard_normal(len(t))


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    n = hp(hp(rng.standard_normal(len(t))))
    return n * np.exp(-t * (14 if open_ else 70)) * 0.18


def clap():
    t = tt(0.3); n = hp(rng.standard_normal(len(t)))
    env = np.exp(-t * 18)
    for d in (0.0, 0.012, 0.024):
        env += (t >= d) * np.exp(-np.clip(t - d, 0, None) * 120) * 0.7
    return n * env * 0.35


def bass(m, d):
    t = tt(d); f = note(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3))
    env = np.minimum(1, t / 0.01) * np.exp(-t * 2.5) * np.minimum(1, (d - t) / 0.03)
    return s * env * 0.32


def pluck(m, d=0.35):
    t = tt(d); f = note(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    return s * np.exp(-t * 9) * np.minimum(1, t / 0.004) * 0.1


def pad(ms, d):
    t = tt(d); s = np.zeros(len(t))
    for m in ms:
        for det in (-0.12, 0.12):
            s += np.sin(2 * np.pi * note(m + det) * t)
    env = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6)
    return s * env * 0.022


# progression (bars of 2s): C  G  Am  F
CH = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
ROOT = [36, 43, 45, 41]
bars = int(np.ceil(DUR / 2))
for b in range(bars):
    t0 = b * 2.0; c = b % 4
    add(music, t0, pad([m + 12 for m in CH[c]], 2.1))
    # plucky arpeggio in 8ths
    arp = [CH[c][0] + 12, CH[c][1] + 12, CH[c][2] + 12, CH[c][1] + 12]
    for i in range(8):
        add(music, t0 + i * 0.25, pluck(arp[i % 4]), pan=(-0.35 if i % 2 else 0.35))
    if b >= 1 and t0 < 23.5:  # drums + bass from bar 2 (warning light lands)
        for i in range(4):
            bt = t0 + i * BEAT
            if 19.0 <= bt < 19.75:  # short break so the approval chime lands
                continue
            add(music, bt, kick(), gain=0.85)
            add(music, bt + 0.25, hat(), pan=0.2)
            if i in (1, 3):
                add(music, bt, clap(), pan=-0.05)
        for i, m in enumerate([0, 0, 12, 0, 0, 12, 7, 0]):
            add(music, t0 + i * 0.25, bass(ROOT[c] + m, 0.22))
# final ring-out chord
add(music, 24.0, pad([72, 76, 79], 1.0), gain=2.0)
fade = np.ones(N); fs = int(23.6 * SR); fade[fs:] = np.linspace(1, 0, N - fs) ** 1.5
music *= fade[:, None]


# ---------- sfx ----------
def pop(f0=900, d=0.12):
    t = tt(d); f = f0 * (1 + 0.8 * np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * 0.45


def click(f0=2400):
    t = tt(0.03)
    return (np.sin(2 * np.pi * f0 * t) * 0.5 + 0.5 * hp(rng.standard_normal(len(t)))) * np.exp(-t * 180) * 0.35


def swoosh(d=0.45, up=True):
    t = tt(d); n = rng.standard_normal(len(t))
    k = t / d; a = (0.02 + 0.25 * (k if up else 1 - k))
    # sweep a one-pole low-pass cutoff
    out = np.empty_like(n); acc = 0.0; acc2 = 0.0
    for i, v in enumerate(n):
        c = a[i]; acc += c * (v - acc); acc2 += c * (acc - acc2); out[i] = acc - acc2 * 0.5
    env = np.sin(np.pi * k) ** 1.5
    return out * env * 0.9


def beep(f, d=0.14):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 14) * np.minimum(1, t / 0.003) * 0.28


def chime(fs, gap=0.07):
    out = np.zeros(int(SR * (0.9 + gap * len(fs))))
    for i, f in enumerate(fs):
        t = tt(0.9); s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.01 * f * t)) * np.exp(-t * 5) * 0.22
        j = int(i * gap * SR); out[j:j + len(s)] += s
    return out


def scan(d=0.95):
    t = tt(d); f = 500 + 900 * (t / d)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.08 + 0.05 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    return s * np.sin(np.pi * t / d)


def shutter():
    t = tt(0.12); n = hp(rng.standard_normal(len(t)))
    return n * (np.exp(-t * 90) + 0.6 * (t > 0.05) * np.exp(-np.clip(t - 0.05, 0, None) * 110)) * 0.4


def rise(d=0.8, f0=70, f1=110):
    t = tt(d); f = f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) * 0.25


E = [
    (0.10, swoosh(0.9), 0, 0.6),
    *[(0.7 + i * 0.08, click(3000), 0.3, 0.5) for i in range(4)],
    (1.55, pop(700), 0, 1.0), (1.62, beep(880), 0, 0.9), (1.80, beep(660), 0, 0.7),
    (3.30, swoosh(0.7), 0, 0.8),
    (4.45, click(2600), 0, 0.7),
    *[(5.0 + i * 0.16, click(2200 + i * 120), 0, 0.8) for i in range(6)],
    (6.18, click(1800), 0.1, 1.0), (6.22, pop(1100), 0.1, 0.8),
    (7.35, swoosh(0.6), 0, 0.8), (7.95, pop(820, 0.16), 0.1, 1.0), (8.72, pop(1300), 0.4, 0.8),
    (9.75, swoosh(0.6), 0, 0.7),
    *[(11.1 + i * 0.12, click(2800 + 60 * i), 0, 0.35) for i in range(6)],
    (12.0, pop(1000), 0.3, 0.6), (12.12, pop(1150), 0.35, 0.6), (12.24, pop(1300), 0.4, 0.6),
    (12.95, swoosh(0.7, up=False), 0, 0.7),
    (14.5, swoosh(0.95), -0.4, 0.9),
    (15.55, rise(0.85), 0, 1.0), (16.0, pop(760), -0.5, 0.9),
    (16.45, scan(), 0, 1.0), (17.12, beep(1320, 0.1), 0.2, 0.6),
    (17.50, shutter(), 0, 1.0), (17.66, swoosh(0.65), 0.5, 0.8),
    (18.32, chime([1568, 2093], 0.06), 0.4, 0.7),
    (18.65, swoosh(0.75), 0, 0.6),
    (19.6, click(2000), 0, 1.0),
    (19.78, chime([784, 988, 1175, 1568], 0.075), 0, 1.0),
    (20.9, swoosh(0.9, up=False), 0, 0.7),
    (21.7, swoosh(1.2), 0, 0.6), (22.0, rise(2.5, 55, 80), 0, 0.6),
]
for t0, sig, pan, g in E:
    add(sfx, t0, sig, pan, g)

MUSIC = 0.0 if '--no-music' in sys.argv else 0.9  # --no-music: only the UI sounds
mixd = music * MUSIC + sfx * 0.95
mixd /= np.max(np.abs(mixd)) * 1.12
pcm = (np.clip(mixd, -1, 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', sys.argv[1])
