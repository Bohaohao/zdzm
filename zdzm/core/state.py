# -*- coding: utf-8 -*-
"""Actor 创建与属性重算。

重算顺序照策划案 `18-成长系统进度…契约.md` §三：
  等级裸装基础层 -> 装备 -> 强化/进阶 -> 套装/法宝/宠物 -> 临时战斗状态
M1 只有第一层。

取整规则照同一节：「先保留完整定点值，最终写入战斗属性时统一四舍五入」。
"""
from zdzm.data import classes as C
from zdzm.data import monsters as M


def make_player(cls_key="C01", level=1, actor_id="p1"):
    cls = C.CLASSES[cls_key]
    a = {
        "id": actor_id,
        "side": "player",
        "cls": cls_key,
        "name": cls["name"],
        "level": level,
        "alive": True,

        # 战斗资源（临时态，不入存档）
        "resource": 0,
        "ultimate": 0.0,
        "realm": False,                 # 洞明
        "combo": 0,
        "combo_expire_at": 0.0,
        "last_valid_attack_at": 0.0,

        # 技能
        "skills": {},                   # {skill_key: level}
        "loadout": [],                  # 5 个主动槽（技能键）
        "passives": {},                 # {passive_key: level}
        "skill_points": 0,
        "cd": {},                       # {skill_key: ready_at}
        "casting": None,                # {"skill": key, "done_at": t}
        "dr_buff": None,                # {"until": t, "value": pct}
        "debuffs": {},                  # 施加给目标的（M2 只有 def_down）

        # P01 势行不滞
        "p01_until": 0.0,
        "p01_bonus": 0,
        # P05 守意归元
        "p05_meter": 0.0,
        "p05_icd_until": 0.0,

        # 时间轴
        "next_attack_at": 0.0,
        "gcd_ready_at": 0.0,

        "buffs": [],
        "damage_done": 0,
        "hits": 0,

        # 装备与背包
        "equipped": {},                 # {slot: item}
        "bag": [],                      # [item]
        "gold": 0,
        "xp": 0,

        # 法宝与进度
        "artifact": None,
        "artifacts_owned": [],
        "materials": {},
        "common": {},                   # 通用被动 {key: level}
        "unlocked": [],
        "instance_clears": [],
    }
    recalc(a)
    a["hp"] = a["max_hp"]
    return a


def recalc(a):
    """幂等重算：任何一次重算都必须和初始化一次结果一致。

    顺序照 18 号契约 §三：等级裸装 -> 装备 -> 强化/进阶 -> 套装 -> 临时。
    M4 覆盖前两层（强化并入装备的 plus）。
    """
    cls = C.CLASSES[a["cls"]]
    lv = a["level"]
    hp = cls["base_hp"] + cls["hp_per_lvl"] * (lv - 1)
    atk = cls["base_atk"] + cls["atk_per_lvl"] * (lv - 1)
    df = cls["base_def"] + cls["def_per_lvl"] * (lv - 1)
    mdf = cls["base_mdef"] + cls["mdef_per_lvl"] * (lv - 1)
    crit = float(cls["crit"])

    for it in (a.get("equipped") or {}).values():
        if not it:
            continue
        v = it["value"] * (1 + it.get("plus", 0) * 0.04)
        m = it["main"]
        if m == "atk":
            atk += v
        elif m == "def":
            df += v
        elif m == "hp":
            hp += v
        elif m == "crit":
            crit += v

    # 套装加成
    from zdzm.data import artifacts as A
    sd, sh, sa = A.set_bonus(a)
    df += sd
    hp += sh
    atk += sa

    # 法宝被动
    art = A.artifact(a.get("artifact"))
    if art:
        pa = art.get("passive") or {}
        atk += pa.get("atk", 0)
        hp += pa.get("hp", 0)
        df += pa.get("def", 0)

    # 通用被动（百分比，最后乘）——所有职业共享的面板属性
    from zdzm.data import common_passives as CP
    cm = CP.multipliers(a)
    hp *= cm["hp"]
    atk *= cm["atk"]
    df *= cm["def"]
    crit += cm["crit"]

    a["max_hp"] = round(hp)
    a["atk"] = round(atk)
    a["def"] = round(df)
    a["mdef"] = round(mdf)
    a["aps"] = cls["aps"]
    a["crit"] = round(crit, 1)
    a["crit_mult"] = cls["crit_mult"] + cm["cdmg"]
    if a.get("hp", 0) > a["max_hp"]:
        a["hp"] = a["max_hp"]
    return a


def make_monster(key, actor_id="m1", level=None):
    """按等级生成怪物（数值走 data.monsters.scale）。"""
    a = M.scale(key, level or 1)
    a["id"] = actor_id
    return a


def is_player(a):
    return a.get("side") == "player"


def resource_pct(a):
    if not is_player(a):
        return 0.0
    return a["resource"] / float(C.CLASSES[a["cls"]]["resource_max"])
