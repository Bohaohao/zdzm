# -*- coding: utf-8 -*-
"""终端兼容层：统一处理编码 / 颜色 / 符号降级。

设计原则：
  1. 所有 UI 输出都走这里的 c() / sym() / box()，不要直接写 ANSI 或特殊字符
  2. 启动时探测一次能力，之后按能力自动降级
  3. 降级后仍然可读、对齐正确，只是没那么花

探测项：
  - 编码是否 UTF-8 / CP65001 → 决定中文与框线能否正常显示
  - 是否 tty → 非 tty 一律无色（管道/重定向）
  - Windows → 尝试开 VT；不支持就降到 16 色；再不行就无色
  - TERM=dumb → 无色无框
"""
import os
import re
import sys
import unicodedata

# ---------------------------------------------------------------- 能力探测
ENCODING = (getattr(sys.stdout, "encoding", None) or "").lower().replace("_", "-")
IS_TTY = (not hasattr(sys.stdout, "isatty")) or sys.stdout.isatty()
TERM = os.environ.get("TERM", "").lower()
IS_WIN = (os.name == "nt")
NO_COLOR = bool(os.environ.get("NO_COLOR") or os.environ.get("ZDZM_NO_COLOR"))
FORCE_ASCII = bool(os.environ.get("ZDZM_ASCII"))

# 中文 / 框线能否显示：需要 UTF-8 家族编码
UTF8_OK = ("utf-8" in ENCODING or "utf8" in ENCODING
           or "cp65001" in ENCODING or "65001" in ENCODING)

def enable_win_vt():
    """Windows 10 1607+ 开启 VT；失败返回 False。"""
    if not IS_WIN:
        return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(mode)):
            return False
        ok = k.SetConsoleMode(h, mode.value | 0x0004)
        return bool(ok)
    except Exception:
        return False

VT_OK = enable_win_vt()

# 256 色能力：非 Windows 的 tty 通常支持；Windows 即使开了 VT 也只用 16 色稳
HAS_256 = (IS_TTY and not IS_WIN and TERM != "dumb"
           and ("256color" in TERM or TERM in ("xterm", "screen", "tmux", "rxvt")))

# 颜色总开关
COLOR = IS_TTY and not NO_COLOR and TERM != "dumb"

# ---------------------------------------------------------------- 颜色表
# 键 -> (256色序列, 16色序列)；降级时取 16 色
_CMAP = {
    "reset":   ("\033[0m",   "\033[0m"),
    "dim":     ("\033[2m",   "\033[2m"),
    "bold":    ("\033[1m",   "\033[1m"),
    "red":     ("\033[31m",  "\033[31m"),
    "green":   ("\033[32m",  "\033[32m"),
    "yellow":  ("\033[33m",  "\033[33m"),
    "blue":    ("\033[34m",  "\033[34m"),
    "magenta": ("\033[35m",  "\033[35m"),
    "cyan":    ("\033[36m",  "\033[36m"),
    "gray":    ("\033[90m",  "\033[37m"),   # 90 亮黑在部分终端不支持
    "gold":    ("\033[38;5;220m", "\033[33m"),
    "pink":    ("\033[38;5;211m", "\033[35m"),
}

def c(text, key=None):
    """安全上色。任何终端都不会输出乱码控制序列。"""
    s = str(text)
    if not COLOR or not key:
        return s
    pair = _CMAP.get(key)
    if not pair:
        return s
    code = pair[0] if HAS_256 else pair[1]
    return code + s + _CMAP["reset"][0 if HAS_256 else 1]

# ---------------------------------------------------------------- 符号降级
# Unicode 符号 -> ASCII 替身；UTF-8 环境下用原符号
_SYMS = {
    "▶": ">",   "◀": "<",   "↑": "^",  "↓": "v",  "←": "<",  "→": ">",
    "⏎": "<CR>", "✓": "*",  "✚": "x",  "★": "*",  "✦": "*",
    "◆": "*",   "◇": "o",   "◈": "*",  "●": "*",  "○": "o",
    "█": "#",   "░": ".",   "▓": "+",
    "─": "-",   "│": "|",   "├": "+",  "┤": "+",  "┬": "+",  "┴": "+",
    "╭": "+",   "╮": "+",   "╰": "+",  "╯": "+",  "═": "=",
    "…": "...", "·": "-",  "—": "-",
    "⚠": "!",
}

# 非 UTF-8 编码（cp936/cp437等）下，框线和箭头符号会乱码 → 强制 ASCII 降级
USE_UNICODE = UTF8_OK and not FORCE_ASCII

def sym(ch):
    """把单个 UI 符号按终端能力降级。"""
    if USE_UNICODE:
        return ch
    return _SYMS.get(ch, "?" if ord(ch) > 127 else ch)

def line(text):
    """把一整行里的 UI 符号降级（中文保留——编码不支持时由 stream 层处理）。"""
    if USE_UNICODE:
        return text
    return "".join(_SYMS.get(ch, ch) for ch in str(text))

# ---------------------------------------------------------------- 框线辅助
def box_top(title="", width=50):
    """╭─ title ─────╮ / +-- title ----+"""
    if USE_UNICODE:
        seg = (" " + title + " ") if title else ""
        return "╭" + seg + "─" * max(0, width - 2 - len(seg) * 2 // 2) + "╮"
    seg = (" " + title + " ") if title else ""
    return "+" + seg + "-" * max(0, width - 2 - len(seg)) + "+"

def box_mid(width=50):
    return ("├" + "─" * (width - 2) + "┤") if USE_UNICODE else ("+" + "-" * (width - 2) + "+")

def box_bottom(width=50):
    return ("╰" + "─" * (width - 2) + "╯") if USE_UNICODE else ("+" + "-" * (width - 2) + "+")

def box_row(text, width=50):
    if USE_UNICODE:
        return "│" + str(text) + " " * max(0, width - 2 - vw(text)) + "│"
    return "|" + line(text) + " " * max(0, width - 2 - vw(line(text))) + "|"

# ---------------------------------------------------------------- 宽度
ANSI_RE = re.compile(r"\033\[[0-9;]*m")

def vw(s):
    """显示宽度：CJK 算 2，ANSI 算 0。降级后的 ASCII 算 1。"""
    t = ANSI_RE.sub("", str(s))
    if not USE_UNICODE:
        t = line(t)
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in t)

def pad(s, w):
    s = str(s)
    return s + " " * max(0, w - vw(s))

def bar(cur, mx, width=14, color="green"):
    pct = 0 if mx <= 0 else max(0.0, min(1.0, cur / float(mx)))
    f = int(round(pct * width))
    return c(sym("█") * f, color) + c(sym("░") * (width - f), "gray")

# ---------------------------------------------------------------- 输出
def write(text):
    """安全输出：编码不支持的字符自动替换，避免 UnicodeEncodeError。"""
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", "ascii") or "ascii"
        sys.stdout.write(text.encode(enc, "replace").decode(enc, "replace"))

def info():
    """返回能力摘要，供 -v / debug 显示。"""
    return "enc=%s utf8=%s tty=%s color=%s 256=%s unicode=%s vt=%s" % (
        ENCODING or "?", UTF8_OK, IS_TTY, COLOR, HAS_256, USE_UNICODE, VT_OK)
