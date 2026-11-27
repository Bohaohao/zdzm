# -*- coding: utf-8 -*-
"""
花果山九项收集。

来源：docs/08-花果山篇野外怪物与BOSS设计.md §怪物与收集联动
      docs/03-成长与用户粘性系统.md §主城收集机制

策划案要求：
  - 前 3 项主要由公共野外完成，不靠副本和低概率掉落
  - 收集不阻塞主线、不作为极低概率唯一前置
  - 奖励是称号 / 展示，轻量属性需过门禁

终端版：全部用「击杀计数 / 通关次数 / 获得记录」判定，没有概率项。
"""

# type: kill_region / stage_clear / instance_clear / instance_count / artifact / boss_kill
COLLECTIONS = [
    {
        "key": "C_HG_01", "name": "初入花果山", "type": "kill_region",
        "region": "MOUNTAIN", "need": 50,
        "desc": "在山道击杀 50 只妖物",
        "reward": "称号：山野初行",
    },
    {
        "key": "C_HG_02", "name": "水帘寻踪", "type": "region_clear",
        "region": "WATERFALL", "need": 1,
        "desc": "通关水帘溪谷副本",
        "reward": "称号：寻踪者",
    },
    {
        "key": "C_HG_03", "name": "洞窟清剿", "type": "region_clear",
        "region": "CAVE", "need": 1,
        "region": "CAVE", "need": 50,
        "desc": "通关蝙蝠窟副本",
        "reward": "称号：扫穴人",
    },
    {
        "key": "C_HG_04", "name": "龙宫试炼", "type": "instance_clear",
        "instance": "dragon_old", "need": 1,
        "desc": "通关龙宫旧潮",
        "reward": "称号：入海客",
    },
    {
        "key": "C_HG_05", "name": "龙宫遗珍", "type": "instance_count",
        "instance": "dragon_old", "need": 3,
        "desc": "通关龙宫旧潮 3 次",
        "reward": "称号：龙宫常客",
    },
    {
        "key": "C_HG_06", "name": "潮印初成", "type": "artifact",
        "artifact": "ART_HG_TIDE_SEAL", "need": 1,
        "desc": "获得定潮玄印",
        "reward": "称号：识潮人",
    },
    {
        "key": "C_HG_07", "name": "熔脉破阵", "type": "boss_kill",
        "boss": "niu_ren", "need": 1,
        "desc": "击败牛魔人形",
        "reward": "称号：破阵者",
    },
    {
        "key": "C_HG_08", "name": "白牛镇服", "type": "boss_kill",
        "boss": "niu_bai", "need": 1,
        "desc": "击败披甲白牛",
        "reward": "称号：镇牛人",
    },
    {
        "key": "C_HG_09", "name": "劫痕逆斩", "type": "instance_count",
        "instance": "ox", "need": 3,
        "desc": "通关牛魔旧战场 3 次",
        "reward": "称号：劫痕逆斩",
    },
]

BY_KEY = {c["key"]: c for c in COLLECTIONS}


def all_of():
    return COLLECTIONS
