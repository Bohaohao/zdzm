# -*- coding: utf-8 -*-
"""全量交互冒烟：所有命令 / 菜单交互 / 状态切换，捕获任何异常。

用法：python3 tools/dev_smoke.py
"""
import os
import sys
import re
import pty
import time
import select
import fcntl
import termios
import struct
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PASS = 0
FAIL = 0
PROBLEMS = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        PROBLEMS.append("%s: %s" % (name, detail))
    print("%s %-46s %s" % ("✓" if ok else "✗", name, detail))


class Term:
    def __init__(self, fresh=True, rows=40, cols=100):
        if fresh:
            for f in os.listdir(os.path.expanduser("~/.zdzm")) if os.path.isdir(os.path.expanduser("~/.zdzm")) else []:
                try:
                    os.remove(os.path.join(os.path.expanduser("~/.zdzm"), f))
                except OSError:
                    pass
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(ROOT)
            os.execvp("python3", ["python3", "-m", "zdzm", "--no-color"])
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.buf = b""
        self.tick(0.8)

    def tick(self, t=0.35):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.03)
            if r:
                try:
                    self.buf += os.read(self.fd, 65536)
                except OSError:
                    break
        return self

    def send(self, data, t=0.35):
        os.write(self.fd, data if isinstance(data, bytes) else data.encode())
        return self.tick(t)

    def text(self):
        return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", self.buf.decode("utf-8", "ignore"))

    def errors(self):
        t = self.text()
        return [ln.strip() for ln in t.split("\n")
                if "Traceback" in ln or "Error:" in ln or "Exception" in ln]

    def clearbuf(self):
        self.buf = b""

    def close(self):
        try:
            self.send(b"quit\r", 0.3)
            os.close(self.fd)
            os.waitpid(self.pid, 0)
        except Exception:
            pass


print("=== A. 全命令冒烟 ===")
t = Term(fresh=True)
t.send(b"\r")             # 空存档→创建界面，确认职业
t.send(b"\r")             # 默认昵称
t.clearbuf()
cmds = [
    (b"status\r", "角色面板"), (b"s\r", "s 别名"),
    (b"gear\r", "装备面板"), (b"g\r", "g 别名"),
    (b"bag\r", "背包面板"), (b"b\r", "b 别名"),
    (b"skills\r", "技能面板"), (b"sk\r", "sk 别名"),
    (b"collect\r", "收集面板"), (b"c\r", "c 别名"),
    (b"artifact\r", "法宝面板"), (b"art\r", "art 别名"),
    (b"common\r", "通用被动"), (b"cp\r", "cp 别名"),
    (b"loadout\r", "装配菜单"), (b"lo\r", "lo 别名"),
    (b"learn all\r", "learn all"), (b"learn auto\r", "learn auto"),
    (b"wearbest\r", "wearbest"),
    (b"sell all\r", "sell all"),
    (b"equip 0\r", "equip 空包"),
    (b"lock 0\r", "lock 空包"),
    (b"unlock 0\r", "unlock 空包"),
    (b"help\r", "help"), (b"h\r", "h 别名"),
    (b"save\r", "save"),
    (b"bogus\r", "未知命令"),
]
for cmd, name in cmds:
    t.clearbuf()
    t.send(cmd)
    errs = t.errors()
    check("命令 " + name, not errs, "; ".join(errs[:2]))
t.close()

print()
print("=== B. 每个菜单的按键交互 ===")
menus = [
    ("skills", b"sk\r", [b"\x1b[B", b"\x1b[A", b"\r", b"d", b"\r", b"q"]),
    ("loadout", b"lo\r", [b"\x1b[B", b"\x1b[A", b"\r", b"d", b"q"]),
    ("common", b"common\r", [b"\x1b[B", b"\x1b[A", b"\r", b"q"]),
    ("bag", b"b\r", [b"\x1b[B", b"\x1b[A", b"l", b"x", b"w", b"1", b"a", b"\x1b[C", b"\x1b[D", b"q"]),
]
for name, enter, keys in menus:
    t = Term(fresh=True)
    t.send(b"\r")             # 创建界面确认
    t.send(b"\r")             # 默认昵称
    t.clearbuf()
    t.send(enter, 0.6)
    for k in keys:
        t.send(k, 0.2)
    errs = t.errors()
    check("菜单 " + name + " 全按键", not errs, "; ".join(errs[:2]))
    t.close()

print()
print("=== C. enter 三级菜单 ===")
t = Term(fresh=True)
t.send(b"\r")
t.send(b"\r")
t.clearbuf()
t.send(b"enter\r", 0.5)
for k in [b"\x1b[B", b"\x1b[A", b"\r", b"\x1b[B", b"\r", b"\x1b[B", b"\r", b"q",
          b"q"]:
    t.send(k, 0.3)
errs = t.errors()
check("enter 三级导航 + 逐级返回", not errs, "; ".join(errs[:2]))
t.close()

print()
print("=== D. 命令 → 菜单 → 命令 状态切换 ===")
t = Term(fresh=True)
t.send(b"\r")
t.send(b"\r")
seq = [(b"g\r", "g"), (b"b\r", "b"), (b"q\r", "q退出"), (b"s\r", "s"),
       (b"sk\r", "sk"), (b"q\r", "q退出"), (b"common\r", "common"),
       (b"q\r", "q退出"), (b"status\r", "status")]
for cmd, label in seq:
    t.clearbuf()
    t.send(cmd, 0.4)
    errs = t.errors()
    check("切换 " + label, not errs, "; ".join(errs[:2]))
t.close()

print()
print("=== E. 存档菜单 ===")
t = Term(fresh=True)
t.send(b"\r"); t.send(b"\r"); t.send(b"quit\r", 0.4)   # 建 1 个存档
t2 = Term(fresh=False)
txt = t2.text()          # 不 clearbuf：存档列表在初始输出里
check("存档列表可见", "存档" in txt, "")
t2.send(b"d1\r", 0.3); t2.send(b"n\r", 0.3)   # 删一个（取消）
check("存档删除取消无异常", not t2.errors(), "; ".join(t2.errors()[:2]))
t2.send(b"d1\r", 0.3); t2.send(b"y\r", 0.4)   # 真删
check("存档删除执行无异常", not t2.errors(), "; ".join(t2.errors()[:2]))
t2.close()
t.close()

print()
print("=" * 60)
print("通过 %d / 失败 %d" % (PASS, FAIL))
if PROBLEMS:
    print("\n问题清单:")
    for p in PROBLEMS:
        print("  - " + p)
sys.exit(1 if FAIL else 0)
