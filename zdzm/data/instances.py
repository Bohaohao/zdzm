# -*- coding: utf-8 -*-
"""
副本：龙宫旧潮（单人）、牛魔旧战场（团队/单人佣兵）。

结构来自 docs/物编/15-花果山遭遇与BOSS战斗契约.md：
  龙宫：门将短战 -> 海眼阶梯 -> 龙王战
  牛魔：人形 -> 披甲白牛（同一场战斗的两阶段）

副本不参与 push 主线链，必须手动进入（DESIGN.md §6.3 边界）。
"""

INSTANCES = {
    "dragon_old": {
        "key": "dragon_old",
        "name": "龙宫旧潮",
        "type": "solo",
        "level": 12,
        "time_limit": 720,
        "pool": "HG_DROP_DRAGON_OLD",
        "first_clear_reward": "ART_HG_TIDE_SEAL",
        "stages": [
            {"name": "门将", "waves": [["gui_cheng_xiang"]]},
            {"name": "海眼阶梯", "waves": [["yu_yao", "gui_jia"], ["yu_yao", "gui_jia"]]},
            {"name": "海眼", "waves": [["long_wang"]]},
        ],
    },
    "ox": {
        "key": "ox",
        "name": "牛魔旧战场",
        "type": "raid",
        "level": 20,
        "time_limit": 1200,
        "pool": "HG_DROP_OX_RAID",
        "first_clear_reward": "EQ_HG_SET_GUARD_T1",
        "stages": [
            {"name": "熔脉裂口", "waves": [["niu_mo_scout"], ["niu_mo_scout", "qi_xing"]]},
            {"name": "人形", "waves": [["niu_ren"]]},
            {"name": "白牛", "waves": [["niu_bai"]]},
        ],
    },
}


def get(key):
    return INSTANCES[key]


def list_all():
    return list(INSTANCES.values())
