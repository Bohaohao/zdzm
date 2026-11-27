# -*- coding: utf-8 -*-
"""技能解锁、加点与装配。

口径（2026-11-27 作者确认）：
  - 到达等级解锁技能，**解锁不消耗技能点**
  - 1 级随解锁免费获得
  - 2-5 级由玩家手动加点，每级消耗 1 点
  - 技能点：Lv2~Lv60 每级 +1
  - 玩家最多装配 5 个主动；被动不需要装配，全部生效
  - 新解锁的主动在槽位有空时自动装配
"""
from zdzm.data.skills import SKILLS, PASSIVES

UPGRADE_PRIORITY = [
    "C01_A02", "C01_A06", "C01_A05", "C01_A01",
    "C01_A08", "C01_A03", "C01_A04", "C01_A07",
]
PASSIVE_PRIORITY = [
    "C01_P01", "C01_P02", "C01_P03", "C01_P04",
    "C01_P05", "C01_P06", "C01_P07", "C01_P08",
]


def points_for_level(level):
    return max(0, level - 1)


def _spent(p):
    """已花点数 = 所有技能等级之和 - A01 首级（唯一免费项）。"""
    n = sum(p["skills"].values()) + sum(p["passives"].values())
    if "C01_A01" in p["skills"]:
        n -= 1
    return n


def can_learn_active(p, key):
    if key in p["skills"]:
        return False
    sk = SKILLS[key]
    if p["level"] < sk["unlock"]:
        return False
    pre = sk.get("prereq")
    if pre and p["skills"].get(pre[0], 0) < pre[1]:
        return False
    return True


def can_learn_passive(p, key):
    if key in p["passives"]:
        return False
    ps = PASSIVES[key]
    if p["level"] < ps["unlock"]:
        return False
    pre = ps.get("prereq")
    if pre and p["skills"].get(pre[0], 0) < pre[1]:
        return False
    return True


def learn_active(p, key):
    """学习主动 0→1 级，消耗 1 点。学完自动进空槽。"""
    if not can_learn_active(p, key):
        return False
    if p["skill_points"] <= 0:
        return False
    p["skills"][key] = 1
    p["skill_points"] -= 1
    lo = p.setdefault("loadout", [])
    if not p.get("loadout_locked") and len(lo) < 5:
        lo.append(key)
    return True


def learn_passive(p, key):
    """学习被动 0→1 级，消耗 1 点。被动不用装配。"""
    if not can_learn_passive(p, key):
        return False
    if p["skill_points"] <= 0:
        return False
    p["passives"][key] = 1
    p["skill_points"] -= 1
    return True


def upgrade(p, key):
    """升一级：消耗 1 点。"""
    if p["skill_points"] <= 0:
        return False
    if key in p["skills"]:
        if p["skills"][key] >= 5:
            return False
        p["skills"][key] += 1
    elif key in p["passives"]:
        if p["passives"][key] >= 5:
            return False
        p["passives"][key] += 1
    else:
        return False
    p["skill_points"] -= 1
    return True


def downgrade(p, key):
    """降一级并返还 1 点；降到 0 等于遗忘。

    只有当「已学技能的前置要求」会被破坏时才拒绝。
    """
    cur = p["skills"].get(key) or p["passives"].get(key) or 0
    if cur <= 0:
        return False

    # 有已学技能依赖这个技能的等级吗？
    for k, v in list(p["skills"].items()) + list(p["passives"].items()):
        if v <= 0 or k == key:
            continue
        d = SKILLS.get(k) or PASSIVES.get(k) or {}
        pre = d.get("prereq")
        if pre and pre[0] == key and pre[1] > cur - 1:
            return False

    if cur == 1:
        # 遗忘
        if key in p["skills"]:
            del p["skills"][key]
        else:
            del p["passives"][key]
        lo = p.get("loadout") or []
        if key in lo:
            lo.remove(key)
    else:
        if key in p["skills"]:
            p["skills"][key] -= 1
        else:
            p["passives"][key] -= 1

    p["skill_points"] += 1
    return True


def auto_learn(p):
    """只做两件事：Lv1 初始技能自动学、刷新技能点余额。

    其余技能「达到条件即可学习」，但要玩家自己 learn —— 不自动学。
    """
    p["skill_points"] = points_for_level(p["level"]) - _spent(p)

    # 策划案：Lv1 免费主动自动学习并自动装备
    if "C01_A01" not in p["skills"]:
        p["skills"]["C01_A01"] = 1

    # 装配兜底：只保证已学主动在槽内，不替玩家学新技能
    if not p.get("loadout_locked"):
        lo = []
        for key in UPGRADE_PRIORITY:
            if len(lo) >= 5:
                break
            if key in p["skills"]:
                lo.append(key)
        p["loadout"] = lo


def upgrade_skill(p, key, target):
    """玩家手动把某个技能点到目标等级。返回实际升了几级。"""
    n = 0
    for _ in range(max(0, target)):
        if p["skill_points"] <= 0:
            break
        cur = p["skills"].get(key) or p["passives"].get(key) or 0
        if cur <= 0 or cur >= 5:
            break
        if not upgrade(p, key):
            break
        n += 1
    return n


def auto_spend(p):
    """一键推荐：学 → 升核心解锁进阶 → 再学 → 再升。"""
    for _ in range(4):
        moved = False
        for key in UPGRADE_PRIORITY:
            if p["skill_points"] <= 0:
                break
            if key not in p["skills"] and learn_active(p, key):
                moved = True
        for key in PASSIVE_PRIORITY:
            if p["skill_points"] <= 0:
                break
            if key not in p["passives"] and learn_passive(p, key):
                moved = True
        if _upgrade_pass(p):
            moved = True
        if not moved:
            break
    return p


def _upgrade_pass(p):
    moved = False
    for key in ("C01_A03", "C01_A04", "C01_A05", "C01_A06", "C01_A07", "C01_A08"):
        while p["skill_points"] > 0 and 0 < p["skills"].get(key, 0) < 3:
            if not upgrade(p, key):
                break
            moved = True
    for key in ("C01_A02", "C01_A06", "C01_A05"):
        while p["skill_points"] > 0 and p["skills"].get(key, 0) < 5:
            if not upgrade(p, key):
                break
            moved = True
    for key in PASSIVE_PRIORITY:
        while p["skill_points"] > 0 and p["passives"].get(key, 0) < 5:
            if not upgrade(p, key):
                break
            moved = True
    return moved


def set_loadout(p, keys):
    """设置 5 个主动槽。只接受已解锁主动。设置后不再自动调整。"""
    keys = [k for k in keys if k in p["skills"]][:5]
    p["loadout"] = keys
    p["loadout_locked"] = True
    return keys
