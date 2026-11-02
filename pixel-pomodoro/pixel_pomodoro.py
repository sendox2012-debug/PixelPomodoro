#!/usr/bin/env python3
"""Pixel Pomodoro: a pixel-art pomodoro timer in pure tkinter.

Everything (fonts, buttons, mascot) is drawn on a Canvas out of "logical
pixels", so it looks identical on any system and needs no extra packages
besides python + tk.

Keys: Space start/pause | R reset | S skip | 1/2/3 focus/break/long
      Up/Down (or +/-) change minutes while stopped | Q quit
"""
import argparse
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import time
import wave
import zlib
from datetime import date
from pathlib import Path

APP_ID = "pixel-pomodoro"
APP_NAME = "Pixel Pomodoro"
W, H = 120, 172  # logical size
S = 4  # screen pixels per logical pixel (chosen at startup)

# ------------------------------------------------------------------ colours
BG = "#150a2b"
PANEL = "#241049"
PANEL_IN = "#2e1760"
DARK = "#0d0620"
TEXT = "#f8ecff"
MUTED = "#8a6fb8"
EMPTY = "#3a1d6e"

THEMES = {
    "focus": {"name": "FOCUS TIME", "a": "#b36bff", "b": "#ff5fc8"},
    "short": {"name": "SHORT BREAK", "a": "#ff6fb5", "b": "#ffb0e8"},
    "long": {"name": "LONG BREAK", "a": "#d89bff", "b": "#ff8ad8"},
}
MODES = ["focus", "short", "long"]
TAB_LABELS = {"focus": "FOCUS", "short": "BREAK", "long": "LONG"}
DEFAULT_MINS = {"focus": 25, "short": 5, "long": 15}
MAX_MINS = {"focus": 90, "short": 30, "long": 60}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def lighten(c, t):
    return mix(c, "#ffffff", t)


def darken(c, t):
    return mix(c, "#000000", t)


# --------------------------------------------------------------- pixel font
_F = {
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": ".###.|#...#|....#|..##.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.###.",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    ":": ".....|..#..|..#..|.....|..#..|..#..|.....",
    "-": ".....|.....|.....|#####|.....|.....|.....",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..",
    ".": ".....|.....|.....|.....|.....|.....|..#..",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}


def _runs(rows):
    runs = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] == "#":
                x0 = x
                while x < len(row) and row[x] == "#":
                    x += 1
                runs.append((x0, y, x - x0))
            else:
                x += 1
    return runs


GLYPH_RUNS = {}
for _ch, _s in _F.items():
    _rows = _s.split("|")
    assert len(_rows) == 7 and all(len(r) == 5 for r in _rows), _ch
    GLYPH_RUNS[_ch] = _runs(_rows)

# ------------------------------------------------------------------ sprites
MASCOT_PAL = {
    "o": "#2a0f45", "b": "#ff6fb5", "l": "#ffb3da", "d": "#d44a95",
    "g": "#c9a0ff", "e": "#2a0f45", "c": "#ff3d8a", "m": "#2a0f45",
}
_BASE = [
    ".....g..g.....",
    "....gggggg....",
    "..oobbbbbboo..",
    ".obbllbbbbbbo.",
    "obblbbbbbbbbbo",
    "obbbbbbbbbbbbo",
    "@EYES6",
    "@EYES7",
    "occbbbbbbbbcco",
    "obbbbbmmbbbbbo",
    "odbbbbbbbbbbdo",
    ".oddbbbbbbddo.",
    "..ooddddddoo..",
    "....oooooo....",
]
_EYES = {
    "awake": ("obbeebbbbeebbo", "obbeebbbbeebbo"),
    "sleep": ("obbbbbbbbbbbbo", "obeeebbbbeeebo"),
    "happy": ("obbbebbbbebbbo", "obbebebbebebbo"),
}
HEART = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]


def mascot_rows(face):
    r6, r7 = _EYES[face]
    out = []
    for row in _BASE:
        if row == "@EYES6":
            out.append(r6)
        elif row == "@EYES7":
            out.append(r7)
        else:
            out.append(row)
    return out


# ------------------------------------------------------------------ paths
def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_ID / "config.json"


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / APP_ID


# -------------------------------------------------------------------- sound
def make_chime(path):
    rate = 22050
    notes = [(523.25, 0.11), (659.25, 0.11), (783.99, 0.11), (1046.5, 0.30)]
    frames = bytearray()
    for freq, dur in notes:
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            sq = 1 if (t * freq) % 1 < 0.5 else -1
            env = min(1.0, i / 180) * (max(0.0, 1 - i / n) ** 0.7)
            frames += struct.pack("<h", int(sq * env * 7000))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def play_chime(fallback_bell):
    try:
        wav = cache_dir() / "chime.wav"
        if not wav.exists():
            wav.parent.mkdir(parents=True, exist_ok=True)
            make_chime(wav)
        for cmd in (["pw-play"], ["paplay"], ["aplay", "-q"]):
            if shutil.which(cmd[0]):
                subprocess.Popen(cmd + [str(wav)], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return
    except Exception:
        pass
    fallback_bell()


def notify(title, body):
    if shutil.which("notify-send"):
        try:
            subprocess.Popen(
                ["notify-send", "-a", APP_NAME, "-i", APP_ID, title, body],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


# --------------------------------------------------------------- icon export
def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def export_icon(path, size=256):
    grid = 16
    k = size // grid
    sprite = mascot_rows("awake")
    cells = [[None] * grid for _ in range(grid)]
    for y, row in enumerate(sprite):
        for x, ch in enumerate(row):
            if ch != ".":
                cells[y + 1][x + 1] = _rgb(MASCOT_PAL[ch]) + (255,)
    # soft shadow under the tomato
    for x in range(4, 12):
        cells[15][x] = _rgb("#2a0f45") + (150,)
    rows = []
    for y in range(grid):
        line = b"".join(bytes(c or (0, 0, 0, 0)) * k for c in cells[y])
        rows.extend([line] * k)
    write_png(path, k * grid, k * grid, rows)


# ---------------------------------------------------------------------- app
class PixelPomodoro:
    def __init__(self, tk, root):
        self.tk = tk
        self.root = root
        self.cv = tk.Canvas(root, width=W * S, height=H * S, bg=BG,
                            highlightthickness=0, bd=0)
        self.cv.pack()

        self.mins = dict(DEFAULT_MINS)
        self.today = 0
        self.load_config()

        self.mode = "focus"
        self.running = False
        self.remaining = self.total()
        self.end = 0.0
        self.cycle = 0
        self.cel_until = 0.0
        self.cel_start = 0.0
        self.cel_msg = ""
        self.confetti = []
        self.hover = None
        self.pressed = None
        self.hits = []
        self.sig = None

        rnd = random.Random(7)
        self.stars = [(rnd.randrange(0, W), rnd.randrange(0, H), rnd.random() * 6.3,
                       rnd.choice(["#ff8ad8", "#c9a0ff", "#ffffff", "#b36bff"]))
                      for _ in range(30)]

        self.draw_background()
        self.setup_window()
        self.bind_events()
        self.tick()

    # ---- window ---------------------------------------------------------
    def setup_window(self):
        r = self.root
        r.title(APP_NAME)
        r.configure(bg=BG)
        r.resizable(False, False)
        try:
            img = self.tk.PhotoImage(width=14, height=14)
            for y, row in enumerate(mascot_rows("awake")):
                for x, ch in enumerate(row):
                    if ch != ".":
                        img.put(MASCOT_PAL[ch], (x, y))
            self.icon = img.zoom(8)
            r.iconphoto(True, self.icon)
        except Exception:
            pass
        r.protocol("WM_DELETE_WINDOW", self.quit)

    def bind_events(self):
        r, cv = self.root, self.cv
        r.bind("<space>", lambda e: self.toggle())
        r.bind("<Key-r>", lambda e: self.reset())
        r.bind("<Key-s>", lambda e: self.skip())
        r.bind("<Key-q>", lambda e: self.quit())
        for i, m in enumerate(MODES):
            r.bind(str(i + 1), lambda e, m=m: self.set_mode(m))
        r.bind("<Up>", lambda e: self.adjust(1))
        r.bind("<Down>", lambda e: self.adjust(-1))
        r.bind("<plus>", lambda e: self.adjust(1))
        r.bind("<minus>", lambda e: self.adjust(-1))
        cv.bind("<Motion>", self.on_motion)
        cv.bind("<Leave>", self.on_leave)
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<ButtonRelease-1>", self.on_release)

    # ---- config ---------------------------------------------------------
    def load_config(self):
        try:
            data = json.loads(config_path().read_text())
            for m in MODES:
                v = int(data.get("mins", {}).get(m, self.mins[m]))
                self.mins[m] = max(1, min(MAX_MINS[m], v))
            t = data.get("today", {})
            if t.get("date") == date.today().isoformat():
                self.today = int(t.get("count", 0))
        except Exception:
            pass

    def save_config(self):
        try:
            p = config_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({
                "mins": self.mins,
                "today": {"date": date.today().isoformat(), "count": self.today},
            }))
        except Exception:
            pass

    def quit(self):
        self.save_config()
        self.root.destroy()

    # ---- timer logic ----------------------------------------------------
    def total(self):
        return self.mins[self.mode] * 60

    def set_mode(self, mode):
        self.mode = mode
        self.running = False
        self.remaining = self.total()

    def toggle(self):
        now = time.monotonic()
        if self.running:
            self.remaining = max(0.0, self.end - now)
            self.running = False
        else:
            if self.remaining <= 0:
                self.remaining = self.total()
            self.end = now + self.remaining
            self.running = True
            self.cel_until = 0.0

    def reset(self):
        self.running = False
        self.remaining = self.total()

    def next_after(self, finished, counted):
        if finished == "focus":
            if counted:
                self.cycle += 1
            return "long" if self.cycle >= 4 else "short"
        if finished == "long":
            self.cycle = 0
        return "focus"

    def skip(self):
        self.set_mode(self.next_after(self.mode, counted=False))

    def adjust(self, delta):
        if self.running:
            return
        self.mins[self.mode] = max(1, min(MAX_MINS[self.mode], self.mins[self.mode] + delta))
        self.remaining = self.total()
        self.save_config()

    def complete(self):
        finished = self.mode
        if finished == "focus":
            self.today += 1
        nxt = self.next_after(finished, counted=True)
        self.save_config()
        now = time.monotonic()
        self.cel_start, self.cel_until = now, now + 3.5
        if finished == "focus":
            self.cel_msg = "GREAT JOB!"
            notify("Focus done!", "Time for a %s break." % ("long" if nxt == "long" else "short"))
        else:
            self.cel_msg = "READY?"
            notify("Break over", "Ready for the next focus session?")
        play_chime(self.root.bell)
        self.spawn_confetti()
        self.set_mode(nxt)

    def spawn_confetti(self):
        cols = ["#ff5fc8", "#b36bff", "#ffb0e8", "#ffffff", "#d89bff"]
        for _ in range(46):
            self.confetti.append([60 + random.uniform(-6, 6), 112,
                                  random.uniform(-2.2, 2.2), random.uniform(-4.5, -1.2),
                                  random.choice(cols), random.choice([1, 1, 2]), 0])

    # ---- tick -----------------------------------------------------------
    def tick(self):
        now = time.monotonic()
        if self.running:
            self.remaining = max(0.0, self.end - now)
            if self.remaining <= 0:
                self.complete()
        secs = int(math.ceil(self.remaining - 1e-9))
        sig = (self.mode, self.running, secs, self.hover, self.pressed, self.today,
               self.cycle, int(now * 2) % 2 if self.running else 0,
               now < self.cel_until, self.mins[self.mode])
        if sig != self.sig:
            if self.sig is None or self.sig[2] != secs or self.sig[1] != self.running:
                self.root.title("%02d:%02d - %s" % (secs // 60, secs % 60, APP_NAME)
                                if self.running else APP_NAME)
            self.sig = sig
            self.render_static(now, secs)
        self.render_dynamic(now)
        self.root.after(50, self.tick)

    # ---- low level drawing ---------------------------------------------
    def rect(self, x, y, w, h, color, tag):
        self.cv.create_rectangle(x * S, y * S, (x + w) * S, (y + h) * S,
                                 fill=color, outline="", tags=tag)

    def text(self, x, y, s, px=1, color=TEXT, tag="ui", cx=None, shadow=None):
        s = s.upper()
        w = len(s) * 6 * px - px
        if cx is not None:
            x = cx - w // 2
        if shadow:
            self.text(x + max(1, px // 2), y + max(1, px // 2), s, px, shadow, tag)
        for i, ch in enumerate(s):
            gx = x + i * 6 * px
            for rx, ry, rl in GLYPH_RUNS.get(ch, ()):
                self.rect(gx + rx * px, y + ry * px, rl * px, px, color, tag)
        return w

    def sprite(self, rows, pal, x, y, px, tag):
        for ry, row in enumerate(rows):
            cx = 0
            while cx < len(row):
                ch = row[cx]
                if ch == ".":
                    cx += 1
                    continue
                start = cx
                while cx < len(row) and row[cx] == ch:
                    cx += 1
                self.rect(x + start * px, y + ry * px, (cx - start) * px, px, pal[ch], tag)

    def notched(self, x, y, w, h, color, tag):
        self.rect(x + 1, y, w - 2, h, color, tag)
        self.rect(x, y + 1, w, h - 2, color, tag)

    def panel(self, x, y, w, h, border, fill, tag="ui"):
        self.notched(x + 2, y + 2, w, h, DARK, tag)
        self.notched(x, y, w, h, border, tag)
        self.notched(x + 1, y + 1, w - 2, h - 2, fill, tag)
        self.rect(x + 3, y + 2, w - 6, 1, lighten(fill, 0.12), tag)

    def button(self, bid, x, y, w, h, label, fill, fg=TEXT, enabled=True):
        hover = enabled and self.hover == bid
        down = hover and self.pressed == bid
        face = lighten(fill, 0.18) if hover else fill
        off = 1 if down else 0
        self.notched(x, y + 2, w, h - 2, darken(fill, 0.55), "ui")
        self.notched(x, y + off, w, h - 2, face, "ui")
        self.rect(x + 1, y + off, w - 2, 1, lighten(face, 0.3), "ui")
        self.text(0, y + off + 2, label, 1, fg, cx=x + w // 2)
        if enabled:
            self.hits.append((bid, x, y, w, h))

    # ---- background -----------------------------------------------------
    def draw_background(self):
        bands = [BG, "#190c33", "#1d0e3b", "#220f44"]
        bh = H // 8
        for i in range(8):
            c = bands[min(i // 2, 3)]
            self.rect(0, i * bh, W, bh, c, "bg")
            if i % 2 == 1 and i // 2 < 3:
                nxt = bands[i // 2 + 1]
                for x in range(0, W, 2):
                    self.rect(x + (i // 2) % 2, i * bh + bh - 1, 1, 1, nxt, "bg")
        # little pixel horizon dots at the bottom
        for x in range(0, W, 4):
            self.rect(x, H - 2, 2, 1, "#2e1760", "bg")

    # ---- static layer (text, panels, buttons) ---------------------------
    def render_static(self, now, secs):
        cv = self.cv
        cv.delete("ui")
        self.hits = []
        th = THEMES[self.mode]
        a, b = th["a"], th["b"]
        blink = self.running and int(now * 2) % 2 == 0

        # title
        word = "POMODORO"
        x = (W - (len(word) * 12 - 2)) // 2
        for i, ch in enumerate(word):
            col = a if i % 2 == 0 else b
            self.text(x + i * 12, 3, ch, 2, col, shadow=DARK)

        # tabs
        for i, m in enumerate(MODES):
            active = m == self.mode
            t = THEMES[m]
            self.button("tab:" + m, 5 + i * 38, 19, 34, 12, TAB_LABELS[m],
                        t["a"] if active else PANEL_IN, TEXT if active else MUTED)

        # main panel
        self.panel(6, 35, 108, 64, a, PANEL)
        self.text(0, 40, th["name"], 1, b, cx=60)
        can = not self.running
        self.button("minus", 9, 38, 9, 9, "-", PANEL_IN if can else PANEL,
                    TEXT if can else EMPTY, enabled=can)
        self.button("plus", 102, 38, 9, 9, "+", PANEL_IN if can else PANEL,
                    TEXT if can else EMPTY, enabled=can)

        mm, ss = secs // 60, secs % 60
        digits = "%02d:%02d" % (mm, ss)
        if self.running and not blink:
            digits = digits.replace(":", " ")
        dw = len(digits) * 18 - 3
        self.text((W - dw) // 2, 51, digits, 3, TEXT, shadow=darken(a, 0.45))

        # progress bar
        total = max(1, self.total())
        frac = 1 - (self.remaining / total)
        n = 20
        filled = int(frac * n + 1e-9)
        for i in range(n):
            x0 = 10 + i * 5
            if i < filled:
                col = mix(a, b, i / (n - 1))
            elif i == filled and self.running and blink:
                col = lighten(mix(a, b, i / (n - 1)), 0.45)
            else:
                col = EMPTY
            self.rect(x0, 81, 4, 5, col, "ui")
            if i < filled:
                self.rect(x0, 81, 4, 1, lighten(col, 0.35), "ui")

        self.text(0, 90, "TODAY: %d" % self.today, 1, MUTED, cx=60)

        # status line
        self.text(0, 134, self.status_text(now), 1, b, cx=60, shadow=DARK)

        # hearts: one per focus session in the cycle
        hx = (W - (4 * 7 + 3 * 5)) // 2
        for i in range(4):
            if i < self.cycle:
                col = b
            elif i == self.cycle and self.mode == "focus" and self.running:
                col = lighten(a, 0.4) if blink else EMPTY
            else:
                col = EMPTY
            pal = {"#": col}
            self.sprite(HEART, pal, hx + i * 12, 144, 1, "ui")
            if i < self.cycle:
                self.rect(hx + i * 12 + 1, 144, 1, 1, lighten(col, 0.6), "ui")

        # main buttons
        self.button("toggle", 5, 153, 34, 12, "PAUSE" if self.running else "START",
                    b if not self.running else a, "#2a0f45" if not self.running else TEXT)
        self.button("reset", 43, 153, 34, 12, "RESET", PANEL_IN, TEXT)
        self.button("skip", 81, 153, 34, 12, "SKIP", PANEL_IN, TEXT)

        self.order()

    def status_text(self, now):
        if now < self.cel_until:
            return self.cel_msg
        if self.running:
            return "FOCUS MODE!" if self.mode == "focus" else "ZZZ... REST"
        if self.remaining < self.total():
            return "PAUSED"
        return "READY?" if self.mode == "focus" else "TAKE A BREAK"

    def order(self):
        cv = self.cv
        try:
            cv.tag_lower("stars", "ui")
            cv.tag_lower("bg")
            cv.tag_raise("fx")
        except Exception:
            pass

    # ---- dynamic layer (stars, mascot, confetti) ------------------------
    def render_dynamic(self, now):
        cv = self.cv
        cv.delete("dyn")
        cv.delete("stars")
        cv.delete("fx")

        for (sx, sy, ph, col) in self.stars:
            v = math.sin(now * 2.2 + ph)
            if v > 0.55:
                self.rect(sx, sy, 1, 1, col, "stars")
                self.rect(sx - 1, sy, 3, 1, mix(col, BG, 0.45), "stars")
                self.rect(sx, sy - 1, 1, 3, mix(col, BG, 0.45), "stars")
            elif v > -0.35:
                self.rect(sx, sy, 1, 1, mix(col, BG, 0.4), "stars")

        celebrating = now < self.cel_until
        sleeping = self.running and self.mode != "focus"
        paused = (not self.running) and self.remaining < self.total()
        speed = 6.0 if self.running else 2.4
        bob = 0 if paused else int(round(math.sin(now * speed)))
        jump = 0
        if celebrating:
            jump = -int(abs(math.sin((now - self.cel_start) * 7)) * 6)
        blink = (now * 1000) % 3600 < 150
        if celebrating:
            face = "happy"
        elif sleeping or blink:
            face = "sleep"
        else:
            face = "awake"

        my = 102 + bob + jump
        # shadow shrinks while jumping
        sw = 18 + jump
        self.rect(60 - sw // 2, 131, sw, 1, DARK, "dyn")
        self.rect(60 - (sw - 4) // 2, 132, sw - 4, 1, DARK, "dyn")
        self.sprite(mascot_rows(face), MASCOT_PAL, 60 - 14, my, 2, "dyn")

        if sleeping:
            for k in range(2):
                ph = (now * 0.9 + k * 0.5) % 1.0
                self.text(80 + k * 7, 108 - int(ph * 9), "Z", 1,
                          mix("#c9a0ff", BG, ph * 0.7), tag="dyn")

        # confetti
        alive = []
        for p in self.confetti:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.22
            p[6] += 1
            if p[6] < 48 and p[1] < H:
                alive.append(p)
                self.rect(int(p[0]), int(p[1]), p[5], p[5], p[4], "fx")
        self.confetti = alive
        self.order()

    # ---- mouse ----------------------------------------------------------
    def hit_at(self, e):
        lx, ly = e.x / S, e.y / S
        for bid, x, y, w, h in self.hits:
            if x <= lx < x + w and y <= ly < y + h:
                return bid
        return None

    def on_motion(self, e):
        h = self.hit_at(e)
        if h != self.hover:
            self.hover = h
            self.cv.config(cursor="hand2" if h else "arrow")

    def on_leave(self, e):
        self.hover = None
        self.pressed = None
        self.cv.config(cursor="arrow")

    def on_press(self, e):
        self.pressed = self.hit_at(e)

    def on_release(self, e):
        h = self.hit_at(e)
        pressed, self.pressed = self.pressed, None
        if h and h == pressed:
            self.activate(h)

    def activate(self, bid):
        if bid.startswith("tab:"):
            self.set_mode(bid[4:])
        elif bid == "toggle":
            self.toggle()
        elif bid == "reset":
            self.reset()
        elif bid == "skip":
            self.skip()
        elif bid == "plus":
            self.adjust(1)
        elif bid == "minus":
            self.adjust(-1)


def main():
    global S
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--scale", type=int, help="screen pixels per logical pixel (default: auto)")
    ap.add_argument("--export-icon", metavar="PNG", help="write the app icon and exit")
    args = ap.parse_args()

    if args.export_icon:
        export_icon(args.export_icon)
        return

    try:
        import tkinter as tk
    except ImportError:
        sys.exit("tkinter not found. On Arch: sudo pacman -S tk")

    root = tk.Tk(className="PixelPomodoro")
    if args.scale:
        S = max(1, args.scale)
    else:
        S = 4 if root.winfo_screenheight() >= 900 else 3
    PixelPomodoro(tk, root)
    root.mainloop()


if __name__ == "__main__":
    main()
