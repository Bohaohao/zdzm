# -*- coding: utf-8 -*-
"""
掉落与结算。

结构来自策划案，数值 provisional：
  profile 划分与保底池  —— tables/drop-and-pity.json
  四字段分离            —— item-growth.json proposal_constraints
  12 字段结算信封        —— drop-and-pity.json settlement_receipt
"""

# ---------------------------------------------------------------- profile 表
# tier 决定品质分布；drop_pct / rare_pct 是我填的 provisional
PROFILES = {
    "HG_DROP_MOUNTAIN_COMMON":    {"tier": "COMMON", "drop": 15, "rare": 1},
    "HG_DROP_MOUNTAIN_ELITE":     {"tier": "ELITE",  "drop": 45, "rare": 8},
    "HG_DROP_MOUNTAIN_MAJOR":     {"tier": "MAJOR",  "drop": 70, "rare": 20},
    "HG_DROP_WATERFALL_COMMON":   {"tier": "COMMON", "drop": 15, "rare": 1},
    "HG_DROP_WATERFALL_ELITE":    {"tier": "ELITE",  "drop": 45, "rare": 8},
    "HG_DROP_MACAQUE_PUBLIC":     {"tier": "PUBLIC", "drop": 100, "rare": 100, "count": 2},
    "HG_DROP_PEACH_COMMON":       {"tier": "COMMON", "drop": 15, "rare": 1},
    "HG_DROP_PEACH_MAJOR":        {"tier": "MAJOR",  "drop": 70, "rare": 20},
    "HG_DROP_CAVE_COMMON":        {"tier": "COMMON", "drop": 15, "rare": 1},
    "HG_DROP_CAVE_MAJOR":         {"tier": "MAJOR",  "drop": 70, "rare": 20},
    "HG_DROP_SEVENSTAR_COMMON":   {"tier": "COMMON", "drop": 15, "rare": 1},
    "HG_DROP_SEVENSTAR_ELITE":    {"tier": "ELITE",  "drop": 45, "rare": 8},
    "HG_DROP_SEVENSTAR_MAJOR":    {"tier": "MAJOR",  "drop": 70, "rare": 20},
    "HG_DROP_PENG_OPTIONAL":      {"tier": "PUBLIC", "drop": 100, "rare": 100, "count": 2},
    "HG_DROP_EASTSEA_COMMON":     {"tier": "COMMON", "drop": 15, "rare": 1},
    "HG_DROP_EASTSEA_ELITE":      {"tier": "ELITE",  "drop": 45, "rare": 8},
    "HG_DROP_JIAO_PUBLIC":        {"tier": "PUBLIC", "drop": 100, "rare": 100, "count": 2},
    "HG_DROP_SHARK_PUBLIC":       {"tier": "PUBLIC", "drop": 100, "rare": 100, "count": 2},
    "HG_DROP_DRAGON_OLD":         {"tier": "DUNGEON", "drop": 100, "rare": 100, "count": 3},
    "HG_DROP_DRAGON_REVERSE":     {"tier": "DUNGEON", "drop": 100, "rare": 100, "count": 3},
    "HG_DROP_OX_RAID":            {"tier": "RAID",   "drop": 100, "rare": 100, "count": 3},
}

QUALITY_NAMES = ["普通", "精良", "稀有", "史诗", "传说"]

# 各档次的品质权重（provisional）
QUALITY_WEIGHTS = {
    "COMMON":  [45, 33, 16, 5, 1],
    "ELITE":   [25, 38, 25, 10, 2],
    "MAJOR":   [15, 35, 32, 15, 3],
    "PUBLIC":  [10, 32, 35, 18, 5],
    "DUNGEON": [5, 25, 38, 25, 7],
    "RAID":    [5, 25, 38, 25, 7],
}

# 保底池：显式登记，禁止静默共用（策划案约束）
PITY = {
    "PITY_HG_COMMON": {"pool": "COMMON", "need": 12, "min_quality": 0},
    "PITY_HG_ELITE":  {"pool": "ELITE",  "need": 4,  "min_quality": 1},
    "PITY_HG_MAJOR":  {"pool": "MAJOR",  "need": 2,  "min_quality": 2},
}

# 部位与基础属性（provisional）
SLOTS = {
    "weapon":   {"name": "武器", "main": "atk", "base": 26, "scale": 0.075},
    "helm":     {"name": "头盔", "main": "def", "base": 12, "scale": 0.070},
    "body":     {"name": "护甲", "main": "def", "base": 20, "scale": 0.070},
    "bracer":   {"name": "护腕", "main": "def", "base": 8,  "scale": 0.060},
    "belt":     {"name": "腰带", "main": "def", "base": 7,  "scale": 0.060},
    "boots":    {"name": "靴",   "main": "def", "base": 9,  "scale": 0.060},
    "amulet":   {"name": "项链", "main": "hp",  "base": 40, "scale": 0.080},
    "ring":     {"name": "戒指", "main": "crit", "base": 2, "scale": 0.030},
}

PREFIX = ["锋锐的", "厚重的", "灵动的", "凶戾的", "沉稳的", "残缺的"]
WEAPON_NAME = "长兵"


def quality_index(weights, rng):
    return rng.weighted([(i, w) for i, w in enumerate(weights)])


def make_item(profile_key, level, rng, min_quality=0):
    pf = PROFILES[profile_key]
    qi = quality_index(QUALITY_WEIGHTS[pf["tier"]], rng)
    if qi < min_quality:
        qi = min_quality
    slot = rng.choice(list(SLOTS.keys()))
    sd = SLOTS[slot]
    k = max(0, level - 1)
    value = sd["base"] * (1 + sd["scale"] * k) * (1 + qi * 0.22)
    name = PREFIX[rng.randint(0, len(PREFIX) - 1)] + (
        WEAPON_NAME if slot == "weapon" else sd["name"])
    return {
        "instance_id": "itm_%06d" % rng.randint(1, 999999),
        "name": name,
        "slot": slot,
        "slot_name": sd["name"],
        "quality": qi,
        "quality_name": QUALITY_NAMES[qi],
        "ilvl": level,
        "main": sd["main"],
        "value": int(round(value, 1)),
    }


def roll(state, profile_key, level, rng):
    """返回 (settlements, receipts)。

    settlement 四字段：quality / rare_eligibility / pity_progress / ownership
    receipt 12 字段：结算信封，单人版也生成，为联机预留
    """
    pf = PROFILES.get(profile_key)
    if not pf:
        return [], []
    tier = pf["tier"]
    pool_key = "PITY_HG_" + tier if ("PITY_HG_" + tier) in PITY else None

    settlements, receipts = [], []

    # 1) 保底判定
    forced = False
    if pool_key:
        meta = PITY[pool_key]
        prog = state.setdefault("pity", {}).setdefault(pool_key, 0)
        prog += 1
        state["pity"][pool_key] = prog
        if prog >= meta["need"]:
            forced = True
            state["pity"][pool_key] = 0

    # 2) 概率判定
    hit = rng.chance(pf["drop"]) or forced
    count = pf.get("count", 1) if hit else 0
    if forced and count == 0:
        count = 1

    min_q = PITY[pool_key]["min_quality"] if (forced and pool_key) else 0

    for i in range(count):
        item = make_item(profile_key, level, rng, min_q)
        rare_ok = rng.chance(pf["rare"])
        settlements.append({
            "quality": item["quality"],
            "rare_eligibility": {"eligible": rare_ok, "reason": profile_key},
            "pity_progress": {
                "pool": pool_key,
                "value": state["pity"].get(pool_key, 0) if pool_key else 0,
                "forced": forced,
            },
            "ownership": {"scope": "character", "owner_id": state.get("char_id", "local")},
            "item": item,
        })
        receipts.append({
            "source_profile": profile_key,
            "encounter_instance_id": state.get("encounter_id", "enc_local"),
            "actor_id": state.get("char_id", "local"),
            "qualification_snapshot_id": "qs_local",
            "drop_roll_id": "roll_%s" % item["instance_id"],
            "event_id": "evt_%s" % item["instance_id"],
            "resource_table_version": "v1",
            "schema_version": 1,
            "owner_scope": "character",
            "reward_slot_key": "slot_%d" % i,
            "pity_pool_key": pool_key,
            "receipt_id": "rc_%s" % item["instance_id"],
        })
    return settlements, receipts
