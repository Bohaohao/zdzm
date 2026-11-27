#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M1 冒烟入口：验证时间轴、事件流、破妄战势循环。

    python3 app.py                 # 跑 60 秒
    python3 app.py --seconds 30
    python3 app.py --seed 7
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from zdzm.core.rng import Rng
from zdzm.core.state import make_player, make_monster
from zdzm.core.combat import Battle
from zdzm.core.ai import Ai
from zdzm.core.progress import auto_learn
from zdzm.data import classes as C
from zdzm.data import monsters as M
import ui.log as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--monster", default="shan_hou")
    ap.add_argument("--level", type=int, default=1)
    args = ap.parse_args()

    if args.no_color or not sys.stdout.isatty():
        L.COLOR = False
    L.enable_ansi()

    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    rng = Rng(args.seed)
    player = make_player("C01", args.level)
    auto_learn(player)
    cls = C.CLASSES["C01"]
    mon_def = M.MONSTERS[args.monster]

    print()
    print(L.c("═══ 造梦终端 · 战斗演示 ═══", "bold"))
    print("角色  %s Lv.%d   生命 %d   攻击 %d   防御 %d   攻速 %.2f/s   暴击 %d%%" % (
        cls["name"], player["level"], player["max_hp"], player["atk"],
        player["def"], cls["aps"], cls["crit"]))
    sk = ", ".join("%s%d" % (k[-3:], v) for k, v in sorted(player["skills"].items()))
    ps = ", ".join("%s%d" % (k[-3:], v) for k, v in sorted(player["passives"].items()))
    print("技能  %s" % (sk or "无"))
    print("被动  %s   剩余技能点 %d" % (ps or "无", player["skill_points"]))
    print("对手  %s   生命 %d   攻击 %d   攻速 %.2f/s" % (
        mon_def["name"], mon_def["hp"], mon_def["atk"], mon_def["aps"]))
    print("时长  %.1f 秒   seed %s" % (args.seconds, rng.seed))
    print(L.c("─" * 62, "gray"))
    print()

    battle = Battle(
        player,
        lambda: make_monster(args.monster),
        rng,
        ai=Ai(),
    )
    events = battle.run(args.seconds)

    for ev in events:
        print(L.render(ev))

    # ---------------- 统计 ----------------
    atk_evs = [e for e in events if e["kind"] in ("attack", "skill")]
    hurt_evs = [e for e in events if e["kind"] == "hurt"]
    res_points = [e["resource"] for e in atk_evs] + [e["resource"] for e in events if e["kind"] == "decay"]
    realms = [e for e in events if e["kind"] == "realm" and e["state"] == "enter"]
    dmg_total = sum(e["value"] for e in atk_evs)
    hurt_total = sum(e["value"] for e in hurt_evs)
    crits = sum(1 for e in atk_evs if e.get("crit") or e.get("crits"))
    duration = max(0.001, args.seconds)

    print()
    print(L.c("─" * 62, "gray"))
    print(L.c("═ 统计 %.1f 秒 ═" % args.seconds, "bold"))
    print()
    print("输出伤害   %-8s 命中 %-4d 暴击 %-3d DPS %.1f" % (
        L.c("%d" % dmg_total, "white"), len(atk_evs), crits, dmg_total / duration))
    print("击杀       %d 只" % battle.kills)
    print("承受伤害   %-8s 剩余生命 %s/%s %s" % (
        hurt_total, player["hp"], player["max_hp"],
        L.bar(player["hp"], player["max_hp"], 14,
              "red" if player["hp"] / player["max_hp"] < 0.3 else "green")))
    print("战势       峰值 %-4s 低谷 %-4s 收尾 %-4s 上限 %d" % (
        max(res_points) if res_points else 0,
        min(res_points) if res_points else 0,
        player["resource"], cls["resource_max"]))
    print("洞明       触发 %d 次（阈值 %d）" % (len(realms), cls["realm_threshold"]))
    print()

    # ---------------- 断言 ----------------
    ok = True
    if args.monster != "dummy" and battle.kills < 3:
        print(L.c("! 击杀少于 3 只，单场时长可能过长", "yellow"))
        ok = False
    if not realms:
        print(L.c("! 60 秒内没触发洞明，战势循环可能有问题", "yellow"))
        ok = False
    if player["hp"] <= 0:
        print(L.c("! 玩家死亡", "red"))
        ok = False
    print(L.c("战斗 " + ("PASS" if ok else "WARN"), "green" if ok else "yellow"))
    print()


if __name__ == "__main__":
    main()
