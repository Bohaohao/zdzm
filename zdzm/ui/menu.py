# -*- coding: utf-8 -*-
"""终端选择菜单：方向键移动，回车确认，q / Esc 返回上级。

非交互环境（管道/重定向）自动降级为数字输入。
"""
import os
import sys

IS_WIN = (os.name == "nt")

from zdzm.ui import term as _t

CL = _t._CMAP
COLOR = _t.COLOR


def _c(t, k=None):
    return _t.c(_t.line(t) if not _t.USE_UNICODE else t, k)

_MENU_LINES = 0


def _read_key():
    """读取一个按键，返回 up/down/left/right/enter/back/quit/数字/字母。"""
    if IS_WIN:
        return _read_key_win()
    return _read_key_unix()


def _read_key_win():
    """Windows：msvcrt。方向键是两字节，前缀 \x00 或 \xe0。"""
    import msvcrt
    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(ch2)
    if ch == "\x1b":
        return "back"
    if ch in ("\r", "\n"):
        return "enter"
    if ch in ("q", "Q"):
        return "quit"
    if ch.isdigit():
        return ch
    if ch.isalpha():
        return ch.lower()
    return None


def _read_key_unix():
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            if seq == "[C":
                return "right"
            if seq == "[D":
                return "left"
            return "back"
        if ch in ("\r", "\n"):
            return "enter"
        if ch in ("q", "Q"):
            return "quit"
        if ch.isdigit():
            return ch
        if ch.isalpha():
            return ch.lower()
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


_MENU_LINES = 0



def place(height):
    """把光标移到「底部贴底」的菜单顶部。不清屏。

    记录高度到 _MENU_LINES，供 clear_menu() 退出时清除整块区域。
    """
    global _MENU_LINES
    _MENU_LINES = height
    import shutil
    try:
        rows = shutil.get_terminal_size((80, 24)).lines
    except Exception:
        rows = 24
    row = max(1, rows - height)      # 留一行给光标，避免触发终端 scroll
    sys.stdout.write("\033[%d;1H" % row)
    sys.stdout.flush()


def clear_menu():
    """清除当前菜单区域（供下一级或退出时使用）。"""
    global _MENU_LINES
    if _MENU_LINES > 0:
        import shutil
        try:
            rows = shutil.get_terminal_size((80, 24)).lines
        except Exception:
            rows = 24
        row = max(1, rows - _MENU_LINES)
        sys.stdout.write("\033[%d;1H" % row)
        sys.stdout.write("\033[J")
        sys.stdout.flush()
        _MENU_LINES = 0


def menu(title, options, subtitle=None, allow_back=True):
    """options: [(label, value, note), ...]

    返回选中项的 value；返回上级返回 "back"；退出返回 None。
    """
    if not options:
        return None

    interactive = sys.stdin.isatty()

    if not interactive:
        # 降级：数字输入
        print("  " + _c(title, "cyan"))
        if subtitle:
            print("  " + _c(subtitle, "gray"))
        for i, (label, _v, note) in enumerate(options):
            print("   %s %s%s" % (_c("[%d]" % (i + 1), "gold"), label,
                                  _c("  " + note, "gray") if note else ""))
        if allow_back:
            print("   %s 返回" % _c("[0]", "gold"))
        try:
            raw = input(_c("  选择: ", "cyan")).strip()
        except EOFError:
            return None
        if not raw.isdigit():
            return "back"
        n = int(raw)
        if n == 0:
            return "back"
        if 1 <= n <= len(options):
            return options[n - 1][1]
        return "back"

    global _MENU_LINES

    # 进入新一级：先抹掉上一级
    clear_menu()

    idx = 0
    n = len(options)
    height = 1 + (1 if subtitle else 0) + n + 1

    while True:
        place(height)
        _MENU_LINES = height
        print("  " + _c("◆ " + title, "cyan"))
        if subtitle:
            print("  " + _c(subtitle, "gray"))
        for i, (label, _v, note) in enumerate(options):
            if i == idx:
                line = "  %s %s" % (_c("▶", "gold"), _c(label, "bold"))
            else:
                line = "    %s" % label
            if note:
                line += "  " + _c(note, "gray")
            print(line)
        tip = "  ↑↓ 选择   回车 确认"
        if allow_back:
            tip += "   q 返回"
        print(_c(tip, "gray"))
        sys.stdout.flush()

        key = _read_key()
        if key == "up":
            idx = (idx - 1) % n
        elif key == "down":
            idx = (idx + 1) % n
        elif key == "enter":
            # 不清除，交给下一级 clear_menu() 抹掉，实现"替换"而非"叠加"
            return options[idx][1]
        elif key in ("back", "quit"):
            clear_menu()
            return "back" if allow_back else None
        elif key and key.isdigit():
            d = int(key)
            if 1 <= d <= n:
                return options[d - 1][1]
