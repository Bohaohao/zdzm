#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M3 入口：自动推图。

    python3 run_campaign.py --seconds 600
    python3 run_campaign.py --mode farm --stage 2-3
    python3 run_campaign.py --seconds 3600 --quiet
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from zdzm.core.rng import Rng
from zdzm.core.state import make_player
from zdzm.core.campaign import Campaign
from zdzm.core.progress import auto_learn
from zdzm.data import classes as C
from zdzm.data import zones as Z
from zdzm.data import monsters as MS

B = {"reset": "\033[0m", "dim": "\033[2m", "bold": "\033[1m",
     "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
     "gold": "\033[38;5;220m", "gray": "\033[90m", "cyan": "\033[36m",
     "blue": "\033[34m"}
COLOR = True


def c(t, k=None):
    if not COLOR or not k:
        return str(t)
    return B.get(k, "") + str(t) + B["reset"]


def main():
    global COLOR
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--mode", default="push", choices=["push", "farm"])
    ap.add_argument("--stage", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    if args.no_color or not sys.stdout.isatty():
        COLOR = False
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    rng = Rng(args.seed)
    p = make_player("C01", args.level)
    auto_learn(p)
    p["char_id"] = "local"

    def say(kind, **kw):
        if args.quiet:
            return
        if kind == "stage_clear":
            st = Z.get(kw["stage"])
            print("%s %s 通关 %s %s%s" % (
                banner_time(cur["c"]), c("─", "gray"), kw["stage"], st["name"],
                c("  (%s)" % kw["mode"], "gray")))
        elif kind == "death":
            print("%s %s 死亡  Lv.%d 回营地重试" % (
                banner_time(cur["c"]), c("X", "red"), kw["level"]))
        elif kind == "levelup":
            print("%s %s 升级 Lv.%d" % (
                banner_time(cur["c"]), c("★", "gold"), kw["level"]))

    def on_kill(mon, gold, settlements):
        if args.quiet:
            return
        loot = ""
        if settlements:
            it = settlements[0]["item"]
            loot = "  " + c("[%s %s]" % (it["quality_name"], it["name"]),
                            "green" if it["quality"] >= 2 else "gray")
        print("%s   %s %s%s%s" % (
            banner_time(cur["c"]), c("%-8s" % mon["name"], "gray"),
            c("+%d xp" % mon.get("xp", 0), "dim"),
            c(" +%dg" % gold, "dim"), loot))

    cur = {"c": None}
    camp = Campaign(p, rng, mode=args.mode, stage=args.stage,
                    log_kill=on_kill, say=say)
    cur["c"] = camp

    print()
    print(c("═══ 造梦终端 · 自动推图 ═══", "bold"))
    print("角色  %s Lv.%d   生命 %d   攻击 %d" % (
        C.CLASSES["C01"]["name"], p["level"], p["max_hp"], p["atk"]))
    print("模式  %s   起点 %s %s" % (
        args.mode, camp.stage, Z.get(camp.stage)["name"]))
    print("时长  %.0f 秒   seed %s" % (args.seconds, rng.seed))
    print(c("─" * 60, "gray"))
    print()

    camp.run(args.seconds)

    # ---------------- 结算 ----------------
    print()
    print(c("─" * 60, "gray"))
    print(c("═ 推图结算 ═", "bold"))
    print()
    print("等级      Lv.%d   经验 %d / %d" % (
        p["level"], p.get("xp", 0), C.xp_to_next(p["level"])))
    print("推进      %d 关   %s" % (
        len(camp.cleared),
        " → ".join(camp.cleared[:3]) + (" ..." if len(camp.cleared) > 3 else "")))
    print("当前      %s %s  %s" % (camp.stage, Z.get(camp.stage)["name"], camp.mode))
    print("死亡      %d 次" % camp.deaths)
    print("掉落      %d 件" % len(camp.loot))
    if camp.loot:
        by_q = {}
        for s in camp.loot:
            q = s["item"]["quality_name"]
            by_q[q] = by_q.get(q, 0) + 1
        print("品质      " + "  ".join("%s %d" % (k, v) for k, v in by_q.items()))
    print("技能      " + " ".join("%s%d" % (k[-3:], v)
                                 for k, v in sorted(p["skills"].items())))
    print("被动      " + (" ".join("%s%d" % (k[-3:], v)
                                 for k, v in sorted(p["passives"].items())) or "无"))
    print("结算信封  %d 条" % len(camp.receipts))
    print()


def banner_time(camp):
    if camp is None or camp.battle is None:
        return c("[    0.0]", "dim")
    return c("[%7.1f]" % camp.battle.tl.now, "dim")


if __name__ == "__main__":
    main()
