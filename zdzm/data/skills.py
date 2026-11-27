# -*- coding: utf-8 -*-
"""
破妄 8 个主动 + 8 个被动。

数值来源：docs/归档/职业设计/02-破妄法门资源循环与完整技能组.md §6 §7
伤害口径（同文档 §2.2）：
    技能基础伤害 = 最终物理攻击 × 技能攻击系数 × 目标防御结算 × 修正

provisional（策划案未锁定）：
    gcd —— 策划案无全局冷却概念，M2 暂不实现
    目标防御结算公式 —— 沿用 M1 的 减法 × 0.4
"""

# ---------------------------------------------------------------- 主动技能
# mult / cd / gain 均为 1-5 级数组，索引 = 技能等级 - 1
SKILLS = {
    "C01_A01": {
        "key": "C01_A01", "poise": 1.0, "name": "开锋式", "kind": "attack",
        "role": "基础生势", "unlock": 1, "prereq": None,
        "cast": 0.15, "cost": 0, "hits": 1,
        "mult": [0.75, 0.85, 0.95, 1.05, 1.20],
        "cd": [4.2, 4.2, 4.0, 3.8, 3.6],
        "gain": [10, 10, 12, 12, 12],
        "note": "5级：释放不打断普攻段数",
    },
    "C01_A02": {
        "key": "C01_A02", "poise": 2.0, "name": "贯心式", "kind": "attack",
        "role": "基础耗势", "unlock": 3, "prereq": None,
        "cast": 0.30, "cost": 30, "hits": 1,
        "mult": [1.50, 1.70, 1.90, 2.15, 2.45],
        "cd": [7.0, 7.0, 7.0, 6.5, 6.0],
        "gain": [0, 0, 0, 0, 0],
        # 洞明追加：主击之外的一次额外系数
        "realm_add": [0.50, 0.55, 0.60, 0.70, 0.80],
        "note": "洞明时追加风压伤害",
    },
    "C01_A03": {
        "key": "C01_A03", "poise": 0.5, "name": "叠锋三破", "kind": "attack",
        "role": "断岳·生势", "unlock": 8, "prereq": None,
        "cast": 0.80, "cost": 0, "hits": 3,
        "mult": [0.45, 0.50, 0.55, 0.60, 0.70],
        "cd": [9.5, 9.5, 9.0, 8.5, 8.0],
        "gain": [5, 5, 5, 5, 5],          # 每击 +5
        "gain_bonus": [0, 0, 3, 3, 3],    # 三击同目标额外 +3
        "note": "三击同中一个目标时额外生势",
    },
    "C01_A04": {
        "key": "C01_A04", "poise": 0.6, "name": "踏虚行", "kind": "attack",
        "role": "踏虚·生势位移", "unlock": 8, "prereq": None,
        "cast": 0.05, "cost": 0, "hits": 1,
        "mult": [0.80, 0.90, 1.00, 1.10, 1.25],
        "cd": [10.0, 10.0, 9.5, 9.0, 10.0],
        "gain": [12, 12, 12, 12, 12],
        "self_dr": 0.40, "dr_dur": 0.25,  # 位移期间减伤 40%
        "note": "瞬发，释放后获得短暂减伤",
    },
    "C01_A05": {
        "key": "C01_A05", "poise": 1.5, "name": "照妄横扫", "kind": "attack",
        "role": "照真·生势范围", "unlock": 8, "prereq": None,
        "cast": 0.25, "cost": 0, "hits": 1,
        "mult": [1.00, 1.15, 1.30, 1.45, 1.65],
        "cd": [11.0, 11.0, 10.5, 10.0, 9.5],
        "gain": [10, 10, 12, 12, 12],
        # 显妄（简化：只做物防降低，不做团队共享）
        "debuff_def": [5, 5, 5, 6, 6],
        "debuff_dur": [5, 5, 6, 7, 8],
        "note": "命中后施加显妄",
    },
    "C01_A06": {
        "key": "C01_A06", "poise": 3.0, "name": "断岳裁", "kind": "attack",
        "role": "断岳·耗势终结", "unlock": 20, "prereq": ("C01_A03", 3),
        "cast": 0.55, "cost": 50, "hits": 1,
        "mult": [3.00, 3.35, 3.70, 4.10, 4.60],
        "cd": [16.0, 16.0, 15.5, 15.0, 14.0],
        "gain": [0, 0, 0, 0, 0],
        "realm_add": [0.25, 0.25, 0.30, 0.35, 0.40],   # 洞明二斩
        "note": "洞明时追加二斩",
    },
    "C01_A07": {
        "key": "C01_A07", "poise": 0.8, "name": "回锋照影", "kind": "attack",
        "role": "踏虚·耗势减伤", "unlock": 20, "prereq": ("C01_A04", 3),
        "cast": 0.0, "cost": 25, "hits": 1,
        "mult": [0.95, 1.10, 1.25, 1.40, 1.60],
        "cd": [13.0, 13.0, 12.5, 12.0, 11.0],
        "gain": [0, 0, 0, 0, 0],
        "self_dr": 0.35, "dr_dur": 1.2,
        "note": "释放后获得减伤窗口",
    },
    "C01_A08": {
        "key": "C01_A08", "poise": 2.5, "name": "定真贯阵", "kind": "attack",
        "role": "照真·耗势控制", "unlock": 20, "prereq": ("C01_A05", 3),
        "cast": 0.40, "cost": 40, "hits": 1,
        "mult": [2.20, 2.45, 2.70, 3.00, 3.40],
        "cd": [15.0, 15.0, 14.5, 14.0, 13.0],
        "gain": [0, 0, 0, 0, 0],
        "realm_add": [0.40, 0.45, 0.50, 0.55, 0.70],   # 显妄目标追加
        "note": "高倍率终结技，命中后施加显妄",
    },
}

# ---------------------------------------------------------------- 学习型被动
PASSIVES = {
    "C01_P01": {
        "key": "C01_P01", "name": "势行不滞", "type": "common",
        "unlock": 10, "prereq": None,
        # 耗势技能有效命中后，4 秒内下一个生势技能额外获得
        "extra_gain": [2, 3, 4, 5, 7],
        "window": 4.0,
        "mastery": "战势开始衰减的等待时间由 4 秒提高到 6 秒",
    },
    "C01_P02": {
        "key": "C01_P02", "name": "锋随势涨", "type": "断岳",
        "unlock": 15, "prereq": ("C01_A03", 3),
        "dmg_mid": [2, 3, 4, 5, 6],       # 战势 40-79
        "dmg_realm": [4, 6, 8, 10, 12],   # 洞明
        "mastery_poise": 0.5,             # 5级：洞明耗势额外破韧
        "mastery": "洞明耗势技能额外 0.5 破韧",
        "m2": True,
    },
    "C01_P03": {
        "key": "C01_P03", "name": "踏虚生风", "type": "踏虚",
        "unlock": 15, "prereq": ("C01_A04", 3),
        # 终端改造：原为"位移后"，改为"A04/A07 释放后"
        "haste": [4, 6, 8, 10, 12],
        "window": 3.0,
        "mastery_gain": 5,
        "deviation": "原为位移后加速，终端无位移，改为技能释放后",
        "mastery": "窗口内第一套普攻额外 5 战势",
        "m2": True,
    },
    "C01_P04": {
        "key": "C01_P04", "name": "妄痕可见", "type": "照真",
        "unlock": 15, "prereq": ("C01_A05", 3),
        "break_bonus": [8, 10, 12, 14, 16],
        "mastery_extend": 2.0,
        "mastery": "显妄期间首次破韧延长显妄 2 秒",
        "m2": True,
    },
    "C01_P05": {
        "key": "C01_P05", "name": "守意归元", "type": "common",
        "unlock": 25, "prereq": None,
        # 每累计实际消耗 50 战势触发
        "cost_threshold": 50,
        "heal_pct": [0.006, 0.008, 0.010, 0.012, 0.015],
        "dr": [4, 5, 6, 7, 8],
        "dr_dur": 3.0,
        "icd": 8.0,
        "mastery": "生命低于 35% 时治疗提高至 3%，每 30 秒至多一次",
    },
    "C01_P06": {
        "key": "C01_P06", "name": "破隙连裁", "type": "断岳",
        "unlock": 30, "prereq": ("C01_A06", 3),
        "dmg": [6, 8, 10, 12, 15],
        "refund": [2, 3, 4, 5, 6],
        "window": 6.0,
        "mastery_cd": 1.5,
        "mastery": "消耗破隙时断岳裁冷却 -1.5 秒",
        "m2": True,
    },
    "C01_P07": {
        "key": "C01_P07", "name": "进退无碍", "type": "踏虚",
        "unlock": 30, "prereq": ("C01_A07", 3),
        # 终端改造：原为"位移期间"，改为"A04/A07 释放后"
        "dr": [6, 8, 10, 12, 15],
        "window": 1.5,
        "deviation": "原为位移期间减伤，终端无位移，改为技能释放后",
        "mastery": "窗口内额外减伤",
        "m2": True,
    },
    "C01_P08": {
        "key": "C01_P08", "name": "照真同证", "type": "照真",
        "unlock": 30, "prereq": ("C01_A08", 3),
        "def_extra": [1, 2, 3, 4, 5],
        "dur_extra": [0.5, 1, 1.5, 2, 3],
        "mastery_dmg": 10,
        "deviation": "5级精通原为给队友明识，终端单人改为自身对显妄目标伤害 +10%",
        "mastery": "对显妄目标伤害 +10%",
        "m2": True,
    },
}

# M2 只实现这两个（其余依赖位移/破韧/显妄共享，留到 M4）
M2_PASSIVES = ["C01_P01", "C01_P05"]
ALL_PASSIVES = [k for k in PASSIVES]


def mult(skill_key, level):
    s = SKILLS[skill_key]
    return s["mult"][min(level, 5) - 1]


def cooldown(skill_key, level):
    s = SKILLS[skill_key]
    return s["cd"][min(level, 5) - 1]


def gain_of(skill_key, level):
    s = SKILLS[skill_key]
    return s["gain"][min(level, 5) - 1]


def realm_add(skill_key, level):
    s = SKILLS[skill_key]
    arr = s.get("realm_add")
    return arr[min(level, 5) - 1] if arr else 0.0
