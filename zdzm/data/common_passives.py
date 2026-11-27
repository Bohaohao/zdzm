# -*- coding: utf-8 -*-
"""通用被动：五项，所有职业共享的面板属性。

参考《造梦西游2》的通用被动设计（热血/魔泉/狂暴/光之永恒/月之辉煌）：
  - 纯数值，不涉及任何职业专属机制
  - 独立货币驱动（本作复用金币）
  - 5 级封顶，成本线性递增

映射说明：原作的「魔法上限 / 回蓝」在本作无对应物（破妄没有蓝），
硬套会变成职业专属属性，违背「通用」定义，因此替换为攻击 / 防御。
"""

COST = [600, 1400, 2800, 5200, 9000]      # 1→5 级，每级成本
MAX_LEVEL = 5

COMMON = [
    {"key": "hp", "name": "体魄", "desc": "生命上限", "per": 0.04, "unit": "%"},
    {"key": "atk", "name": "锋锐", "desc": "攻击力", "per": 0.04, "unit": "%"},
    {"key": "def", "name": "坚壁", "desc": "防御力", "per": 0.04, "unit": "%"},
    {"key": "crit", "name": "锐眼", "desc": "暴击率", "per": 2.0, "unit": " 点"},
    {"key": "cdmg", "name": "破军", "desc": "暴击伤害", "per": 0.10, "unit": "%"},
]

BY_KEY = {c["key"]: c for c in COMMON}


def all_of():
    return COMMON


def level_of(p, key):
    return (p.get("common") or {}).get(key, 0)


def cost_of(level):
    """升到 level+1 级的价格；已满返回 None。"""
    if level >= MAX_LEVEL:
        return None
    return COST[level]


def total_cost(level):
    return sum(COST[:level])


def value_of(p, key):
    """当前加成值（百分比或点）。"""
    c = BY_KEY[key]
    return level_of(p, key) * c["per"]


def multipliers(p):
    """给 recalc 用的倍率/加点。"""
    lv = p.get("common") or {}
    return {
        "hp": 1 + lv.get("hp", 0) * 0.04,
        "atk": 1 + lv.get("atk", 0) * 0.04,
        "def": 1 + lv.get("def", 0) * 0.04,
        "crit": lv.get("crit", 0) * 2.0,
        "cdmg": lv.get("cdmg", 0) * 0.10,
    }


def upgrade(p, key):
    """花金币升一级。返回 (成功, 花费, 新等级)。"""
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
