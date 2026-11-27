# -*- coding: utf-8 -*-
"""装备穿戴、战力评分、强化。

槽位 9 个（戒指两个），装备方向见 DESIGN.md §7.1。
战力公式与终端版同构：输出 65% + 有效生命 35%。
"""
import uuid

from zdzm.core.state import recalc

# 玩家可用的槽位顺序（展示用）
SLOT_ORDER = ["weapon", "helm", "body", "bracer", "belt", "boots", "amulet", "ring1", "ring2"]
SLOT_NAMES = {
    "weapon": "武器", "helm": "头盔", "body": "护甲", "bracer": "护腕",
    "belt": "腰带", "boots": "靴", "amulet": "项链",
    "ring1": "戒指1", "ring2": "戒指2",
}
QUALITY_NAMES = ["普通", "精良", "稀有", "史诗", "传说"]


def power(p):
    """角色综合战力。"""
    dps = p["atk"] * (1 + p["crit"] / 100.0 * 0.75)
    ehp = p["max_hp"] * (1 + p["def"] / 600.0)
    return (max(1.0, dps) ** 0.65) * (max(1.0, ehp) ** 0.35) * 10.0


def targets_for(p, item):
    """这件装备能进哪些槽。"""
    slot = item["slot"]
    if slot == "ring":
        return ["ring1", "ring2"]
    return [slot]


def gain_on(p, item, slot):
    """换上后战力变化。"""
    cur = p["equipped"].get(slot)
    base = power(p)
    p["equipped"][slot] = item
    recalc(p)
    new = power(p)
    p["equipped"][slot] = cur
    recalc(p)
    return new - base


def best_slot(p, item):
    """返回 (槽位, 提升)。"""
    best = (None, -1e9)
    for s in targets_for(p, item):
        g = gain_on(p, item, s)
        if g > best[1]:
            best = (s, g)
    return best


def equip(p, item, slot=None):
    """强制穿到指定槽（没指定就选提升最大的）。返回被换下的装备或 None。"""
    if slot is None:
        slot, _ = best_slot(p, item)
    if slot is None:
        return None
    old = p["equipped"].get(slot)
    p["equipped"][slot] = item
    recalc(p)
    return old


def try_equip(p, item):
    """捡到装备时的自动判断：有提升就穿。返回 (是否穿上, 换下的)。"""
    slot, g = best_slot(p, item)
    if slot is None:
        return False, None
    if g > 0.01:
        old = equip(p, item, slot)
        return True, old
    return False, None


def sell_price(item):
    q = item["quality"]
    return int((6 + item["ilvl"] * 2) * (1 + q * 1.2))


def junk_score(item):
    return item["ilvl"] * 2 + item["quality"] * 10 + (item.get("plus", 0)) * 3


def equip_line(item):
    v = item["value"] * (1 + item.get("plus", 0) * 0.04)
    unit = {"atk": "攻", "def": "防", "hp": "血", "crit": "暴击"}[item["main"]]
    plus = "+%d " % item["plus"] if item.get("plus") else ""
    return "%s%s %s %s%d" % (
        plus, item["name"], QUALITY_NAMES[item["quality"]], unit, round(v))


# ---------------------------------------------------------------- 强化
STRENGTHEN_MAX = 15
STRENGTHEN_STEP = 0.04


def strengthen_cost(item):
    return int((30 + item["ilvl"] * 12) * (1 + item.get("plus", 0) * 0.35))


def can_strengthen(p, item):
    if item.get("plus", 0) >= STRENGTHEN_MAX:
        return False
    return p.get("gold", 0) >= strengthen_cost(item)


def strengthen(p, item):
    """安全强化：不碎、不降级（策划案约束）。"""
    if item.get("plus", 0) >= STRENGTHEN_MAX:
        return False
    cost = strengthen_cost(item)
    if p.get("gold", 0) < cost:
        return False
    p["gold"] -= cost
    item["plus"] = item.get("plus", 0) + 1
    return True


def auto_strengthen(p, reserve_ratio=0.25):
    """把当前装备平均强化，留一部分金币。返回强化次数。"""
    n = 0
    for _ in range(60):
        budget = p.get("gold", 0) * (1 - reserve_ratio)
        cand = None
        low = 99
        for it in p["equipped"].values():
            if not it:
                continue
            pl = it.get("plus", 0)
            if pl < low and pl < STRENGTHEN_MAX and strengthen_cost(it) <= budget:
                low = pl
                cand = it
        if cand is None:
            break
        if not strengthen(p, cand):
            break
        recalc(p)
        n += 1
    return n


# ---------------------------------------------------------------- 进阶
# 策划案约束（item-growth.json）：
#   必须原子保留 source_instance_id、强化状态、新实例 lineage
MAT_ADVANCE = "MAT_ADVANCE_HG"
ADVANCE_MATERIALS = 3


def advance_cost(item):
    return int(200 * (1 + item["ilvl"] * 0.30) * (1 + item["quality"] * 0.50))


def can_advance(p, item):
    if item["quality"] >= 4:
        return False
    if p.get("materials", {}).get(MAT_ADVANCE, 0) < ADVANCE_MATERIALS:
        return False
    return p.get("gold", 0) >= advance_cost(item)


def advance(p, item):
    """安全进阶：不碎、不降级，生成 lineage。返回新实例或 None。"""
    if not can_advance(p, item):
        return None
    cost = advance_cost(item)
    p["materials"][MAT_ADVANCE] -= ADVANCE_MATERIALS
    p["gold"] -= cost

    new = dict(item)
    new["instance_id"] = "itm_" + uuid.uuid4().hex[:8]
    new["ilvl"] = item["ilvl"] + 4
    new["quality"] = min(4, item["quality"] + 1)
    new["quality_name"] = QUALITY_NAMES[new["quality"]]
    new["value"] = round(item["value"] * 1.35, 1)
    # lineage：旧实例、旧强化、材料消耗
    new["source_instance_id"] = item["instance_id"]
    new["previous_strengthen"] = item.get("plus", 0)
    new["generation"] = item.get("generation", 1) + 1
    new["consumed_materials"] = [{"key": MAT_ADVANCE, "count": ADVANCE_MATERIALS}]
    new["superseded_by"] = None
    item["superseded_by"] = new["instance_id"]
    return new


def auto_advance(p, min_quality=2):
    """把身上低于阈值的装备自动进阶（材料够就进）。返回次数。"""
    n = 0
    for _ in range(12):
        cand = None
        for it in p["equipped"].values():
            if not it:
                continue
            if it["quality"] < min_quality and can_advance(p, it):
                cand = it
                break
        if cand is None:
            break
        slot = None
        for s2, it2 in p["equipped"].items():
            if it2 is cand:
                slot = s2
                break
        new = advance(p, cand)
        if new is None:
            break
        p["equipped"][slot] = new
        recalc(p)
        n += 1
    return n
