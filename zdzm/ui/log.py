# -*- coding: utf-8 -*-
"""事件 -> 日志行。这里只读 Event，不碰 State。"""
from zdzm.ui import term as _t

COLOR = _t.COLOR
C = _t._CMAP


def c(text, color=None):
    return _t.c(text, color)


def enable_ansi():
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass


def bar(cur, mx, width=16, color="green"):
    pct = 0.0 if mx <= 0 else max(0.0, min(1.0, cur / float(mx)))
    fill = int(round(pct * width))
    return c("█" * fill, color) + c("░" * (width - fill), "gray")


def render(ev):
    k = ev["kind"]
    t = ev["t"]
    head = c("[%6.2f]" % t, "dim")

    if k == "cast_start":
        return "%s %s %s 起手 %.2fs" % (
            head, c("…", "gray"), c(ev["name"], "cyan"), ev["cast"])

    if k == "skill":
        crit = c(" 暴击x%d" % ev["crits"], "yellow") if ev["crits"] else ""
        add = c(" +%d" % ev["add"], "gray") if ev.get("add") else ""
        cost = c(" -%d势" % ev["cost"], "gray") if ev["cost"] else ""
        gain = c(" +%d→%d" % (ev["gain"], ev["resource"]), "blue") if ev["gain"] else ""
        realm = c(" 洞明", "gold") if ev.get("realm") else ""
        return "%s %s %s %s%s%s%s  (%d/%d)%s%s" % (
            head, c("»", "cyan"), c(ev["name"], "bold"),
            c("-%d" % ev["value"], "white"), crit, add, cost,
            ev["hp_after"], ev["max_hp"], gain, realm)

    if k == "spend":
        return "%s %s 战势 -%d → %d" % (
            head, c("·", "gray"), ev["cost"], ev["resource"])

    if k == "p05":
        return "%s %s 守意归元 回复 %d  (%d/%d) 减伤 %d%%" % (
            head, c("✚", "green"), ev["heal"], ev["hp"], ev["max_hp"], ev["dr"])

    if k == "attack":
        combo = "%d/3" % ev["combo"]
        crit = c(" 暴击", "yellow") if ev["crit"] else ""
        gain = ev["gain"]
        ov = ""
        if ev.get("overflow"):
            ov = c(" 溢出%d" % ev["overflow"], "gray")
        return "%s %s %s 普攻%s %s %s%s  (%d/%d)  %s%s" % (
            head, c("»", "cyan"), "破妄", c(combo, "gray"),
            ev["name"], c("-%d" % ev["value"], "white"), crit,
            ev["hp_after"], ev["max_hp"],
            c("战势+%d→%d" % (gain, ev["resource"]), "blue"), ov)

    if k == "hurt":
        crit = c(" 暴击", "yellow") if ev["crit"] else ""
        return "%s %s %s 抓击 破妄 %s%s  (%d/%d)" % (
            head, c("«", "red"), ev["name"],
            c("-%d" % ev["value"], "red"), crit,
            ev["hp_after"], ev["max_hp"])

    if k == "decay":
        return "%s %s 战势流失 %s  (%d→%d)" % (
            head, c("·", "gray"), c("-%d" % ev["loss"], "gray"),
            ev["before"], ev["resource"])

    if k == "realm":
        if ev["state"] == "enter":
            return "%s %s 战势 %d — 进入%s" % (
                head, c("★", "gold"), ev["resource"], c(ev["name"], "gold"))
        return "%s %s 退出%s" % (head, c("·", "gray"), ev["name"])

    if k == "break":
        return "%s %s %s 破韧 %.0f 秒" % (
            head, c("◈", "magenta" if "magenta" in C else "gold"),
            ev["name"], ev["duration"])

    if k == "gap":
        return "%s %s 破隙 +%d 伤害  返还 %d 战势" % (
            head, c("◇", "gold"), ev["bonus"], ev["refund"])

    if k == "spawn":
        return "%s %s %s 出现  (%s)" % (
            head, c("+", "gray"), ev["name"], c("%d" % ev["hp"], "gray"))

    if k == "kill":
        return "%s %s %s 倒下  %s" % (
            head, c("x", "yellow"), ev["name"], c("+%d 经验" % ev["xp"], "green"))

    if k == "death":
        return "%s %s %s 被 %s 打死" % (
            head, c("X", "red"), ev["name"], ev["by"])

    return "%s %s %s" % (head, c("?", "gray"), ev)
