# -*- coding: utf-8 -*-
"""
四职业裸装成长与资源规则。

数值来源（accepted-baseline）：
  docs/物编/18-成长系统进度、掉落与长期目标契约.md §三
  docs/归档/职业设计/01-职业与技能树设计大纲.md §职业战斗资源
  docs/归档/职业设计/02-破妄法门资源循环与完整技能组.md §3

攻速、暴击率、伤害系数在策划案中未定义（numeric_policy: deferred），
本文件标 provisional。
"""

CLASSES = {
    "C01": {
        "key": "C01",
        "name": "破妄",
        "weapon": "长兵",
        "resource": "zhan",
        "resource_name": "战势",
        "resource_max": 100,
        "realm_name": "洞明",
        "realm_threshold": 80,          # 策划案 §3.5：释放前战势达到 80 进入洞明

        # 裸装成长（accepted）
        "base_hp": 620, "hp_per_lvl": 68,
        "base_atk": 48, "atk_per_lvl": 5.7,
        "base_def": 22, "def_per_lvl": 1.9,
        "base_mdef": 16, "mdef_per_lvl": 1.5,

        # ---- 以下 provisional（策划案无） ----
        "aps": 1.20,                    # 每秒攻击次数
        "crit": 5.0,                    # 暴击率 %
        "crit_mult": 1.75,

        # 普攻三段生势（策划案 §3.3：4 / 4 / 7，连段窗口 1.4 秒）
        "combo_gain": [4, 4, 7],
        "combo_window": 1.4,

        # 断循环（策划案 §3.1：连续 4 秒未有效攻击后，每秒衰减 12）
        "decay_after": 4.0,
        "decay_per_sec": 12,

        # 绝技值换算（策划案 §3.5：1 战势 = 0.2 绝技值）
        "ultimate_per_resource": 0.2,
    },
}

# 一阶技能只放 M1 需要的最小集。
# 完整 8 主动 / 8 被动在 M2 补齐，数值来自 docs/归档/职业设计/02-破妄法门资源循环…
SKILLS = {
    "C01_A00": {
        "key": "C01_A00",
        "name": "普通攻击",
        "kind": "attack",
        "cast": 0.0,
        "cd": 0.0,
        "gcd": 0.0,
        "mult": 1.0,
        "hits": 1,
        "gain": None,               # 由 combo 逻辑单独处理
    },
}


# ---------------------------------------------------------------- 经验曲线
# provisional：exp_to_next(n) = 75 * n^1.85
# 策划案 experience-progression.json 的 ECO-XP-001 为 deferred，此处为占位
XP_COEF = 90.0
XP_POW = 1.85


def xp_to_next(level):
    return int(round(XP_COEF * (max(1, level) ** XP_POW)))
