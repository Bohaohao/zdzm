# -*- coding: utf-8 -*-
"""通用被动：五项，覆盖所有职业都会用到的抽象属性。

参考《造梦西游2》：热血(生命) / 魔泉(魔法上限) / 狂暴(暴击) / 光之永恒(回血) / 月之辉煌(回蓝)

「通用」的含义不是「所有职业属性相同」，而是——
抽象层是【资源】【回复】这类概念，每个职业用自己的一套兑现：
    有蓝职业  → 法力上限 / 每秒回蓝
    战势职业  → 战势上限 / 生势效率（洞明阈值同步提高，保持难度）
    生命回复  → 不分职业，战斗内定期回血

因此不能因为「当前只有破妄一个职业，它没有蓝」就把资源类被动砍掉。

成本：金币，5 级封顶，线性递增。
"""

COST = [600, 1400, 2800, 5200, 9000]
MAX_LEVEL = 5

COMMON = [
    {"key": "hp",      "name": "体魄", "desc": "生命上限", "per": 0.04,  "pct": True,  "unit": "%"},
    {"key": "res_max", "name": "灵泉", "desc": "资源上限", "per": 0.05,  "pct": True,  "unit": "%"},
    {"key": "crit",    "name": "锐眼", "desc": "暴击率",   "per": 2.0,   "pct": False, "unit": " 点"},
    {"key": "heal",    "name": "回春", "desc": "战斗回血", "per": 0.004, "pct": True,  "unit": "%/5秒"},
    {"key": "res_gen", "name": "归元", "desc": "资源获取", "per": 0.06,  "pct": True,  "unit": "%"},
]


def label(c, lv):
    """把等级换算成可读的加成文本。"""
    v = lv * c["per"]
    if c.get("pct"):
        num = round(v * 100, 1)
        num = int(num) if num == int(num) else num
        return "+%s%s" % (num, c["unit"])
    return "+%s%s" % (round(v, 1), c["unit"])

BY_KEY = {c["key"]: c for c in COMMON}


def all_of():
    return COMMON


def level_of(p, key):
    return (p.get("common") or {}).get(key, 0)


def cost_of(level):
    if level >= MAX_LEVEL:
        return None
    return COST[level]


def total_cost(level):
    return sum(COST[:level])


def multipliers(p):
    lv = p.get("common") or {}
    return {
        "hp": 1 + lv.get("hp", 0) * 0.04,
        "res_max": 1 + lv.get("res_max", 0) * 0.05,
        "crit": lv.get("crit", 0) * 2.0,
        "heal": lv.get("heal", 0) * 0.004,       # 每 5 秒回的最大生命百分比
        "res_gen": 1 + lv.get("res_gen", 0) * 0.06,
    }


def upgrade(p, key):
    lv = level_of(p, key)
    if lv >= MAX_LEVEL:
        return False, 0, lv
    price = COST[lv]
    if p.get("gold", 0) < price:
        return False, price, lv
    p["gold"] -= price
    p.setdefault("common", {})
    p["common"][key] = lv + 1
    return True, price, lv + 1
