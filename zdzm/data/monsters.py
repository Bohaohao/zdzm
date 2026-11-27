# -*- coding: utf-8 -*-
"""
花果山怪物。

名字与行为来自 docs/08-花果山篇野外怪物与BOSS设计.md §野外区域划分。
血量/攻击/防御全部 provisional（策划案 pending），按 tier 分档，
生成时按关卡等级缩放。

tier 对应 docs/08 的三层强度 + 掉落 profile 的档次：
    COMMON  普通小怪
    ELITE   精英
    MAJOR   野外大精英（你的 MAJOR 池）
    BOSS    野外区域 BOSS（你的 PUBLIC 池）
"""

# 基础值按 Lv1 定义，生成时按关卡等级缩放
MONSTERS = {
    # ---------------- 区域 1 山道 ----------------
    "shan_hou": {          # 山猴：小范围追击，成群出现
        "name": "山猴", "tier": "COMMON", "kind": "melee",
        "hp": 380, "atk": 13, "def": 5, "mdef": 2, "aps": 1.0,
    },
    "shi_pi": {            # 石皮山怪：移速慢，生命较高
        "name": "石皮山怪", "tier": "COMMON", "kind": "tank",
        "hp": 620, "atk": 15, "def": 9, "mdef": 2, "aps": 0.7,
    },
    "teng_ye": {           # 藤叶小妖：远程
        "name": "藤叶小妖", "tier": "COMMON", "kind": "ranged",
        "hp": 300, "atk": 14, "def": 3, "mdef": 4, "aps": 1.1,
    },
    "hou_tou": {           # 猴群头目：精英，召唤山猴
        "name": "猴群头目", "tier": "ELITE",
        "hp": 1100, "atk": 22, "def": 12, "mdef": 4, "aps": 1.0,
    },
    "da_xing_xing": {      # 大猩猩：野外大精英
        "name": "大猩猩", "tier": "MAJOR",
        "hp": 3400, "atk": 32, "def": 18, "mdef": 6, "aps": 0.9,
    },

    # ---------------- 区域 2 水帘溪谷 ----------------
    "shui_lian": {"name": "水帘小妖", "tier": "COMMON", "kind": "melee",
                  "hp": 420, "atk": 15, "def": 6, "mdef": 4, "aps": 1.0},
    "quan_ling": {"name": "泉灵", "tier": "COMMON", "kind": "support",
                  "hp": 360, "atk": 12, "def": 4, "mdef": 6, "aps": 0.9},
    "yu_yao": {"name": "鱼妖哨兵", "tier": "COMMON", "kind": "ranged",
               "hp": 340, "atk": 16, "def": 4, "mdef": 5, "aps": 1.1},
    "shui_wei": {"name": "水帘妖卫", "tier": "ELITE",
                 "hp": 1250, "atk": 24, "def": 13, "mdef": 6, "aps": 1.0},
    "mi_hou_wang": {"name": "猕猴王", "tier": "BOSS",
                    "hp": 3800, "atk": 44, "def": 24, "mdef": 10, "aps": 0.85},

    # ---------------- 区域 3 桃林 ----------------
    "tao_hua": {"name": "桃花妖", "tier": "COMMON", "kind": "ranged",
                "hp": 460, "atk": 18, "def": 6, "mdef": 7, "aps": 1.0},
    "mi_zong": {"name": "迷踪猴", "tier": "COMMON", "kind": "melee",
                "hp": 480, "atk": 17, "def": 7, "mdef": 3, "aps": 1.2},
    "yu_rong": {"name": "禺狨王", "tier": "MAJOR",
                "hp": 4200, "atk": 36, "def": 20, "mdef": 8, "aps": 0.95},

    # ---------------- 区域 4 蝙蝠窟 ----------------
    "dong_bat": {"name": "洞窟蝙蝠", "tier": "COMMON", "kind": "flying",
                 "hp": 320, "atk": 19, "def": 5, "mdef": 5, "aps": 1.3},
    "dong_yao": {"name": "洞窟小妖", "tier": "COMMON", "kind": "melee",
                 "hp": 560, "atk": 20, "def": 9, "mdef": 4, "aps": 1.0},
    "bian_fu_shixiang": {"name": "蝙蝠石像", "tier": "MAJOR",
                         "hp": 4800, "atk": 38, "def": 24, "mdef": 10, "aps": 0.7},

    # ---------------- 区域 5 七星洞 ----------------
    "qi_xing": {"name": "七星洞妖", "tier": "COMMON", "kind": "melee",
                "hp": 720, "atk": 24, "def": 12, "mdef": 6, "aps": 1.0},
    "shan_xiao": {"name": "山魈术士", "tier": "COMMON", "kind": "ranged",
                  "hp": 640, "atk": 27, "def": 9, "mdef": 9, "aps": 0.95},
    "fei_yi": {"name": "飞翼妖", "tier": "COMMON", "kind": "flying",
               "hp": 600, "atk": 26, "def": 8, "mdef": 7, "aps": 1.25},
    "niu_mo_scout": {"name": "牛魔斥候", "tier": "ELITE",
                     "hp": 2100, "atk": 34, "def": 18, "mdef": 8, "aps": 1.0},
    "shi_tuo": {"name": "狮驼王", "tier": "MAJOR",
                "hp": 6800, "atk": 46, "def": 26, "mdef": 12, "aps": 0.9},
    "peng_mo": {"name": "鹏魔王", "tier": "BOSS", "optional": True,
                "hp": 5200, "atk": 52, "def": 26, "mdef": 14, "aps": 1.0},

    # ---------------- 区域 6 东海前缘 ----------------
    "yu_xun": {"name": "鱼妖巡兵", "tier": "COMMON", "kind": "melee",
               "hp": 880, "atk": 27, "def": 14, "mdef": 8, "aps": 1.05},
    "gui_jia": {"name": "龟甲守卫", "tier": "COMMON", "kind": "tank",
                "hp": 1400, "atk": 25, "def": 22, "mdef": 8, "aps": 0.65},
    "shui_ling": {"name": "水灵术士", "tier": "COMMON", "kind": "ranged",
                  "hp": 820, "atk": 30, "def": 11, "mdef": 12, "aps": 0.95},
    "xuan_wo": {"name": "漩涡妖兵", "tier": "ELITE",
                "hp": 2400, "atk": 38, "def": 20, "mdef": 10, "aps": 1.0},
    "jiao_mo": {"name": "蛟魔王", "tier": "BOSS",
                "hp": 6000, "atk": 56, "def": 28, "mdef": 14, "aps": 0.85},
    "sha_mo": {"name": "鲨魔王", "tier": "BOSS",
               "hp": 7200, "atk": 62, "def": 30, "mdef": 12, "aps": 0.9},

    # ---------------- 龙宫旧潮（单人本）---------------
    # 数值 provisional，按"单人可通"标定：BOSS 战约 40-60 秒
    "gui_cheng_xiang": {"name": "龟丞相", "tier": "ELITE",
                        "hp": 2600, "atk": 22, "def": 18, "mdef": 8, "aps": 0.8},
    "long_wang": {"name": "龙王·旧潮化身", "tier": "BOSS", "fixed_level": True,
                  "hp": 12000, "atk": 24, "def": 22, "mdef": 12, "aps": 0.9},

    # ---------------- 牛魔旧战场（团队本）----------------
    "niu_ren": {"name": "牛魔·人形", "tier": "BOSS", "fixed_level": True,
                "hp": 14000, "atk": 26, "def": 22, "mdef": 10, "aps": 0.85},
    "niu_bai": {"name": "披甲白牛", "tier": "BOSS", "fixed_level": True,
                "hp": 16000, "atk": 30, "def": 26, "mdef": 10, "aps": 0.75},

    # ---------------- 训练木桩 ----------------
    "dummy": {"name": "训练木桩", "tier": "DUMMY",
              "hp": 999999, "atk": 0, "def": 40, "mdef": 0, "aps": 0.1},
}

# 破韧阈值（策划案 §6 / 15 号契约给出的 BOSS 值，其余 provisional）
POISE = {
    "COMMON": 8, "ELITE": 15, "MAJOR": 25, "BOSS": 18, "DUMMY": 999999,
}
POISE_BY_KEY = {
    "long_wang": 11,     # 策划案：龙宫龙王阈值 11
    "niu_ren": 20,       # 策划案：牛魔人形阈值 20
    "niu_bai": 24,       # 策划案：披甲白牛阈值 24
}
# 全局缩放（provisional）：比例减伤上线后，原血量/攻击配比过重
HP_SCALE = 1.00
ATK_SCALE = 1.00
BROKEN_DURATION = 4.0    # 策划案：破韧窗口 4 秒
BROKEN_TAKEN_MULT = 1.25 # 破韧期间受伤加成（provisional）

# 等级缩放（provisional）
GROWTH = {
    # 血量成长压低：原 0.26/0.24 到 Lv16 会翻 4.9 倍，BOSS 战拉到 80 秒
    "COMMON": (0.30, 0.14, 0.16),   # hp, atk, def
    "ELITE":  (0.28, 0.13, 0.15),
    "MAJOR":  (0.26, 0.12, 0.14),
    "BOSS":   (0.24, 0.11, 0.13),
    "DUMMY":  (0.00, 0.00, 0.00),
}

# 经验与金币（provisional）
REWARD = {
    "COMMON": (34, (4, 9)),
    "ELITE":  (140, (22, 40)),
    "MAJOR":  (620, (90, 160)),
    "BOSS":   (2600, (400, 700)),
    "DUMMY":  (0, (0, 0)),
}


def get(key):
    return MONSTERS[key]


def scale(key, level):
    """按关卡等级生成一只怪物。副本 BOSS 用固定数值，不缩放。"""
    m = MONSTERS[key]
    tier = m["tier"]
    if m.get("fixed_level"):
        xp, gold = REWARD.get(tier, (30, (4, 9)))
        hp = int(round(m["hp"] * HP_SCALE))
        return {
            "id": "m1", "side": "enemy", "key": key, "name": m["name"],
            "tier": tier, "level": level, "alive": True,
            "max_hp": hp, "hp": hp,
            "atk": round(m["atk"] * ATK_SCALE, 1), "def": m["def"], "mdef": m["mdef"],
            "aps": m["aps"], "crit": 4.0, "crit_mult": 1.5,
            "xp": xp * 3, "gold": gold, "buffs": [],
            "poise_max": POISE_BY_KEY.get(key, POISE.get(tier, 10)),
            "poise": POISE_BY_KEY.get(key, POISE.get(tier, 10)),
            "broken_until": 0.0,
        }
    gh, ga, gd = GROWTH.get(tier, (0.28, 0.13, 0.15))
    k = max(0, level - 1)
    xp, gold = REWARD.get(tier, (30, (4, 9)))
    hp = int(round(m["hp"] * (1 + gh * k) * HP_SCALE))
    return {
        "id": "m1",
        "side": "enemy",
        "key": key,
        "name": m["name"],
        "tier": tier,
        "level": level,
        "alive": True,
        "max_hp": hp,
        "hp": hp,
        "atk": round(m["atk"] * (1 + ga * k) * ATK_SCALE, 1),
        "def": round(m["def"] * (1 + gd * k), 1),
        "mdef": m["mdef"],
        "aps": m["aps"],
        "crit": 4.0 if tier in ("MAJOR", "BOSS") else 2.0,
        "crit_mult": 1.5,
        "xp": int(round(xp * (1 + 0.18 * k))),
        "gold": gold,
        "buffs": [],
        "poise_max": POISE_BY_KEY.get(key, POISE.get(tier, 10)),
        "poise": POISE_BY_KEY.get(key, POISE.get(tier, 10)),
        "broken_until": 0.0,
    }
