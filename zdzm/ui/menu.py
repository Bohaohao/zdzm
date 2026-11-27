# -*- coding: utf-8 -*-
"""终端选择菜单：方向键移动，回车确认，q / Esc 返回上级。

非交互环境（管道/重定向）自动降级为数字输入。
"""
import sys

CL = {"reset": "\033[0m", "dim": "\033[2m", "bold": "\033[1m",
      "cyan": "\033[36m", "green": "\033[32m", "gold": "\033[38;5;220m",
      "gray": "\033[90m", "red": "\033[31m"}
COLOR = True


def _c(t, k=None):
    if not COLOR or not k:
        return str(t)
    return CL.get(k, "") + str(t) + CL["reset"]


def cursor_pos():
    """查询光标位置 (row, col)。失败返回 None。"""
    import select
    import time
    sys.stdout.write("\033[6n")
    sys.stdout.flush()
    buf = ""
    end = time.time() + 0.12
    while time.time() < end:
        r, _, _ = select.select([sys.stdin], [], [], 0.02)
        if not r:
            continue
        ch = sys.stdin.read(1)
        buf += ch
        if ch == "R":
            break
    i = buf.find("\033[")
    j = buf.find("R", i)
    if i < 0 or j < 0:
        return None
    try:
        row, col = buf[i + 2:j].split(";")
        return int(row), int(col)
    except ValueError:
        return None


def mouse_on():
    sys.stdout.write("\033[?1000h\033[?1006h")
    sys.stdout.flush()


def mouse_off():
    sys.stdout.write("\033[?1000l\033[?1006l")
    sys.stdout.flush()


def _read_key():
    """读取一个按键，返回 up/down/enter/back/quit/None。"""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq.startswith("[<"):
                rest = ""
                while True:
                    c2 = sys.stdin.read(1)
                    rest += c2
                    if c2 in ("M", "m"):
                        break
                try:
                    b, x, y = rest[:-1].split(";")
                    return ("mouse", int(b), int(x), int(y), rest[-1] == "M")
                except ValueError:
                    return None
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


def clear_menu():
    """清除当前菜单区域（供下一级或退出时使用）。"""
    global _MENU_LINES
    if _MENU_LINES > 0:
        sys.stdout.write("\033[%dA" % _MENU_LINES)
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
        if _MENU_LINES > 0:
            sys.stdout.write("\033[%dA" % _MENU_LINES)
        sys.stdout.write("\033[J")
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
