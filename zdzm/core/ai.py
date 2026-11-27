# -*- coding: utf-8 -*-
"""自动战斗策略。

M2 版本：按优先级表选技能，选不出就普攻。
优先级的设计意图——先兑现洞明，再用资源，不够就生势。
"""
from zdzm.data.skills import SKILLS, cooldown


# (技能键, 条件)  条件签名: (resource, realm, player) -> bool
# 设计意图：战势是"攒到 80 进洞明再兑现"的资源，不是"有多少花多少"。
# 见 docs/归档/职业设计/02-破妄法门资源循环…md §3.5
RULES = [
    # 洞明窗口：优先大额兑现
    ("C01_A06", lambda r, realm, p: realm),
    ("C01_A02", lambda r, realm, p: realm),
    # 快溢出时提前兑现，避免浪费生势
    ("C01_A06", lambda r, realm, p: r >= 96),
    ("C01_A08", lambda r, realm, p: r >= 92),
    ("C01_A02", lambda r, realm, p: r >= 88),
    # 其余时间只生势，把战势攒起来
    ("C01_A05", lambda r, realm, p: True),
    ("C01_A01", lambda r, realm, p: True),
    ("C01_A03", lambda r, realm, p: True),
    ("C01_A04", lambda r, realm, p: True),
]


class Ai:
    def __init__(self, rules=None, use_skills=True):
        self.rules = rules if rules is not None else RULES
        self.use_skills = use_skills

    def choose(self, battle, p):
        """返回技能键；None 表示普攻。"""
        if not self.use_skills:
            return None
        now = battle.tl.now
        res = p["resource"]
        realm = p["realm"]

        loadout = p.get("loadout") or list(p["skills"])
        for key, cond in self.rules:
            lv = p["skills"].get(key, 0)
            if lv <= 0:
                continue
            if key not in loadout:      # 只放装配槽里的技能
                continue
            if p["cd"].get(key, 0) > now:
                continue
            sk = SKILLS[key]
            if sk["cost"] > res:
                continue
            if not cond(res, realm, p):
                continue
            return key
        return None
