#!/usr/bin/env python3
"""Pixel Pomodoro: pixel-art pomodoro timer in pure tkinter.

Two modes:
- DESKTOP: normal window with title bar, icon, standard behavior
- OVERLAY: borderless, always-on-top widget, draggable, visible over fullscreen
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
W, H = 120, 160
W_MINI, H_MINI = 100, 50    
S = 4

# ------------------------------------------------------------------ languages
LANGS = {
    "en": {
        "focus": "FOCUS", "short": "BREAK", "long": "LONG",
        "focus_time": "FOCUS TIME", "short_break": "SHORT BREAK", "long_break": "LONG BREAK",
        "start": "START", "pause": "PAUSE", "reset": "RESET", "skip": "SKIP",
        "great_job": "GREAT JOB!", "ready": "READY?",
        "focus_done": "Focus done!", "time_for_break": "Time for a %s break.",
        "break_over": "Break over", "ready_next": "Ready for the next focus session?",
        "zzz": "ZZZ... REST", "paused": "PAUSED", "ready_break": "TAKE A BREAK",
        "settings": "SETTINGS", "language": "LANGUAGE", "theme": "THEME",
        "mode": "MODE", "desktop": "DESKTOP", "overlay": "OVERLAY",
        "back": "BACK", "mini": "MINI",
        "purple": "PURPLE", "green": "GREEN", "ocean": "OCEAN", "sunset": "SUNSET"
    },
    "ru": {
        "focus": "ФОКУС", "short": "КОРОТ", "long": "ДЛИНН",
        "focus_time": "РАБОТА", "short_break": "ПЕРЕРЫВ", "long_break": "ДЛИН ПЕР",
        "start": "СТАРТ", "pause": "ПАУЗА", "reset": "СБРОС", "skip": "ПРОПУСК",
        "great_job": "ОТЛИЧНО!", "ready": "ГОТОВ?",
        "focus_done": "Фокус завершен!", "time_for_break": "Время %s перерыва.",
        "break_over": "Перерыв окончен", "ready_next": "Готовы к следующему?",
        "zzz": "ZZZ ОТДЫХ", "paused": "ПАУЗА", "ready_break": "ПЕРЕРЫВ",
        "settings": "НАСТРОЙКИ", "language": "ЯЗЫК", "theme": "ТЕМА",
        "mode": "РЕЖИМ", "desktop": "ОКНО", "overlay": "ОВЕРЛЕЙ",
        "back": "НАЗАД", "mini": "МИНИ",
        "purple": "ФИОЛЕТ", "green": "ЗЕЛЕНЫЙ", "ocean": "ОКЕАН", "sunset": "ЗАКАТ"
    }
}

# ------------------------------------------------------------------ themes
GLOBAL_THEMES = {
    "purple": {
        "BG": "#150a2b", "PANEL": "#241049", "PANEL_IN": "#2e1760", "DARK": "#0d0620",
        "TEXT": "#f8ecff", "MUTED": "#8a6fb8", "EMPTY": "#3a1d6e",
        "modes": {
            "focus": {"name": "focus_time", "a": "#b36bff", "b": "#ff5fc8"},
            "short": {"name": "short_break", "a": "#ff6fb5", "b": "#ffb0e8"},
            "long": {"name": "long_break", "a": "#d89bff", "b": "#ff8ad8"},
        }
    },
    "green": {
        "BG": "#0a1a0f", "PANEL": "#103018", "PANEL_IN": "#184520", "DARK": "#051008",
        "TEXT": "#eafff0", "MUTED": "#6fb88a", "EMPTY": "#1d6e3a",
        "modes": {
            "focus": {"name": "focus_time", "a": "#6bff8b", "b": "#5fc8ff"},
            "short": {"name": "short_break", "a": "#8aff6f", "b": "#b0ffb8"},
            "long": {"name": "long_break", "a": "#9bff6f", "b": "#8ad8ff"},
        }
    },
    "ocean": {
        "BG": "#0a102b", "PANEL": "#102049", "PANEL_IN": "#173060", "DARK": "#060d20",
        "TEXT": "#ecf4ff", "MUTED": "#6f90b8", "EMPTY": "#1d3a6e",
        "modes": {
            "focus": {"name": "focus_time", "a": "#6f8bff", "b": "#5fc8ff"},
            "short": {"name": "short_break", "a": "#6fb5ff", "b": "#b0e8ff"},
            "long": {"name": "long_break", "a": "#9bb3ff", "b": "#8ad8ff"},
        }
    },
    "sunset": {
        "BG": "#2b0a0a", "PANEL": "#491010", "PANEL_IN": "#601717", "DARK": "#200606",
        "TEXT": "#ffecec", "MUTED": "#b86f6f", "EMPTY": "#6e1d1d",
        "modes": {
            "focus": {"name": "focus_time", "a": "#ff6f6f", "b": "#ffb05f"},
            "short": {"name": "short_break", "a": "#ff8a6f", "b": "#ffd0b0"},
            "long": {"name": "long_break", "a": "#ff9b9b", "b": "#ffd88a"},
        }
    }
}

# ------------------------------------------------------------------ helpers
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)

def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))

def lighten(c, t): return mix(c, "#ffffff", t)
def darken(c, t): return mix(c, "#000000", t)

# ------------------------------------------------------------------ pixel font
_F = {
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": ".###.|#...#|....#|..##.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.###.", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.", "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    
    # Выровненная кириллица
    "А": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "Б": "#####|#....|#....|####.|#...#|#...#|####.",
    "В": "####.|#...#|#...#|####.|#...#|#...#|####.", "Г": "#####|#....|#....|#....|#....|#....|#....",
    "Д": "..##.|.#..#|#...#|#...#|#...#|#...#|#####", "Е": "#####|#....|#....|####.|#....|#....|#####",
    "Ж": "#...#|#.#.#|##.##|.###.|##.##|#.#.#|#...#", "З": ".###.|....#|....#|.###.|....#|#...#|.###.",
    "И": "#...#|#...#|#..#.|#.#..|#....|#...#|#...#", "Й": ".#.#.|.#.#.|#...#|#..#.|#.#..|#....|#...#",
    "К": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "Л": "..##.|.#..#|#...#|#...#|#...#|#...#|#...#",
    "М": "#...#|##.##|#.#.#|#...#|#...#|#...#|#...#", "Н": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "О": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "П": "#####|#...#|#...#|#...#|#...#|#...#|#...#",
    "Р": "####.|#...#|#...#|####.|#....|#....|#....", "С": ".####|#....|#....|#....|#....|#....|.####",
    "Т": "#####|..#..|..#..|..#..|..#..|..#..|..#..", "У": "#...#|#...#|.###.|..#..|..#..|..#..|.##..",
    "Ф": "..#..|##.##|#####|.#.#.|#####|##.##|..#..", "Х": "#...#|#...#|#.#..|.#...|#.#..|#...#|#...#",
    "Ц": "#.#..|#.#..|#.#..|#.#..|#.#..|#.###|...##", "Ч": "#...#|#...#|#...#|.####|....#|....#|....#",
    "Ш": "#...#|#...#|#...#|#...#|#.#.#|##.##|#...#", "Щ": "#.#.#|#.#.#|#.#.#|#.#.#|#####|...##|...##",
    "Ъ": "##...|.#...|.#...|.####|.#..#|.#..#|.####", "Ы": "#.#..|#.#..|#.#..|.####|.#..#|.#..#|.####",
    "Ь": "#....|#....|#....|####.|#...#|#...#|####.", "Э": ".###.|#...#|...#.|.##..|...#.|#...#|.###.",
    "Ю": "#.###|#.#.#|#.#.#|#.###|#.#.#|#.#.#|#.###", "Я": "..###|.#..#|.#.#.|.###.|.#...|.#...|#....",
    
    ":": ".....|..#..|..#..|.....|..#..|..#..|.....", "-": ".....|.....|.....|#####|.....|.....|.....",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....", "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..", ".": ".....|.....|.....|.....|.....|.....|..#..",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....", " ": ".....|.....|.....|.....|.....|.....|.....",
}

def _runs(rows):
    runs = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] == "#":
                x0 = x
                while x < len(row) and row[x] == "#": x += 1
                runs.append((x0, y, x - x0))
            else: x += 1
    return runs

GLYPH_RUNS = {}
for _ch, _s in _F.items():
    _rows = _s.split("|")
    assert len(_rows) == 7 and all(len(r) == 5 for r in _rows), _ch
    GLYPH_RUNS[_ch] = _runs(_rows)

# ------------------------------------------------------------------ sprites
MASCOT_PAL = {"o": "#2a0f45", "b": "#ff6fb5", "l": "#ffb3da", "d": "#d44a95", "g": "#c9a0ff", "e": "#2a0f45", "c": "#ff3d8a", "m": "#2a0f45"}
_BASE = [".....g..g.....", "....gggggg....", "..oobbbbbboo..", ".obbllbbbbbbo.", "obblbbbbbbbbbo", "obbbbbbbbbbbbo", "@EYES6", "@EYES7", "occbbbbbbbbcco", "obbbbbmmbbbbbo", "odbbbbbbbbbbdo", ".oddbbbbbbddo.", "..ooddddddoo..", "....oooooo...."]
_EYES = {"awake": ("obbeebbbbeebbo", "obbeebbbbeebbo"), "sleep": ("obbbbbbbbbbbbo", "obeeebbbbeeebo"), "happy": ("obbbebbbbebbbo", "obbebebbebebbo")}
HEART = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]

def mascot_rows(face):
    r6, r7 = _EYES[face]
    return [r6 if row == "@EYES6" else r7 if row == "@EYES7" else row for row in _BASE]

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
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(frames))

def play_chime(fallback_bell):
    try:
        wav = cache_dir() / "chime.wav"
        if not wav.exists():
            wav.parent.mkdir(parents=True, exist_ok=True)
            make_chime(wav)
        for cmd in (["pw-play"], ["paplay"], ["aplay", "-q"]):
            if shutil.which(cmd[0]):
                subprocess.Popen(cmd + [str(wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
    except Exception: pass
    fallback_bell()

def notify(title, body):
    if shutil.which("notify-send"):
        try: subprocess.Popen(["notify-send", "-a", APP_NAME, "-i", APP_ID, title, body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception: pass

# ---------------------------------------------------------------------- app
class PixelPomodoro:
    def __init__(self, tk, root):
        self.tk = tk
        self.root = root
        self.cv = tk.Canvas(root, width=W * S, height=H * S, bg="#150a2b", highlightthickness=0, bd=0)
        self.cv.pack()

        self.mins = {"focus": 25, "short": 5, "long": 15}
        self.lang = "ru"
        self.theme_name = "purple"
        self.app_mode = "desktop"  # "desktop" or "overlay"
        self.minimized = False
        self.view = "main"
        
        self.load_config()
        self.apply_theme()

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
        self.drag_start = None

        rnd = random.Random(7)
        self.stars = [(rnd.randrange(0, W), rnd.randrange(0, H), rnd.random() * 6.3, rnd.choice(["#ff8ad8", "#c9a0ff", "#ffffff", "#b36bff"])) for _ in range(30)]

        self.draw_background()
        self.setup_window()
        self.bind_events()
        self.tick()

    def t(self, key):
        return LANGS.get(self.lang, LANGS["en"]).get(key, key)

    def get_theme_mode_name(self, mode):
        return self.t(self.THEMES_MODES[mode]["name"])

    def apply_theme(self):
        gt = GLOBAL_THEMES[self.theme_name]
        self.BG, self.PANEL, self.PANEL_IN = gt["BG"], gt["PANEL"], gt["PANEL_IN"]
        self.DARK, self.TEXT, self.MUTED, self.EMPTY = gt["DARK"], gt["TEXT"], gt["MUTED"], gt["EMPTY"]
        self.THEMES_MODES = gt["modes"]
        self.cv.config(bg=self.BG)
        self.root.configure(bg=self.BG)
        self._apply_window_mode()

    def _apply_window_mode(self):
        """Apply Desktop or Overlay window properties."""
        r = self.root
        if self.app_mode == "overlay":
            r.overrideredirect(True)
            r.attributes('-topmost', True)
            try: r.attributes('-type', 'splash')
            except Exception: pass
            r.lift()
            r.attributes('-topmost', True)
        else:
            r.overrideredirect(False)
            r.attributes('-topmost', False)
            try: r.attributes('-type', 'normal')
            except Exception: pass

    def setup_window(self):
        r = self.root
        r.title(APP_NAME)
        r.configure(bg=self.BG)
        r.resizable(False, False)
        self._apply_window_mode()
        try:
            img = self.tk.PhotoImage(width=14, height=14)
            for y, row in enumerate(mascot_rows("awake")):
                for x, ch in enumerate(row):
                    if ch != ".": img.put(MASCOT_PAL[ch], (x, y))
            self.icon = img.zoom(8)
            r.iconphoto(True, self.icon)
        except Exception: pass
        r.protocol("WM_DELETE_WINDOW", self.quit)

    def bind_events(self):
        r, cv = self.root, self.cv
        r.bind("<space>", lambda e: self.toggle())
        r.bind("<Key-r>", lambda e: self.reset())
        r.bind("<Key-s>", lambda e: self.skip())
        r.bind("<Key-q>", lambda e: self.quit())
        r.bind("<Escape>", lambda e: self.quit() if self.view == "main" else self.set_view("main"))
        r.bind("<m>", lambda e: self.toggle_minimize())
        r.bind("<M>", lambda e: self.toggle_minimize())
        r.bind("<Shift-O>", lambda e: self.toggle_minimize())
        r.bind("<F12>", lambda e: self.toggle_minimize())
        for i, m in enumerate(["focus", "short", "long"]):
            r.bind(str(i + 1), lambda e, m=m: self.set_mode(m))
        r.bind("<Up>", lambda e: self.adjust(1))
        r.bind("<Down>", lambda e: self.adjust(-1))
        r.bind("<plus>", lambda e: self.adjust(1))
        r.bind("<minus>", lambda e: self.adjust(-1))
        cv.bind("<Motion>", self.on_motion)
        cv.bind("<Leave>", self.on_leave)
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<ButtonRelease-1>", self.on_release)
        cv.bind("<B1-Motion>", self.on_drag)

    def load_config(self):
        try:
            data = json.loads(config_path().read_text())
            for m in ["focus", "short", "long"]:
                v = int(data.get("mins", {}).get(m, self.mins[m]))
                self.mins[m] = max(1, min({"focus": 90, "short": 30, "long": 60}[m], v))
            self.lang = data.get("lang", "ru")
            self.theme_name = data.get("theme", "purple")
            self.app_mode = data.get("mode", "desktop")
        except Exception: pass

    def save_config(self):
        try:
            p = config_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({
                "mins": self.mins,
                "lang": self.lang, "theme": self.theme_name, "mode": self.app_mode
            }))
        except Exception: pass

    def quit(self):
        self.save_config()
        self.root.destroy()

    def total(self): return self.mins[self.mode] * 60

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
            if self.remaining <= 0: self.remaining = self.total()
            self.end = now + self.remaining
            self.running = True
            self.cel_until = 0.0

    def reset(self):
        self.running = False
        self.remaining = self.total()

    def next_after(self, finished, counted):
        if finished == "focus":
            if counted: self.cycle += 1
            return "long" if self.cycle >= 4 else "short"
        if finished == "long": self.cycle = 0
        return "focus"

    def skip(self):
        self.set_mode(self.next_after(self.mode, counted=False))

    def adjust(self, delta):
        if self.running: return
        self.mins[self.mode] = max(1, min({"focus": 90, "short": 30, "long": 60}[self.mode], self.mins[self.mode] + delta))
        self.remaining = self.total()
        self.save_config()

    def complete(self):
        finished = self.mode
        nxt = self.next_after(finished, counted=True)
        self.save_config()
        now = time.monotonic()
        self.cel_start, self.cel_until = now, now + 3.5
        if finished == "focus":
            self.cel_msg = self.t("great_job")
            notify(self.t("focus_done"), self.t("time_for_break") % self.t("short" if nxt == "short" else "long"))
        else:
            self.cel_msg = self.t("ready")
            notify(self.t("break_over"), self.t("ready_next"))
        play_chime(self.root.bell)
        self.spawn_confetti()
        self.set_mode(nxt)

    def spawn_confetti(self):
        cols = ["#ff5fc8", "#b36bff", "#ffb0e8", "#ffffff", "#d89bff"]
        for _ in range(46):
            self.confetti.append([60 + random.uniform(-6, 6), 112, random.uniform(-2.2, 2.2), random.uniform(-4.5, -1.2), random.choice(cols), random.choice([1, 1, 2]), 0])

    def tick(self):
        now = time.monotonic()
        if self.running:
            self.remaining = max(0.0, self.end - now)
            if self.remaining <= 0: self.complete()
        secs = int(math.ceil(self.remaining - 1e-9))
        sig = (self.mode, self.running, secs, self.hover, self.pressed, self.cycle, int(now * 2) % 2 if self.running else 0, now < self.cel_until, self.mins[self.mode], self.minimized, self.view)
        if sig != self.sig:
            if self.sig is None or self.sig[2] != secs or self.sig[1] != self.running:
                if not self.minimized:
                    self.root.title("%02d:%02d - %s" % (secs // 60, secs % 60, APP_NAME) if self.running else APP_NAME)
            self.sig = sig
            self.render_static(now, secs)
        self.render_dynamic(now)
        self.root.after(50, self.tick)

    def rect(self, x, y, w, h, color, tag):
        self.cv.create_rectangle(x * S, y * S, (x + w) * S, (y + h) * S, fill=color, outline="", tags=tag)

    def text(self, x, y, s, px=1, color=None, tag="ui", cx=None, shadow=None):
        if color is None: color = self.TEXT
        s = s.upper()
        w = len(s) * 6 * px - px
        if cx is not None: x = cx - w // 2
        if shadow: self.text(x + max(1, px // 2), y + max(1, px // 2), s, px, shadow, tag)
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
                if ch == ".": cx += 1; continue
                start = cx
                while cx < len(row) and row[cx] == ch: cx += 1
                self.rect(x + start * px, y + ry * px, (cx - start) * px, px, pal[ch], tag)

    def notched(self, x, y, w, h, color, tag):
        self.rect(x + 1, y, w - 2, h, color, tag)
        self.rect(x, y + 1, w, h - 2, color, tag)

    def panel(self, x, y, w, h, border, fill, tag="ui"):
        self.notched(x + 2, y + 2, w, h, self.DARK, tag)
        self.notched(x, y, w, h, border, tag)
        self.notched(x + 1, y + 1, w - 2, h - 2, fill, tag)
        self.rect(x + 3, y + 2, w - 6, 1, lighten(fill, 0.12), tag)

    def button(self, bid, x, y, w, h, label, fill, fg=None, enabled=True):
        if fg is None: fg = self.TEXT
        hover = enabled and self.hover == bid
        down = hover and self.pressed == bid
        face = lighten(fill, 0.18) if hover else fill
        off = 1 if down else 0
        self.notched(x, y + 2, w, h - 2, darken(fill, 0.55), "ui")
        self.notched(x, y + off, w, h - 2, face, "ui")
        self.rect(x + 1, y + off, w - 2, 1, lighten(face, 0.3), "ui")
        self.text(0, y + off + 2, label, 1, fg, cx=x + w // 2)
        if enabled: self.hits.append((bid, x, y, w, h))

    def draw_background(self):
        bands = [self.BG, lighten(self.BG, 0.05), lighten(self.BG, 0.1), lighten(self.BG, 0.15)]
        bh = H // 8
        for i in range(8):
            c = bands[min(i // 2, 3)]
            self.rect(0, i * bh, W, bh, c, "bg")
            if i % 2 == 1 and i // 2 < 3:
                nxt = bands[i // 2 + 1]
                for x in range(0, W, 2): self.rect(x + (i // 2) % 2, i * bh + bh - 1, 1, 1, nxt, "bg")
        for x in range(0, W, 4): self.rect(x, H - 2, 2, 1, self.PANEL_IN, "bg")

    def render_static(self, now, secs):
        self.cv.delete("ui")
        self.hits = []
        if self.minimized:
            self.render_mini(secs)
        elif self.view == "settings":
            self.render_settings()
        else:
            self.render_main(now, secs)
        self.order()

    def render_mini(self, secs):
        mm, ss = secs // 60, secs % 60
        digits = "%02d:%02d" % (mm, ss)
        
        # Рамка
        self.panel(0, 0, W_MINI, H_MINI, self.THEMES_MODES[self.mode]["a"], self.PANEL)
        
  
        text_height = 21
        y_pos = (H_MINI - text_height) // 2  
        
        self.text(0, y_pos, digits, 3, self.TEXT, cx=W_MINI//2, shadow=self.DARK)
        
        col = self.THEMES_MODES[self.mode]["a"] if self.running else self.MUTED
        indicator_width = 30
        self.rect((W_MINI - indicator_width) // 2, H_MINI - 8, indicator_width, 3, col, "ui")

    def render_settings(self):
        self.panel(6, 6, 108, 152, self.THEMES_MODES[self.mode]["a"], self.PANEL)
        self.text(0, 10, self.t("settings"), 2, self.TEXT, cx=60, shadow=self.DARK)
        
        # Language section
        self.text(0, 28, self.t("language"), 1, self.MUTED, cx=60)
        self.button("lang:en", 30, 38, 24, 12, "EN", self.PANEL_IN if self.lang != "en" else self.THEMES_MODES["focus"]["a"], self.TEXT if self.lang == "en" else self.MUTED)
        self.button("lang:ru", 66, 38, 24, 12, "RU", self.PANEL_IN if self.lang != "ru" else self.THEMES_MODES["focus"]["a"], self.TEXT if self.lang == "ru" else self.MUTED)

        # Theme section (vertical column)
        self.text(0, 58, self.t("theme"), 1, self.MUTED, cx=60)
        themes = [("purple", self.t("purple")), ("green", self.t("green")), ("ocean", self.t("ocean")), ("sunset", self.t("sunset"))]
        for i, (tid, tname) in enumerate(themes):
            y_pos = 68 + i * 14
            self.button("theme:" + tid, 20, y_pos, 80, 12, tname, self.PANEL_IN if self.theme_name != tid else GLOBAL_THEMES[tid]["modes"]["focus"]["a"], self.TEXT if self.theme_name == tid else self.MUTED)

        # Back button
        self.button("back", 42, 150, 36, 12, self.t("back"), self.PANEL_IN, self.TEXT)

    def render_main(self, now, secs):
        th = self.THEMES_MODES[self.mode]
        a, b = th["a"], th["b"]
        blink = self.running and int(now * 2) % 2 == 0

        word = "POMODORO"
        x = (W - (len(word) * 12 - 2)) // 2
        for i, ch in enumerate(word):
            col = a if i % 2 == 0 else b
            self.text(x + i * 12, 4, ch, 2, col, shadow=self.DARK)

        for i, m in enumerate(["focus", "short", "long"]):
            active = m == self.mode
            t = self.THEMES_MODES[m]
            self.button("tab:" + m, 5 + i * 38, 18, 34, 12, self.t(m), t["a"] if active else self.PANEL_IN, self.TEXT if active else self.MUTED)

        self.panel(6, 34, 108, 66, a, self.PANEL)
        self.text(0, 39, self.get_theme_mode_name(self.mode), 1, b, cx=60)
        can = not self.running
        self.button("minus", 9, 38, 9, 9, "-", self.PANEL_IN if can else self.PANEL, self.TEXT if can else self.EMPTY, enabled=can)
        self.button("plus", 102, 38, 9, 9, "+", self.PANEL_IN if can else self.PANEL, self.TEXT if can else self.EMPTY, enabled=can)

        mm, ss = secs // 60, secs % 60
        digits = "%02d:%02d" % (mm, ss)
        if self.running and not blink: digits = digits.replace(":", " ")
        dw = len(digits) * 18 - 3
        self.text((W - dw) // 2, 50, digits, 3, self.TEXT, shadow=darken(a, 0.45))

        total = max(1, self.total())
        frac = 1 - (self.remaining / total)
        n = 20
        filled = int(frac * n + 1e-9)
        for i in range(n):
            x0 = 10 + i * 5
            if i < filled: col = mix(a, b, i / (n - 1))
            elif i == filled and self.running and blink: col = lighten(mix(a, b, i / (n - 1)), 0.45)
            else: col = self.EMPTY
            self.rect(x0, 84, 4, 5, col, "ui")
            if i < filled: self.rect(x0, 84, 4, 1, lighten(col, 0.35), "ui")

        self.text(0, 96, self.status_text(now), 1, b, cx=60, shadow=self.DARK)

        hx = (W - (4 * 7 + 3 * 5)) // 2
        for i in range(4):
            if i < self.cycle: col = b
            elif i == self.cycle and self.mode == "focus" and self.running: col = lighten(a, 0.4) if blink else self.EMPTY
            else: col = self.EMPTY
            pal = {"#": col}
            self.sprite(HEART, pal, hx + i * 12, 108, 1, "ui")
            if i < self.cycle: self.rect(hx + i * 12 + 1, 108, 1, 1, lighten(col, 0.6), "ui")

        # 2x2 button grid
        self.button("toggle", 8, 122, 46, 16, self.t("pause") if self.running else self.t("start"), b if not self.running else a, "#2a0f45" if not self.running else self.TEXT)
        self.button("reset", 66, 122, 46, 16, self.t("reset"), self.PANEL_IN, self.TEXT)
        self.button("mini", 8, 142, 46, 16, self.t("mini"), self.PANEL_IN, self.TEXT)
        self.button("settings", 66, 142, 46, 16, self.t("settings")[:4], self.PANEL_IN, self.TEXT)

    def status_text(self, now):
        if now < self.cel_until: return self.cel_msg
        if self.running: return self.t("focus") if self.mode == "focus" else self.t("zzz")
        if self.remaining < self.total(): return self.t("paused")
        return self.t("ready") if self.mode == "focus" else self.t("ready_break")

    def order(self):
        try:
            self.cv.tag_lower("stars", "ui")
            self.cv.tag_lower("bg")
            self.cv.tag_raise("fx")
        except Exception: pass

    def render_dynamic(self, now):
        self.cv.delete("dyn")
        self.cv.delete("stars")
        self.cv.delete("fx")
        if self.minimized: return

        for (sx, sy, ph, col) in self.stars:
            v = math.sin(now * 2.2 + ph)
            if v > 0.55:
                self.rect(sx, sy, 1, 1, col, "stars")
                self.rect(sx - 1, sy, 3, 1, mix(col, self.BG, 0.45), "stars")
                self.rect(sx, sy - 1, 1, 3, mix(col, self.BG, 0.45), "stars")
            elif v > -0.35:
                self.rect(sx, sy, 1, 1, mix(col, self.BG, 0.4), "stars")

        celebrating = now < self.cel_until
        sleeping = self.running and self.mode != "focus"
        paused = (not self.running) and self.remaining < self.total()
        speed = 6.0 if self.running else 2.4
        bob = 0 if paused else int(round(math.sin(now * speed)))
        jump = 0
        if celebrating: jump = -int(abs(math.sin((now - self.cel_start) * 7)) * 6)
        blink = (now * 1000) % 3600 < 150
        face = "happy" if celebrating else ("sleep" if sleeping or blink else "awake")

        # Скрываем маскота и анимацию сна в меню настроек, чтобы он не перекрывал кнопки
        if self.view != "settings":
            my = 102 + bob + jump
            sw = 18 + jump
            self.rect(60 - sw // 2, 131, sw, 1, self.DARK, "dyn")
            self.rect(60 - (sw - 4) // 2, 132, sw - 4, 1, self.DARK, "dyn")
            self.sprite(mascot_rows(face), MASCOT_PAL, 60 - 14, my, 2, "dyn")

            if sleeping:
                for k in range(2):
                    ph = (now * 0.9 + k * 0.5) % 1.0
                    self.text(80 + k * 7, 108 - int(ph * 9), "Z", 1, mix("#c9a0ff", self.BG, ph * 0.7), tag="dyn")

        alive = []
        for p in self.confetti:
            p[0] += p[2]; p[1] += p[3]; p[3] += 0.22; p[6] += 1
            if p[6] < 48 and p[1] < H:
                alive.append(p)
                self.rect(int(p[0]), int(p[1]), p[5], p[5], p[4], "fx")
        self.confetti = alive
        self.order()

    def hit_at(self, e):
        lx, ly = e.x / S, e.y / S
        for bid, x, y, w, h in self.hits:
            if x <= lx < x + w and y <= ly < y + h: return bid
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
        if self.minimized:
            self.toggle_minimize()
            return
        # In overlay mode: drag by top 20 logical pixels
        if self.app_mode == "overlay" and e.y < 20 * S and self.view == "main":
            self.drag_start = (e.x_root, e.y_root)
        else:
            self.pressed = self.hit_at(e)

    def on_drag(self, e):
        if self.drag_start:
            dx = e.x_root - self.drag_start[0]
            dy = e.y_root - self.drag_start[1]
            self.root.geometry(f"+{self.root.winfo_x() + dx}+{self.root.winfo_y() + dy}")
            self.drag_start = (e.x_root, e.y_root)

    def on_release(self, e):
        if self.drag_start:
            self.drag_start = None
            return
        h = self.hit_at(e)
        pressed, self.pressed = self.pressed, None
        if h and h == pressed: self.activate(h)

    def activate(self, bid):
        if bid.startswith("tab:"): self.set_mode(bid[4:])
        elif bid == "toggle": self.toggle()
        elif bid == "reset": self.reset()
        elif bid == "mini": self.toggle_minimize()
        elif bid == "settings": self.set_view("settings")
        elif bid == "back": self.set_view("main")
        elif bid.startswith("lang:"):
            self.lang = bid[5:]
            self.apply_theme()
            self.save_config()
        elif bid.startswith("theme:"):
            self.theme_name = bid[6:]
            self.apply_theme()
            self.save_config()
        elif bid.startswith("mode:"):
            self.app_mode = bid[5:]
            self._apply_window_mode()
            self.save_config()

    def set_view(self, view):
        self.view = view
        self.hover = None
        self.pressed = None

    def toggle_minimize(self):
        self.minimized = not self.minimized
        if self.minimized:
            self.root.geometry(f"{W_MINI*S}x{H_MINI*S}")
            self.cv.config(width=W_MINI*S, height=H_MINI*S)
        else:
            self.root.geometry(f"{W*S}x{H*S}")
            self.cv.config(width=W*S, height=H*S)
        self._apply_window_mode()

def main():
    global S
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--scale", type=int, help="screen pixels per logical pixel (default: auto)")
    ap.add_argument("--export-icon", metavar="PNG", help="write the app icon and exit")
    args = ap.parse_args()

    if args.export_icon:
        return

    try:
        import tkinter as tk
    except ImportError:
        sys.exit("tkinter not found. On Arch: sudo pacman -S tk")

    root = tk.Tk(className="PixelPomodoro")
    if args.scale: S = max(1, args.scale)
    else: S = 4 if root.winfo_screenheight() >= 900 else 3
    
    app = PixelPomodoro(tk, root)
    root.mainloop()

if __name__ == "__main__":
    main()
