# -*- coding: utf-8 -*-
"""
花果山 6 区域 18 关。

关卡数不是拍脑袋定的——由 21 个掉落 profile 的档次分布反推：
    MOUNTAIN:  COMMON + ELITE + MAJOR          -> 3 关
    WATERFALL: COMMON + ELITE + MACAQUE_PUBLIC -> 3 关
    PEACH:     COMMON + MAJOR                  -> 2 关
    CAVE:      COMMON + MAJOR                  -> 2 关
    SEVENSTAR: COMMON + ELITE + MAJOR + PENG   -> 4 关
    EASTSEA:   COMMON + ELITE + JIAO + SHARK   -> 4 关

怪物配置来自 docs/08-花果山篇野外怪物与BOSS设计.md §野外区域划分。
"""

REGIONS = [
    {
        "key": "MOUNTAIN", "name": "花果山山道", "lv": (1, 3),
        "stages": [
            {"key": "1-1", "name": "山道入口", "level": 1, "type": "COMMON",
             "pool": "HG_DROP_MOUNTAIN_COMMON",
             "waves": [["shan_hou", "shan_hou"], ["teng_ye", "shan_hou"], ["shi_pi"]]},
            {"key": "1-2", "name": "猴群营地", "level": 2, "type": "ELITE",
             "pool": "HG_DROP_MOUNTAIN_ELITE",
             "waves": [["shan_hou", "shan_hou", "teng_ye"], ["shi_pi", "shan_hou"], ["hou_tou"]]},
            {"key": "1-3", "name": "猩猩巢穴", "level": 3, "type": "MAJOR",
             "pool": "HG_DROP_MOUNTAIN_MAJOR",
             "waves": [["shan_hou", "shi_pi"], ["da_xing_xing"]]},
        ],
    },
    {
        "key": "WATERFALL", "name": "水帘溪谷", "lv": (4, 6),
        "stages": [
            {"key": "2-1", "name": "溪谷浅滩", "level": 4, "type": "COMMON",
             "pool": "HG_DROP_WATERFALL_COMMON",
             "waves": [["shui_lian", "shui_lian"], ["yu_yao", "quan_ling"], ["shui_lian", "yu_yao"]]},
            {"key": "2-2", "name": "妖卫哨所", "level": 5, "type": "ELITE",
             "pool": "HG_DROP_WATERFALL_ELITE",
             "waves": [["shui_lian", "yu_yao"], ["quan_ling", "shui_lian"], ["shui_wei"]]},
            {"key": "2-3", "name": "瀑布台", "level": 6, "type": "BOSS",
             "pool": "HG_DROP_MACAQUE_PUBLIC",
             "waves": [["shui_lian", "yu_yao"], ["mi_hou_wang"]]},
        ],
    },
    {
        "key": "PEACH", "name": "桃林", "lv": (7, 9),
        "stages": [
            {"key": "3-1", "name": "桃林小径", "level": 7, "type": "COMMON",
             "pool": "HG_DROP_PEACH_COMMON",
             "waves": [["tao_hua", "mi_zong"], ["mi_zong", "mi_zong"], ["tao_hua", "mi_zong"]]},
            {"key": "3-2", "name": "惑雾深处", "level": 9, "type": "MAJOR",
             "pool": "HG_DROP_PEACH_MAJOR",
             "waves": [["mi_zong", "tao_hua"], ["yu_rong"]]},
        ],
    },
    {
        "key": "CAVE", "name": "蝙蝠窟", "lv": (10, 12),
        "stages": [
            {"key": "4-1", "name": "洞窟入口", "level": 10, "type": "COMMON",
             "pool": "HG_DROP_CAVE_COMMON",
             "waves": [["dong_bat", "dong_bat"], ["dong_yao", "dong_bat"], ["dong_yao"]]},
            {"key": "4-2", "name": "古阵残响", "level": 12, "type": "MAJOR",
             "pool": "HG_DROP_CAVE_MAJOR",
             "waves": [["dong_bat", "dong_yao"], ["bian_fu_shixiang"]]},
        ],
    },
    {
        "key": "SEVENSTAR", "name": "七星洞", "lv": (13, 17),
        "stages": [
            {"key": "5-1", "name": "七星洞窟", "level": 13, "type": "COMMON",
             "pool": "HG_DROP_SEVENSTAR_COMMON",
             "waves": [["qi_xing", "qi_xing"], ["shan_xiao", "fei_yi"], ["qi_xing", "shan_xiao"]]},
            {"key": "5-2", "name": "斥候营地", "level": 14, "type": "ELITE",
             "pool": "HG_DROP_SEVENSTAR_ELITE",
             "waves": [["qi_xing", "fei_yi"], ["shan_xiao", "qi_xing"], ["niu_mo_scout"]]},
            {"key": "5-3", "name": "狮驼关隘", "level": 16, "type": "MAJOR",
             "pool": "HG_DROP_SEVENSTAR_MAJOR",
             "waves": [["niu_mo_scout", "qi_xing"], ["shi_tuo"]]},
            {"key": "5-4", "name": "迦楼罗崖", "level": 17, "type": "OPTIONAL",
             "pool": "HG_DROP_PENG_OPTIONAL",
             "waves": [["fei_yi", "fei_yi"], ["peng_mo"]]},
        ],
    },
    {
        "key": "EASTSEA", "name": "东海前缘", "lv": (18, 20),
        "stages": [
            {"key": "6-1", "name": "东海滩涂", "level": 18, "type": "COMMON",
             "pool": "HG_DROP_EASTSEA_COMMON",
             "waves": [["yu_xun", "yu_xun"], ["shui_ling", "gui_jia"], ["yu_xun", "shui_ling"]]},
            {"key": "6-2", "name": "漩涡海域", "level": 19, "type": "ELITE",
             "pool": "HG_DROP_EASTSEA_ELITE",
             "waves": [["yu_xun", "shui_ling"], ["gui_jia", "yu_xun"], ["xuan_wo"]]},
            {"key": "6-3", "name": "海眼", "level": 20, "type": "BOSS",
             "pool": "HG_DROP_JIAO_PUBLIC",
             "waves": [["xuan_wo", "yu_xun"], ["jiao_mo"]]},
            {"key": "6-4", "name": "鲨之涡流", "level": 20, "type": "BOSS",
             "pool": "HG_DROP_SHARK_PUBLIC",
             "waves": [["xuan_wo", "shui_ling"], ["sha_mo"]]},
        ],
    },
]

# ---- 扁平索引 ----
STAGES = {}
ORDER = []
for _r in REGIONS:
    for _s in _r["stages"]:
        _s["region"] = _r["key"]
        _s["region_name"] = _r["name"]
        STAGES[_s["key"]] = _s
        ORDER.append(_s["key"])


REGIONS_BY_KEY = {r["key"]: r for r in REGIONS}


def get(key):
    return STAGES[key]


def entry_of(region_key):
    """区域入口阶段，如 MOUNTAIN -> 1-1。"""
    r = REGIONS_BY_KEY[region_key]
    return r["stages"][0]["key"]


def region_of_entry(key):
    """入口阶段 -> 区域键。"""
    return STAGES[key]["region"]


def next_key(key):
    i = ORDER.index(key)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None


def region_of(key):
    return STAGES[key]["region"]


def region_stages(region_key):
    return [k for k in ORDER if STAGES[k]["region"] == region_key]


def first_key():
    return ORDER[0]


def last_key():
    return ORDER[-1]


def upcoming(key, n=1):
    """从 key 之后取 n 关（用于 push 预览）。"""
    i = ORDER.index(key)
    return ORDER[i + 1:i + 1 + n]
