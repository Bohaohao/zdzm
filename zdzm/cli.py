#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
造梦终端 · 交互入口

    python3 main.py            读档/新建
    python3 main.py --new      强制新建
"""
import argparse
import os
import sys
import time


from zdzm.core.rng import Rng
from zdzm.core.state import make_player, recalc
from zdzm.core.campaign import Campaign
from zdzm.core.progress import auto_learn, upgrade_skill, set_loadout, can_learn_active, can_learn_passive, auto_spend
from zdzm.core import gear, storage
from zdzm.data import classes as C
from zdzm.data import zones as Z
from zdzm.data import monsters as MS
from zdzm.data import instances as I
from zdzm.core import collect as COL
import zdzm.ui.menu as MENU
from zdzm.ui.menu import menu
import zdzm.ui.log as L
from zdzm.data import collect as COLD
from zdzm.data import common_passives as CP
from zdzm.data.skills import SKILLS, PASSIVES
from zdzm.data import artifacts as A

CL = {"reset": "\033[0m", "dim": "\033[2m", "bold": "\033[1m",
      "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
      "gold": "\033[38;5;220m", "gray": "\033[90m", "cyan": "\033[36m",
      "blue": "\033[34m", "magenta": "\033[35m"}
COLOR = True


def c(t, k=None):
    if not COLOR or not k:
        return str(t)
    return CL.get(k, "") + str(t) + CL["reset"]


import re as _re
import unicodedata as _ud
ANSI_RE = _re.compile(r"\033\[[0-9;]*m")


def vw(s):
    """显示宽度：CJK 算 2，ANSI 序列算 0。"""
    return sum(2 if _ud.east_asian_width(ch) in ("W", "F") else 1
               for ch in ANSI_RE.sub("", str(s)))


def pad(s, w):
    return str(s) + " " * max(0, w - vw(s))


def bar(cur, mx, width=14, color="green"):
    pct = 0 if mx <= 0 else max(0.0, min(1.0, cur / float(mx)))
    f = int(round(pct * width))
    return c("█" * f, color) + c("░" * (width - f), "gray")


def panel(title, lines, width=54):
    inner = width - 4
    head = (c("╭─ ", "cyan") + c(title, "bold")
            + c(" " + "─" * max(0, inner - vw(title) - 1) + "╮", "cyan"))
    out = [head]
    for ln in lines:
        if ln == "-":
            out.append(c("├" + "─" * (width - 2) + "┤", "cyan"))
        elif ln.startswith("## "):
            t2 = ln[3:]
            seg = "─ " + t2 + " "
            out.append(c("├" + seg + "─" * max(0, width - 2 - vw(seg)) + "┤", "cyan"))
        else:
            out.append(c("│", "cyan") + " " + pad(ln, inner) + " " + c("│", "cyan"))
    out.append(c("╰" + "─" * (width - 2) + "╯", "cyan"))
    return "\n".join(out)


def show_status(p, camp):
    st = p
    lines = []
    lines.append("生命 %s %s %s" % (
        pad(p["hp"], 9), bar(p["hp"], p["max_hp"], 14,
                             "red" if p["hp"] / p["max_hp"] < 0.3 else "green"),
        pad("%d/%d" % (p["hp"], p["max_hp"]), 10)))
    lines.append("战势 %s %s %s" % (
        pad(p["resource"], 9),
        bar(p["resource"], 100, 14, "gold" if p["realm"] else "blue"),
        pad("洞明" if p["realm"] else "", 10)))
    lines.append("经验 %s %s %s" % (
        pad(p.get("xp", 0), 9),
        bar(p.get("xp", 0), C.xp_to_next(p["level"]), 14, "cyan"), ""))
    lines.append("-")
    lines.append("攻击 %-6d 防御 %-6d 暴击 %.1f%%" % (p["atk"], p["def"], p["crit"]))
    lines.append("战力 %-6d 金币 %-8d 技能点 %d" % (gear.power(p), p.get("gold", 0), p["skill_points"]))
    lines.append("-")
    st_now = Z.get(camp.stage)
    art = A.artifact(p.get("artifact"))
    lines.append("法宝 %s" % (art["name"] if art else c("（无）", "gray")))
    if camp.mode == "instance" and camp.instance:
        lines.append("副本 %s" % I.get(camp.instance)["name"])
    else:
        lines.append("进度 %s %s   %s" % (camp.stage, st_now["name"], camp.mode))
    lines.append("已通 %d 关   死亡 %d 次   背包 %d/40" % (
        len(camp.cleared), camp.deaths, len(p["bag"])))
    return panel("%s Lv.%d" % (C.CLASSES[p["cls"]]["name"], p["level"]), lines)


def show_gear(p):
    lines = []
    for s in gear.SLOT_ORDER:
        it = p["equipped"].get(s)
        lines.append("%s %s" % (
            pad(gear.SLOT_NAMES[s], 6),
            gear.equip_line(it) if it else c("（空）", "gray")))
    lines.append("-")
    lines.append("战力 %d" % gear.power(p))
    return panel("装备", lines)


def show_common(p):
    lines = []
    for c0 in CP.all_of():
        lv = CP.level_of(p, c0["key"])
        shown = CP.label(c0, lv)
        price = CP.cost_of(lv)
        tail = ("升级 %d 金" % price) if price is not None else c("已满", "gold")
        lines.append("%-6s %d/5   %s %s   %s" % (
            c0["name"], lv, c0["desc"], shown, tail))
    lines.append("-")
    total = sum(CP.cost_of(CP.level_of(p, c0["key"])) or 0 for c0 in CP.all_of())
    lines.append("金币 %d   全部升一级需 %d" % (p.get("gold", 0), total))
    return panel("通用被动", lines, width=58)


def common_menu(p):
    if not sys.stdin.isatty():
        print(show_common(p))
        return
    idx = 0
    first = True
    toast = ""
    while True:
        rows = CP.all_of()
        n = len(rows)
        height = n + 3
        if not first:
            sys.stdout.write("\033[%dA" % height)
            sys.stdout.write("\033[J")
        first = False
        print("  " + c("◆ 通用被动", "cyan") + "   " +
              c("金币 %d" % p.get("gold", 0), "gold"))
        for i, c0 in enumerate(rows):
            lv = CP.level_of(p, c0["key"])
            mark = "▶" if i == idx else " "
            shown = CP.label(c0, lv)
            price = CP.cost_of(lv)
            tail = c("升级 %d" % price, "green") if price is not None else c("已满", "gold")
            line = "  %s %s %d/5  %s %s   %s" % (
                mark, pad(c0["name"], 5), lv, c0["desc"], shown, tail)
            print(c(line, "bold") if i == idx else line)
        print(c("  ↑↓ 选择   回车 升级   q 返回" if not toast else "  " + toast,
                "gray" if not toast else "green"))
        sys.stdout.flush()
        toast = ""

        key = MENU._read_key()
        if key == "up":
            idx = (idx - 1) % n
        elif key == "down":
            idx = (idx + 1) % n
        elif key in ("enter", " "):
            ok, price, nl = CP.upgrade(p, rows[idx]["key"])
            if ok:
                recalc(p)
                toast = "%s 升到 %d 级，花费 %d 金币" % (rows[idx]["name"], nl, price)
            else:
                toast = "金币不足（需要 %d）" % price if price else "已满级"
        elif key in ("back", "quit"):
            MENU.clear_menu()
            return


def bag_menu(p):
    """背包：分页列表 + 底部按钮区，↑↓ 选，字母键操作，←→ 翻页。"""
    if not sys.stdin.isatty():
        print(show_bag(p))
        return

    return _bag_loop(p, MENU)


def _bag_loop(p, MENU):
    idx = 0
    page = 0
    first = True
    toast = ""

    while True:
        bag = gear.sorted_bag(p)
        n = len(bag)
        pages = max(1, (n + gear.BAG_PAGE - 1) // gear.BAG_PAGE)
        page = max(0, min(page, pages - 1))
        start = page * gear.BAG_PAGE
        rows = bag[start:start + gear.BAG_PAGE]
        if idx < start:
            idx = start
        if idx >= start + len(rows):
            idx = start + max(0, len(rows) - 1)

        height = 1 + max(1, len(rows)) + 4
        if not first:
            sys.stdout.write("\033[%dA" % height)
            sys.stdout.write("\033[J")
        first = False

        print("  " + c("◆ 背包", "cyan") + "   " +
              c("%d/%d 格   第 %d/%d 页" % (n, gear.BAG_MAX, page + 1, pages), "gray"))
        if not rows:
            print(c("  （空）", "gray"))
        for i, it in enumerate(rows):
            gidx = start + i
            mark = "▶" if gidx == idx else " "
            lock = c("锁", "gold") if it.get("locked") else " "
            _, g = gear.best_slot(p, it)
            arrow = c("↑", "green") if g > 0.01 else c("↓", "gray")
            line = "  %s[%2d] %s %s %s %s" % (
                mark, gidx, lock, arrow, pad(gear.equip_line(it), 26),
                c("评分%d" % int(gear.score(it)), "gray"))
            print(c(line, "bold") if gidx == idx else line)
        for _ in range(max(0, gear.BAG_PAGE - len(rows))):
            print("")
        print(c("  " + "─" * 58, "gray"))
        print(c("  [↑↓]选择  [⏎]穿上  [l]锁定  [x]卖出  [←→]翻页  [q]返回", "gray"))
        print(c("  [1]普通 [2]精良 [3]稀有 [4]史诗 [5]传说 [a]全卖 [w]换装", "gray"))
        if toast:
            print(c("  " + toast, "green"))
        else:
            print("")
        sys.stdout.flush()
        toast = ""

        if key == "up":
            idx = max(0, idx - 1)
        elif key == "down":
            idx = min(max(0, n - 1), idx + 1)
        elif key in ("enter", "e") and rows:
            it = bag[idx]
            old = gear.equip(p, it, gear.best_slot(p, it)[0])
            p["bag"].remove(it)
            if old:
                p["bag"].append(old)
            toast = "穿上 %s" % it["name"]
        elif key == "l" and rows:
            it = bag[idx]
            it["locked"] = not it.get("locked")
            toast = "%s %s" % ("已锁定" if it["locked"] else "已解锁", it["name"])
        elif key == "x" and rows:
            it = bag[idx]
            if it.get("locked"):
                toast = "已锁定，先按 l 解锁"
            else:
                p["bag"].remove(it)
                g = gear.sell_price(it)
                p["gold"] = p.get("gold", 0) + g
                toast = "卖出 %s +%d 金币" % (it["name"], g)
        elif key in ("1", "2", "3", "4", "5"):
            q = int(key) - 1
            sold = [x for x in p["bag"] if x.get("quality") == q and not x.get("locked")]
            g = sum(gear.sell_price(x) for x in sold)
            for x in sold:
                p["bag"].remove(x)
            p["gold"] = p.get("gold", 0) + g
            toast = "卖出 %d 件%s +%d 金币" % (len(sold), gear.QUALITY_NAMES[q], g)
        elif key == "a":
            sold = [x for x in p["bag"] if not x.get("locked")]
            g = sum(gear.sell_price(x) for x in sold)
            for x in sold:
                p["bag"].remove(x)
            p["gold"] = p.get("gold", 0) + g
            toast = "全部卖出 %d 件 +%d 金币" % (len(sold), g)
        elif key == "w":
            moved = gear.equip_best(p)
            toast = "换上 %d 件，战力 %.0f" % (len(moved), gear.power(p)) if moved else "没有更好的装备"
        elif key == "left":
            page = max(0, page - 1)
            idx = page * gear.BAG_PAGE
        elif key == "right":
            page = min(pages - 1, page + 1)
            idx = page * gear.BAG_PAGE
        elif key in ("back", "quit"):
            MENU.clear_menu()
            return


def show_bag(p):
    if not p["bag"]:
        return panel("背包", [c("空空如也", "gray")])
    bag = gear.sorted_bag(p)
    base = gear.power(p)
    lines = []
    for i, it in enumerate(bag[:20]):
        slot, g = gear.best_slot(p, it)
        if it.get("locked"):
            mark = c("锁", "gold")
        elif g > 0.01:
            mark = c("↑", "green")
        else:
            mark = c("↓", "gray")
        score = int(gear.score(it))
        lines.append("%s %s %s %s" % (
            ("[%2d]" % i), mark, pad(gear.equip_line(it), 28),
            c("评分%d  %s" % (score, "+%d" % int(g) if g > 0.01 else ""),
              "green" if g > 0.01 else "gray")))
    if len(bag) > 20:
        lines.append(c("…… 还有 %d 件" % (len(bag) - 20), "gray"))
    lines.append("-")
    locked_g = sum(gear.sell_price(x) for x in p["bag"] if not x.get("locked"))
    lines.append("共 %d 件（锁定 %d）  可卖 %d 金币" % (
        len(bag), sum(1 for x in p["bag"] if x.get("locked")), locked_g))
    lines.append(c("sell q0..q4 按品质批量卖   lock N 锁定   wearbest 一键换装", "gray"))
    return panel("背包", lines, width=62)


HELP_GROUPS = [
    ("查看", [
        ("status / s", "角色面板、战力、进度"),
        ("gear / g", "装备与强化"),
        ("collect / c", "9 项收集与称号"),
        ("artifact / art", "法宝，查看与切换"),
    ]),
    ("战斗", [
        ("push", "自动推图，跨副本推进"),
        ("farm 1-1", "循环刷指定副本"),
        ("enter", "选副本进入（菜单）"),
    ]),
    ("成长", [
        ("skills / sk", "技能加点 · ↑↓ 选，回车升，d 降"),
        ("loadout", "技能装配 · ↑↓ 选槽，回车换"),
        ("learn A06|all|auto", "学单个 / 全学 / 一键推荐"),
        ("common", "通用被动 · 金币升级"),
    ]),
    ("物品", [
        ("bag / b", "背包 · ↑↓选 ⏎穿 l锁 x卖 w换装"),
        ("wearbest", "一键穿上更好的（也可按 w）"),
        ("equip N / sell N", "直接穿 / 卖第 N 件"),
        ("lock / unlock N", "锁定 / 解锁第 N 件"),
        ("sell q0-q4", "按品质批量卖，如 sell q2"),
        ("sell all", "全卖，锁定的会跳过"),
    ]),
    ("系统", [
        ("save", "存档"),
        ("quit / q", "存档并退出"),
        ("help / h", "这份帮助"),
    ]),
]


def help_lines():
    col = max(len(c) for _, items in HELP_GROUPS for c, _ in items) + 3
    out = []
    for title, items in HELP_GROUPS:
        out.append("## " + title)
        for cmd, desc in items:
            out.append(cmd + " " * (col - len(cmd)) + desc)
    return out


def _prereq_text(p, key):
    d = SKILLS.get(key) or PASSIVES.get(key) or {}
    unlock = d.get("unlock", 1)
    if p["level"] < unlock:
        return "等级不足（需 Lv%d）" % unlock
    pre = d.get("prereq")
    if pre:
        k, lv = pre
        cur = p["skills"].get(k, 0) or p["passives"].get(k, 0)
        if cur < lv:
            return "需要 %s 到 %d 级（当前 %d）" % (k[-3:], lv, cur)
    return "可学习"


GLOSSARY = {
    "倍率": "伤害 = 攻击力 × 倍率",
    "生势": "命中攒战势，满 80 进洞明",
    "耗势": "释放时消耗的战势",
    "破韧": "清空敌人韧性，4 秒内受伤 +25%",
    "显妄": "目标防御降低，持续数秒",
    "洞明": "战势满后的强化状态",
    "冷却": "两次释放的最小间隔",
}


def _short_req(p, key):
    """菜单用的短前置提示，控制左列宽度。"""
    d = SKILLS.get(key) or PASSIVES.get(key) or {}
    if p["level"] < d.get("unlock", 1):
        return "需 Lv%d" % d["unlock"]
    pre = d.get("prereq")
    if pre:
        k, lv = pre
        cur = p["skills"].get(k, 0) or p["passives"].get(k, 0)
        if cur < lv:
            return "需 %s %d级" % (k[-3:], lv)
    return "可学习"


def skill_detail(key, lv):
    """生成技能说明的若干行，供菜单右侧展示。"""
    out = []
    if key in SKILLS:
        sk = SKILLS[key]
        i = max(0, min((lv or 1) - 1, 4))
        out.append("%s · 主动" % sk["name"])
        out.append(c(sk.get("role", ""), "gray"))
        out.append("")
        out.append("倍率  %d%%" % round(sk["mult"][i] * 100))
        out.append("耗势  %d    冷却  %.1fs" % (sk["cost"], sk["cd"][i]))
        out.append("生势  +%d   破韧  %.1f" % (sk["gain"][i], sk.get("poise", 0)))
        if sk.get("hits", 1) > 1:
            out.append("段数  %d × %d%%" % (sk["hits"], round(sk["mult"][i] * 100)))
        if sk.get("cast", 0) > 0:
            out.append("前摇  %.2fs" % sk["cast"])
        if sk.get("note"):
            out.append(c(sk["note"], "gold"))

        terms = ["倍率"]
        if sk.get("gain"):
            terms.append("生势")
        if sk.get("cost"):
            terms.append("耗势")
        if sk.get("poise"):
            terms.append("破韧")
        if sk.get("debuff_def"):
            terms.append("显妄")
        if sk.get("realm_add"):
            terms.append("洞明")
        out.append(c("── 名词 ──", "gray"))
        for t in terms:
            out.append(c("%s：%s" % (t, GLOSSARY[t]), "gray"))
    else:
        ps = PASSIVES[key]
        out.append("%s · 被动" % ps["name"])
        out.append(c("%s分支 · Lv%d 解锁" % (ps.get("type", ""), ps["unlock"]), "gray"))
        out.append("")
        for fld, label, unit in (("extra_gain", "额外生势", ""),
                                 ("dmg_mid", "中段伤害", "%"),
                                 ("dmg_realm", "洞明伤害", "%"),
                                 ("haste", "攻速", "%"),
                                 ("dr", "减伤", "%"),
                                 ("break_bonus", "破韧", "%"),
                                 ("refund", "返还战势", ""),
                                 ("dmg", "破隙伤害", "%"),
                                 ("def_extra", "显妄降防", "点")):
            arr = ps.get(fld)
            if isinstance(arr, list) and arr:
                idx = max(0, min((lv or 1) - 1, len(arr) - 1))
                out.append("%s  +%s%s" % (label, arr[idx], unit))
        if ps.get("window"):
            out.append("窗口  %.1fs" % ps["window"])
        if ps.get("mastery"):
            out.append(c("5级：" + ps["mastery"], "gold"))

        terms = []
        if ps.get("extra_gain"):
            terms.append("生势")
        if ps.get("break_bonus") or ps.get("dmg") or ps.get("refund"):
            terms.append("破韧" if ps.get("break_bonus") else "战势")
        if ps.get("def_extra"):
            terms.append("显妄")
        if ps.get("dmg_realm") or ps.get("dmg_mid"):
            terms.append("洞明" if ps.get("dmg_realm") else "战势")
        if terms:
            out.append(c("── 名词 ──", "gray"))
            seen = set()
            for t in terms:
                if t in seen or t not in GLOSSARY:
                    continue
                seen.add(t)
                out.append(c("%s：%s" % (t, GLOSSARY[t]), "gray"))
    return out


def _pad_vis(text, width):
    return text + " " * max(0, width - vw(text))


def skill_menu(p):
    """技能加点：列出全部技能，已学可升，满足条件可学，未解锁显示原因。"""
    from zdzm.core.progress import (downgrade, can_learn_active,
                                    can_learn_passive, learn_active, learn_passive)
    if not sys.stdin.isatty():
        print(show_skills(p))
        return

    def build():
        rows = []
        for k in sorted(SKILLS):
            lv = p["skills"].get(k, 0)
            if lv:
                st = "learned"
            elif can_learn_active(p, k):
                st = "available"
            else:
                st = "locked"
            rows.append([k, SKILLS[k]["name"], lv, True, st])
        for k in sorted(PASSIVES):
            lv = p["passives"].get(k, 0)
            if lv:
                st = "learned"
            elif can_learn_passive(p, k):
                st = "available"
            else:
                st = "locked"
            rows.append([k, PASSIVES[k]["name"], lv, False, st])
        return rows

    while True:
        rows = build()
        idx = 0
        first = True
        n = len(rows)
        while True:
            height = n + 2      # 标题 1 + 技能 n + 提示 1
            if not first:
                sys.stdout.write("\033[%dA" % height)
                sys.stdout.write("\033[J")
            first = False
            detail = skill_detail(rows[idx][0], rows[idx][2] or 1)
            LW, BW = 30, 42
            inner = BW - 2
            body = detail[:n - 2]
            while len(body) < n - 2:
                body.append("")
            box = [c("╭" + "─" * inner + "╮", "cyan")]
            for ln in body:
                box.append(c("│", "cyan") + " " + pad(ln, inner - 1) + c("│", "cyan"))
            box.append(c("╰" + "─" * inner + "╯", "cyan"))

            print("  " + c("◆ 技能加点", "cyan") + "   " +
                  c("技能点 %d" % p["skill_points"], "gold"))
            for i, (k, name, lv, is_active, st) in enumerate(rows):
                mark = "▶" if i == idx else " "
                tag = "" if is_active else " 被动"
                if st == "learned":
                    slot = "●" if (is_active and k in p["loadout"]) else " "
                    left = "  %s%s %s %d/5%s" % (mark, slot, pad(name, 9), lv, tag)
                    if lv >= 5:
                        left += " MAX"
                elif st == "available":
                    left = "  %s  %s %s%s" % (mark, pad(name, 9), "可学习", tag)
                else:
                    left = "  %s  %s %s%s" % (mark, pad(name, 9), _short_req(p, k), tag)
                if st == "available":
                    left = left.replace("可学习", c("可学习", "green"))
                elif st == "locked":
                    left = left.replace(name, c(name, "gray"))
                line = pad(left, LW) + (box[i] if i < len(box) else "")
                print(c(line, "bold") if i == idx else line)
            print(c("  ↑↓ 选择   回车 学习/升级   d 降级   q 返回", "gray"))
            sys.stdout.flush()

            key = MENU._read_key()
            if key == "up":
                idx = (idx - 1) % n
            elif key == "down":
                idx = (idx + 1) % n
            elif key == "enter":
                k, name, lv, is_active, st = rows[idx]
                if st == "learned":
                    upgrade_skill(p, k, 5)
                elif st == "available":
                    if is_active:
                        learn_active(p, k)
                    else:
                        learn_passive(p, k)
                rows = build()
                n = len(rows)
            elif key == "d":
                downgrade(p, rows[idx][0])
                rows = build()
                n = len(rows)
            elif key in ("back", "quit"):
                MENU.clear_menu()
                return


def loadout_menu(p):
    """技能装配：↑↓ 选槽，回车换技能，d 卸下，q 返回。"""
    if not sys.stdin.isatty():
        print(c("  当前装配：%s" % " ".join(k[-3:] for k in p["loadout"]), "gray"))
        return
    slots = [""] * 5
    for i, k in enumerate(p["loadout"][:5]):
        slots[i] = k
    idx = 0
    first = True
    while True:
        height = 5 + 2          # 标题 + 5 个槽 + 提示
        if not first:
            sys.stdout.write("\033[%dA" % height)
            sys.stdout.write("\033[J")
        first = False
        print("  " + c("◆ 技能装配", "cyan") + "   " + c("5 个主动槽", "gray"))
        for i in range(5):
            k = slots[i]
            name = SKILLS[k]["name"] if k else c("（空）", "gray")
            mark = "▶" if i == idx else " "
            line = "  %s [%d] %-10s" % (mark, i + 1, name)
            print(c(line, "bold") if i == idx else line)
        print(c("  ↑↓ 选择槽位   回车 更换   d 卸下   q 返回", "gray"))
        sys.stdout.flush()

        key = MENU._read_key()
        if key == "up":
            idx = (idx - 1) % 5
        elif key == "down":
            idx = (idx + 1) % 5
        elif key == "enter":
            avail = [k for k in sorted(p["skills"]) if k not in slots]
            if not avail:
                continue
            MENU.clear_menu()
            opts = [(SKILLS[k]["name"], k, "") for k in avail]
            pick = menu("选择技能", opts)
            if pick in (None, "back"):
                sys.stdout.write("\033[J")
                continue
            slots[idx] = pick
            set_loadout(p, [x for x in slots if x])
        elif key == "d":
            slots[idx] = ""
            set_loadout(p, [x for x in slots if x])
        elif key in ("back", "quit"):
            MENU.clear_menu()
            return


def show_skills(p):
    """非交互环境的技能清单：全部技能，分已学 / 可学 / 未解锁。"""
    from zdzm.core.progress import can_learn_active, can_learn_passive
    lines = []
    for key in sorted(SKILLS):
        sk = SKILLS[key]
        lv = p["skills"].get(key, 0)
        slot = c("●", "green") if key in p["loadout"] else c(" ", "gray")
        if lv:
            lines.append("%s %s %-8s %d/5" % (slot, key[-3:], sk["name"], lv))
        elif can_learn_active(p, key):
            lines.append("%s %s %-8s %s" % (slot, key[-3:], sk["name"], c("可学习", "green")))
        else:
            lines.append("%s %s %-8s %s" % (c(" ", "gray"), key[-3:], sk["name"],
                                           c(_prereq_text(p, key), "gray")))
    lines.append("-")
    for key in sorted(PASSIVES):
        ps = PASSIVES[key]
        lv = p["passives"].get(key, 0)
        if lv:
            lines.append("  %s %-8s %d/5  %s" % (key[-3:], ps["name"], lv, c(ps["type"], "gray")))
        elif can_learn_passive(p, key):
            lines.append("  %s %-8s %s" % (key[-3:], ps["name"], c("可学习", "green")))
        else:
            lines.append("  %s %-8s %s" % (key[-3:], ps["name"], c(_prereq_text(p, key), "gray")))
    lines.append("-")
    lines.append("技能点 %d   ●装配中 %d/5" % (p["skill_points"], len(p["loadout"])))
    return panel("技能", lines, width=58)


def enter_menu(p, camp):
    """篇章 -> 主线/副本 -> 具体关卡。返回 (kind, key) 或 None。"""
    while True:
        ch = menu("选择篇章", [
            ("花果山篇   Lv1-20", "hg", "当前篇章"),
            ("地府篇     Lv21-40", "df", "未开放"),
            ("天庭篇     Lv41-60", "tf", "未开放"),
        ], subtitle="当前 %s · Lv%d" % (camp.stage, p["level"]))
        if ch in (None, "back"):
            return None
        if ch != "hg":
            print(c("  该篇章尚未开放", "gray"))
            continue

        kind = menu("花果山篇", [
            ("主线副本", "main", "6 个副本"),
            ("隐藏副本", "inst", "龙宫旧潮 / 牛魔旧战场"),
        ])
        if kind in (None, "back"):
            continue

        if kind == "main":
            opts = []
            for r in Z.REGIONS:
                entry = r["stages"][0]["key"]
                total = len(r["stages"])
                done = sum(1 for st in r["stages"] if st["key"] in (p.get("cleared") or []))
                mark = "✓" if done >= total else " "
                opts.append(("%s %-4s %-8s Lv%d-%d  %d/%d 阶段" % (
                    mark, entry, r["name"], r["lv"][0], r["lv"][1], done, total),
                    r["key"], ""))
            rk = menu("主线副本", opts, subtitle="选中后从入口打到该副本最后一阶段")
            if rk in (None, "back"):
                continue
            camp.enter_region(rk)
            return ("region", rk)

        if kind == "inst":
            opts = []
            for inst in I.list_all():
                done = "✓" if inst["key"] in (p.get("instance_clears") or []) else " "
                opts.append(("%s %-10s Lv%-2d" % (done, inst["name"], inst["level"]),
                             inst["key"], "限时 %d 秒" % inst["time_limit"]))
            ik = menu("副本", opts, subtitle="✓ = 已通关")
            if ik in (None, "back"):
                continue
            camp.enter_instance(ik)
            return ("instance", ik)


SHOW_KINDS = {"attack", "skill", "hurt", "artifact", "break", "realm", "p05", "gap"}


def battle_event(ev):
    """战斗中实时输出（不含 spawn/kill，那两个由 logger 处理）。"""
    if ev["kind"] in SHOW_KINDS:
        print(L.render(ev))


def run_realtime(camp, speed=1.0, stop=None, tick=0.02):
    """按真实时间推进游戏，speed 为倍速。让日志有正常呼吸节奏。"""
    last = time.time()
    while True:
        if stop and stop():
            return
        now = time.time()
        dt = min((now - last) * speed, 0.25)
        last = now
        if dt > 0:
            camp.run(camp.t + dt)
        time.sleep(tick)


def make_logger(camp_ref, quiet=False):
    def say(kind, **kw):
        if quiet:
            return
        t = "[%7.1f]" % (camp_ref[0].battle.tl.now if camp_ref[0] and camp_ref[0].battle else 0)
        if kind == "stage_clear":
            st = Z.get(kw["stage"])
            print("%s %s 通关 %s %s" % (c(t, "dim"), c("─", "gray"),
                                       kw["stage"], st["name"]))
        elif kind == "death":
            print("%s %s 死亡 Lv.%d 回营地" % (c(t, "dim"), c("X", "red"), kw["level"]))
        elif kind == "levelup":
            print("%s %s 升级 Lv.%d" % (c(t, "dim"), c("★", "gold"), kw["level"]))
        elif kind == "region_stage":
            st = Z.get(kw["cur"])
            print("%s %s 下一阶段 %s %s" % (c(t, "dim"), c("→", "gray"),
                                          kw["cur"], st["name"]))
        elif kind == "region_clear":
            print("%s %s %s 通关 · %d 阶段全部完成" % (
                c(t, "dim"), c("★", "gold"), kw["name"], kw["stages"]))
        elif kind == "stage_once_clear":
            st = Z.get(kw["stage"])
            print("%s %s 通关 %s %s" % (c(t, "dim"), c("─", "gray"),
                                       kw["stage"], st["name"]))
        elif kind == "instance_enter":
            print("%s %s 进入 %s（Lv%d）" % (c(t, "dim"), c("▶", "cyan"), kw["name"], kw["level"]))
        elif kind == "instance_clear":
            print("%s %s %s 通关%s" % (
                c(t, "dim"), c("★", "gold"), kw["name"],
                c("  首通！" + (kw.get("reward") or ""), "green") if kw.get("first") else ""))
        elif kind == "artifact_gain":
            print("%s %s 获得法宝 %s" % (c(t, "dim"), c("✦", "gold"), kw["name"]))
        elif kind == "set_gain":
            print("%s %s 获得套装 %s" % (c(t, "dim"), c("✦", "gold"), kw["name"]))
        elif kind == "collect":
            print("%s %s 收集解锁：%s  %s" % (
                c(t, "dim"), c("◆", "gold"), kw["name"], c(kw["reward"], "green")))
        elif kind == "paused":
            print("%s %s 连续死亡 %d 次，已暂停推图" % (
                c(t, "dim"), c("!", "red"), kw["streak"]))
            print(c("    用 farm <关> 去刷装备，或再敲 push 继续", "gray"))

    def on_kill(mon, gold, settlements):
        if quiet:
            return
        t = "[%7.1f]" % camp_ref[0].battle.tl.now
        extra = ""
        for s in settlements:
            it = s["item"]
            if s.get("equipped"):
                extra = "  " + c("[换上 %s]" % it["name"], "green")
            elif it["quality"] >= 3:
                extra = "  " + c("[%s %s]" % (it["quality_name"], it["name"]), "yellow")
        print("%s   %s %s%s" % (
            c(t, "dim"), c(mon["name"].ljust(8), "gray"),
            c("+%dxp" % mon.get("xp", 0), "dim"), extra))
    return say, on_kill


def new_player(seed=None):
    p = make_player("C01", 1)
    auto_learn(p)
    p["char_id"] = os.urandom(6).hex()
    return p


def load_or_new(args):
    if args.new:
        return new_player(), None
    while True:
        saves = storage.list_saves()
        if not saves:
            print(c("  没有存档，新建角色", "gray"))
            return new_player(), None
        print()
        print(c("── 存档 " + "─" * 44, "gray"))
        for i, s2 in enumerate(saves[:9]):
            print("  %s Lv.%-3d %-4s  %s" % (
                c("[%d]" % (i + 1), "yellow"), s2["level"], s2["stage"],
                time.strftime("%m-%d %H:%M", time.localtime(s2["saved_at"]))))
        print("  %s 新建角色" % c("[n]", "yellow"))
        print("  %s 删除某个存档    %s 删除全部" % (c("[d1]", "red"), c("[da]", "red")))
        print()
        try:
            raw = input(c("  选择: ", "cyan")).strip().lower()
        except EOFError:
            print()
            return new_player(), None

        if raw == "n":
            return new_player(), None

        if raw == "da":
            try:
                sure = input(c("  删除全部 %d 个存档？不可恢复 (y/N): " % len(saves), "red")).strip().lower()
            except EOFError:
                sure = "n"
            if sure == "y":
                n = storage.delete_all()
                print(c("  已删除 %d 个存档" % n, "green"))
            else:
                print(c("  已取消", "gray"))
            continue

        if raw.startswith("d") and raw[1:].isdigit():
            i = int(raw[1:]) - 1
            if 0 <= i < len(saves):
                s2 = saves[i]
                try:
                    sure = input(c("  删除 %s Lv.%d？不可恢复 (y/N): " % (
                        s2["char_id"][:6], s2["level"]), "red")).strip().lower()
                except EOFError:
                    sure = "n"
                if sure == "y":
                    storage.delete(s2["char_id"])
                    print(c("  已删除", "green"))
                else:
                    print(c("  已取消", "gray"))
            else:
                print(c("  没有这个编号", "red"))
            continue

        if raw.isdigit() and 1 <= int(raw) <= min(9, len(saves)):
            s2 = saves[int(raw) - 1]
            data = storage.load(s2["char_id"])
            p = new_player()
            storage.apply(p, data)
            recalc(p)
            p["hp"] = p["max_hp"]
            return p, data

        print(c("  输入编号、n（新建）、d1（删第1个）、da（全删）", "red"))


def main():
    global COLOR
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--char", default=None)
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0)
    args = ap.parse_args()

    if args.no_color or not sys.stdout.isatty():
        COLOR = False
    MENU.COLOR = COLOR
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    p, data = load_or_new(args)
    stage = (data or {}).get("stage", Z.first_key())
    mode = (data or {}).get("mode", "push")

    ref = [None]
    say, on_kill = make_logger(ref)
    camp = Campaign(p, Rng(getattr(args, "seed", None)),
                    mode=mode, stage=stage, log_kill=on_kill, say=say,
                    on_event=battle_event)
    if data:
        camp.cleared = data.get("cleared", [])
        camp.deaths = data.get("deaths", 0)
    ref[0] = camp

    print()
    print(c("═══ 造梦终端 ═══", "bold"))
    print("  %s Lv.%d   %s %s  %s" % (
        C.CLASSES[p["cls"]]["name"], p["level"],
        camp.stage, Z.get(camp.stage)["name"], camp.mode))
    print(c("  敲 help 看命令", "gray"))
    print()

    while True:
        try:
            raw = input(c("%s> " % p["char_id"][:6], "green")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()
        arg = parts[1:]

        if cmd in ("quit", "exit", "q"):
            break

        if cmd in ("help", "h", "?"):
            print(panel("命令", help_lines(), width=58))
            continue

        if cmd in ("enter", "inst"):
            got = enter_menu(p, camp)
            MENU.clear_menu()
            if not got:
                continue
            kind, key = got
            if kind == "region":
                r = Z.REGIONS_BY_KEY[key]
                print(c("  进入 %s · %d 阶段" % (r["name"], len(r["stages"])), "gray"))
            else:
                print(c("  进入 %s" % I.get(key)["name"], "gray"))
            print(c("  Ctrl+C 退出", "gray"))
            try:
                run_realtime(camp, args.speed,
                             stop=lambda: camp.mode not in ("instance", "region") or camp.paused)
            except KeyboardInterrupt:
                print()
            print(c("  离开 · %s" % camp.stage, "gray"))
            continue

        if cmd in ("skills", "sk"):
            skill_menu(p)
            camp.save_now()
            continue

        if cmd == "learn":
            if not arg:
                print(c("  用法：learn <技能> [等级]   例 learn A06 3", "red"))
                continue
            if arg[0].lower() in ("all", "全部"):
                from zdzm.core.progress import learn_active as LA, learn_passive as LP
                n = 0
                for k in list(SKILLS):
                    if LA(p, k):
                        n += 1
                for k in list(PASSIVES):
                    if LP(p, k):
                        n += 1
                print(c("  学了 %d 个技能，剩余点数 %d" % (n, p["skill_points"]), "green" if n else "gray"))
                continue
            if arg[0].lower() in ("auto", "推荐", "一键"):
                auto_spend(p)
                print(c("  已按推荐方案分配，剩余点数 %d" % p["skill_points"], "green"))
                continue
            key = arg[0].upper()
            if not key.startswith("C01_"):
                key = "C01_" + (key if key[0] in "AP" else "A" + key)
            tgt = int(arg[1]) if len(arg) > 1 and arg[1].isdigit() else 5
            if key in p["skills"] or key in p["passives"]:
                n = upgrade_skill(p, key, tgt)
                if n:
                    lv = p["skills"].get(key) or p["passives"].get(key)
                    print(c("  %s 升了 %d 级 → %d 级，剩余点数 %d" % (key[-3:], n, lv, p["skill_points"]), "green"))
                else:
                    print(c("  无法升级（点数不足或已满级）", "red"))
            elif key in SKILLS:
                if can_learn_active(p, key):
                    from zdzm.core.progress import learn_active
                    learn_active(p, key)
                    print(c("  学会 %s，剩余点数 %d" % (SKILLS[key]["name"], p["skill_points"]), "green"))
                else:
                    print(c("  %s" % _prereq_text(p, key), "red"))
            elif key in PASSIVES:
                if can_learn_passive(p, key):
                    from zdzm.core.progress import learn_passive
                    learn_passive(p, key)
                    print(c("  学会 %s，剩余点数 %d" % (PASSIVES[key]["name"], p["skill_points"]), "green"))
                else:
                    print(c("  %s" % _prereq_text(p, key), "red"))
            else:
                print(c("  没有这个技能", "red"))
            continue

        if cmd in ("loadout", "lo"):
            if not arg:
                loadout_menu(p)
                camp.save_now()
                continue
            if False:
                print(c("  当前装配：%s" % " ".join(k[-3:] for k in p["loadout"]), "gray"))
                print(c("  改装配：loadout A02 A06 A05 A01 A08", "gray"))
                continue
            keys = []
            for a in arg:
                k = a.upper()
                if not k.startswith("C01_"):
                    k = "C01_" + (k if k[0] in "AP" else "A" + k)
                keys.append(k)
            got = set_loadout(p, keys)
            print(c("  装配：%s" % " ".join(k[-3:] for k in got), "green"))
            continue

        if cmd in ("collect", "c"):
            rows = COL.summary(p)
            lines = []
            for cc, v, need, done in rows:
                mark = c("◆", "gold") if done else c("·", "gray")
                lines.append("%s %-8s %3d/%-3d  %s" % (
                    mark, cc["name"], v, need, c(cc["desc"], "gray")))
            lines.append("-")
            lines.append("已解锁 %d/%d   称号 %d 个" % (
                sum(1 for x in rows if x[3]), len(rows), len(p.get("titles") or [])))
            print(panel("收集 · 花果山", lines, width=58))
            continue

        if cmd in ("artifact", "art"):
            owned = p.get("artifacts_owned") or []
            if not owned:
                print(c("  还没有法宝。首通龙宫旧潮可获得定潮玄印", "gray"))
                continue
            cur = p.get("artifact")
            for i, k in enumerate(owned):
                a = A.artifact(k)
                mark = c("●", "green") if k == cur else c("○", "gray")
                print("  %s %s  %s" % (mark, a["name"], c(a["desc"], "gray")))
            if arg and arg[0].isdigit():
                i = int(arg[0])
                if 0 <= i < len(owned):
                    p["artifact"] = owned[i]
                    recalc(p)
                    print(c("  已切换到 %s" % A.artifact(owned[i])["name"], "green"))
            continue

        if cmd in ("status", "s"):
            print(show_status(p, camp))
            continue

        if cmd in ("gear", "g"):
            print(show_gear(p))
            continue

        if cmd in ("common", "cp", "gp"):
            common_menu(p)
            camp.save_now()
            continue

        if cmd in ("bag", "b"):
            bag_menu(p)
            camp.save_now()
            continue

        if cmd in ("push", "run"):
            camp.mode = "push"
            camp.resume()
            print(c("  自动推图 · %s 起" % camp.stage, "gray"))
            print(c("  Ctrl+C 停止", "gray"))
            try:
                run_realtime(camp, args.speed, stop=lambda: camp.paused)
            except KeyboardInterrupt:
                print()
            print(c("  停止 · %s %s" % (camp.stage, Z.get(camp.stage)["name"]), "gray"))
            continue

        if cmd == "farm":
            key = arg[0] if arg else None
            if not key or key not in Z.STAGES:
                print(c("  用法：farm 1-1   循环刷该副本（自动从入口开始）", "red"))
                print(c("  可用：%s" % " ".join(
                    Z.REGIONS_BY_KEY[r]["stages"][0]["key"] for r in Z.REGIONS), "gray"))
                continue
            region = Z.STAGES[key]["region"]
            camp.farm_region(region)
            r = Z.REGIONS_BY_KEY[region]
            print(c("  循环刷 %s（%d 阶段）" % (r["name"], len(r["stages"])), "gray"))
            print(c("  Ctrl+C 停止", "gray"))
            try:
                run_realtime(camp, args.speed, stop=lambda: camp.paused)
            except KeyboardInterrupt:
                print()
            print(c("  停止 · %s" % Z.get(camp.stage)["name"], "gray"))
            continue

        if cmd == "equip":
            if not arg or not arg[0].isdigit():
                print(c("  用法：equip <背包编号>", "red"))
                continue
            i = int(arg[0])
            if not (0 <= i < len(p["bag"])):
                print(c("  没有这个编号", "red"))
                continue
            it = p["bag"].pop(i)
            slot, _ = gear.best_slot(p, it)
            old = gear.equip(p, it, slot)
            if old:
                p["bag"].append(old)
            print(c("  穿上 %s" % gear.equip_line(it), "green"))
            continue

        if cmd == "sell":
            if not arg:
                print(c("  用法：sell <编号> | sell q<0-4> | sell all", "red"))
                print(c("        q0普通 q1精良 q2稀有 q3史诗 q4传说", "gray"))
                continue

            # 按品质批量卖（跳过锁定）
            if arg[0].startswith("q") and arg[0][1:].isdigit():
                q = int(arg[0][1:])
                if q > 4:
                    print(c("  品质只有 0-4", "red"))
                    continue
                sold = [x for x in p["bag"] if x.get("quality") == q and not x.get("locked")]
                locked = [x for x in p["bag"] if x.get("quality") == q and x.get("locked")]
                g = sum(gear.sell_price(x) for x in sold)
                for x in sold:
                    p["bag"].remove(x)
                p["gold"] = p.get("gold", 0) + g
                msg = "  卖了 %d 件%s，+%d 金币" % (
                    len(sold), gear.QUALITY_NAMES[q], g)
                if locked:
                    msg += c("（%d 件锁定跳过）" % len(locked), "gray")
                print(c(msg, "green") if sold else c("  没有可卖的同品质装备", "gray"))
                continue

            if arg[0] == "all":
                sold = [x for x in p["bag"] if not x.get("locked")]
                locked = [x for x in p["bag"] if x.get("locked")]
                g = sum(gear.sell_price(x) for x in sold)
                for x in sold:
                    p["bag"].remove(x)
                p["gold"] = p.get("gold", 0) + g
                msg = "  卖了 %d 件，+%d 金币" % (len(sold), g)
                if locked:
                    msg += c("（%d 件锁定跳过）" % len(locked), "gray")
                print(c(msg, "green"))
                continue

            if arg[0].isdigit():
                idx = int(arg[0])
                bag = gear.sorted_bag(p)
                if 0 <= idx < len(bag):
                    it = bag[idx]
                    if it.get("locked"):
                        print(c("  该装备已锁定，先 unlock %d" % idx, "red"))
                        continue
                    p["bag"].remove(it)
                    g = gear.sell_price(it)
                    p["gold"] = p.get("gold", 0) + g
                    print(c("  卖了 %s，+%d 金币" % (it["name"], g), "green"))
                    continue
            print(c("  编号不对", "red"))
            continue

        if cmd in ("lock", "unlock"):
            if not arg or not arg[0].isdigit():
                print(c("  用法：lock <编号> / unlock <编号>", "red"))
                continue
            idx = int(arg[0])
            bag = gear.sorted_bag(p)
            if 0 <= idx < len(bag):
                it = bag[idx]
                it["locked"] = (cmd == "lock")
                print(c("  %s %s" % ("已锁定" if cmd == "lock" else "已解锁", it["name"]),
                        "green"))
            else:
                print(c("  编号不对", "red"))
            continue

        if cmd == "wearbest":
            moved = gear.equip_best(p)
            camp.save_now()
            if not moved:
                print(c("  没有更好的装备了", "gray"))
                continue
            for slot, new_it, old_it in moved:
                print(c("  %s → %s" % (
                    gear.SLOT_NAMES.get(slot, slot), new_it["name"]), "green"))
            print(c("  共换 %d 件，战力 %.0f" % (len(moved), gear.power(p)), "green"))
            continue

        if cmd == "save":
            path = storage.save(p, camp)
            print(c("  已保存 → %s" % path, "gray"))
            continue

        print(c("  没有这个命令，敲 help", "red"))

    path = storage.save(p, camp)
    print(c("  存档 → %s" % path, "gray"))
    print(c("  再见", "gray"))


if __name__ == "__main__":
    main()
