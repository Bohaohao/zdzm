# -*- coding: utf-8 -*-
"""
法宝与套装。

⚠️ 法宝效果是【终端版偏离设计】，已获作者授权（方案 B）。

策划案原始设计（三篇法宝详细设计与材料来源包 §2 §3）：
  定潮玄印 = 信息辅助：保留正确侧的潮线预警，玩家仍自行走位
  熔脉劫核 = 信息辅助：让团队看到已确认的破韧进压/撤离方向
  两者都明确禁止「伤害、护盾、无敌、延长破韧、生成伤害」

终端版没有空间方位、没有走位、没有队伍语音，这类信息辅助无对应物，
因此改写为同一主题下的数值表达：
  定潮玄印「识潮→定界→回澜」 → 资源循环强化（涨得更快、门槛更低）
  熔脉劫核「识势→成线→裂阵」 → 洞明窗口爆发（看准时机打更痛）

名称、获取方式、单槽约束、不可叠加均沿用策划案，未改。
"""

ARTIFACTS = {
    "ART_HG_TIDE_SEAL": {
        "key": "ART_HG_TIDE_SEAL",
        "name": "定潮玄印",
        "tier": "low",
        "source": "龙宫旧潮首通",
        "desc": "识潮、定界、回澜。潮起潮落，先看清水往哪边走",
        "effect": {
            "resource_gain_mult": 1.15,     # 生势 +15%
            "realm_threshold_delta": -5,    # 洞明阈值 80 → 75
        },
        "deviation": "原为潮线预警提示；终端版无空间方位，改为资源循环强化",
    },
    "ART_HG_FLAME_CORE": {
        "key": "ART_HG_FLAME_CORE",
        "name": "熔脉劫核",
        "tier": "low_high",
        "source": "牛魔旧战场稀有",
        "desc": "识势、成线、裂阵。看准了那道缝，一击就够",
        "effect": {
            "realm_damage_mult": 1.12,      # 洞明期间伤害 +12%
            "cost_refund": 5,               # 耗势技能返还 5 战势
        },
        "deviation": "原为团队破韧窗口共享；终端版单人无队友，改为洞明爆发",
    },
}

SETS = {
    "EQ_HG_SET_GUARD_T1": {
        "key": "EQ_HG_SET_GUARD_T1",
        "name": "镇守",
        "source": "牛魔旧战场首通",
        "pieces": ["weapon", "helm", "body", "boots"],
        # 2 / 4 件加成（provisional，策划案待决）
        "bonus2": {"def": 40},
        "bonus4": {"hp": 300, "atk": 30},
    },
}


def artifact(key):
    return ARTIFACTS.get(key)


def set_def(key):
    return SETS.get(key)


def effect_of(p):
    a = ARTIFACTS.get(p.get("artifact") or "")
    return (a or {}).get("effect") or {}


def resource_gain_mult(p):
    return effect_of(p).get("resource_gain_mult", 1.0)


def realm_threshold_delta(p):
    return effect_of(p).get("realm_threshold_delta", 0)


def realm_damage_mult(p):
    return effect_of(p).get("realm_damage_mult", 1.0)


def cost_refund(p):
    return effect_of(p).get("cost_refund", 0)


def set_bonus(p):
    """统计身上套装件数，返回 (防御, 生命, 攻击) 加成。"""
    counts = {}
    for it in (p.get("equipped") or {}).values():
        if not it:
            continue
        sk = it.get("set_key")
        if sk:
            counts[sk] = counts.get(sk, 0) + 1
    d = h = a = 0
    for sk, n in counts.items():
        sd = SETS.get(sk)
        if not sd:
            continue
        if n >= 2:
            d += sd["bonus2"].get("def", 0)
            h += sd["bonus2"].get("hp", 0)
            a += sd["bonus2"].get("atk", 0)
        if n >= 4:
            d += sd["bonus4"].get("def", 0)
            h += sd["bonus4"].get("hp", 0)
            a += sd["bonus4"].get("atk", 0)
    return d, h, a
