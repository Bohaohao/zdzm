# -*- coding: utf-8 -*-
"""M1 机制自检：验证策划案里的时间规则是否被正确实现。

    python3 selftest.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from zdzm.core.rng import Rng
from zdzm.core.state import make_player, make_monster
from zdzm.core.combat import Battle
from zdzm.data import classes as C

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("%s %-42s %s" % ("✓" if cond else "✗", name, detail if not cond else ""))


def new_battle(seed=1, mon="shan_hou"):
    p = make_player("C01", 1)
    b = Battle(p, lambda: make_monster(mon), Rng(seed))
    return p, b


def last_attack(b):
    return [e for e in b.events if e["kind"] == "attack"][-1]


# ---------------------------------------------------------------- 1. 属性重算
p = make_player("C01", 1)
check("Lv1 破妄 生命 = 620", p["max_hp"] == 620, "实际 %s" % p["max_hp"])
check("Lv1 破妄 物攻 = 48", p["atk"] == 48, "实际 %s" % p["atk"])
check("Lv1 破妄 物防 = 22", p["def"] == 22, "实际 %s" % p["def"])

p20 = make_player("C01", 20)
check("Lv20 破妄 生命 = 1912", p20["max_hp"] == 620 + 68 * 19,
      "实际 %s" % p20["max_hp"])
check("Lv20 破妄 物攻 = 156", p20["atk"] == round(48 + 5.7 * 19),
      "实际 %s" % p20["atk"])

# 幂等方面：重算两次结果必须相同
from zdzm.core.state import recalc
before = (p20["max_hp"], p20["atk"], p20["def"])
recalc(p20)
recalc(p20)
after = (p20["max_hp"], p20["atk"], p20["def"])
check("属性重算幂等", before == after, "%s != %s" % (before, after))

# ---------------------------------------------------------------- 2. 连段生势
p, b = new_battle(seed=1, mon="dummy")
gains = []
for i in range(6):
    b.tl.now = i * 0.83
    b._player_act(p)
    gains.append(last_attack(b)["gain"])
check("普攻生势序列 = 4/4/7 循环", gains == [4, 4, 7, 4, 4, 7], "实际 %s" % gains)

# ---------------------------------------------------------------- 3. 连段窗口
p, b = new_battle(seed=1, mon="dummy")
b.tl.now = 0.0
b._player_act(p)          # 1 段
b.tl.now = 0.83
b._player_act(p)          # 2 段
b.tl.now = 0.83 + 1.5     # 超过 1.4 秒窗口
b._player_act(p)
seg = last_attack(b)["combo"]
check("超过 1.4 秒窗口连段重置", seg == 1, "实际回到第 %d 段" % seg)

# ---------------------------------------------------------------- 4. 战势上限与溢出
p, b = new_battle(seed=1, mon="dummy")
p["resource"] = 98
b.tl.now = 0.0
b._player_act(p)
ev = last_attack(b)
check("战势不超过 100", p["resource"] == 100, "实际 %s" % p["resource"])
check("溢出部分被丢弃", ev["overflow"] == 2, "溢出 %s，应为 2（98+4-100）" % ev["overflow"])

# ---------------------------------------------------------------- 5. 断循环衰减
p, b = new_battle(seed=1)
p["resource"] = 50
p["last_valid_attack_at"] = 0.0
b.tl.now = 3.9
b._on_decay("p1")
check("3.9 秒未攻击不衰减", p["resource"] == 50, "实际 %s" % p["resource"])

p["last_valid_attack_at"] = 0.0
b.tl.now = 4.0
b._on_decay("p1")
check("4.0 秒开始衰减，每 0.5 秒 -6", p["resource"] == 44, "实际 %s" % p["resource"])

p["last_valid_attack_at"] = 0.0
b.tl.now = 4.5
b._on_decay("p1")
check("第二次衰减再 -6", p["resource"] == 38, "实际 %s" % p["resource"])

# 恢复攻击后停止衰减
p["resource"] = 30
p["last_valid_attack_at"] = 10.0
b.tl.now = 10.5
b._on_decay("p1")
check("攻击后不衰减", p["resource"] == 30, "实际 %s" % p["resource"])

# ---------------------------------------------------------------- 6. 洞明阈值
p, b = new_battle(seed=1, mon="dummy")
p["resource"] = 76
b.tl.now = 0.0
b._player_act(p)          # +4 → 80
check("战势到 80 进入洞明", p["realm"] is True, "战势 %s，realm %s" % (p["resource"], p["realm"]))
check("洞明事件已产出",
      any(e["kind"] == "realm" and e["state"] == "enter" for e in b.events))

# ---------------------------------------------------------------- 7. 时间轴精度
from zdzm.core.timeline import Timeline
tl = Timeline()
tl.now = 0.0
tl.push(1.0, "x")
tl.push(0.5, "y")
tl.push(0.5, "z")
order = []
while not tl.empty():
    k, _ = tl.pop()
    order.append((round(tl.now, 3), k))
check("事件按时间排序", order == [(0.5, "y"), (0.5, "z"), (1.0, "x")], str(order))

# ---------------------------------------------------------------- 8. 技能
from zdzm.core.ai import Ai
from zdzm.data.skills import SKILLS, PASSIVES

p, b = new_battle(seed=1, mon="dummy")
p["skills"]["C01_A02"] = 5
p["skills"]["C01_A06"] = 5
p["skills"]["C01_A01"] = 5
p["resource"] = 100
p["realm"] = True          # 直接构造洞明态（正常流程由 _check_realm 维护）
b.tl.now = 0.0
b._resolve_skill(p, "C01_A02")
ev = [e for e in b.events if e["kind"] == "skill"][-1]
check("贯心式 Lv5 主击系数 245%", SKILLS["C01_A02"]["mult"][4] == 2.45)
check("贯心式扣 30 战势", ev["cost"] == 30)
check("洞明时追加伤害", ev["add"] > 0, "追加 %s" % ev["add"])
check("洞明追加后退出洞明标记", p["realm"] is False)
check("技能进入冷却", p["cd"]["C01_A02"] > 0)

# 冷却期间不能再选
p["resource"] = 100
pick = Ai().choose(b, p)
check("冷却中不会被选中", pick != "C01_A02", "选中了 %s" % pick)

# ---------------------------------------------------------------- 9. P01 势行不滞
p, b = new_battle(seed=1, mon="dummy")
p["skills"]["C01_A02"] = 1
p["skills"]["C01_A01"] = 1
p["passives"]["C01_P01"] = 3
p["resource"] = 100
b.tl.now = 0.0
b._resolve_skill(p, "C01_A02")
check("P01 在耗势后挂上加值", p["p01_bonus"] == PASSIVES["C01_P01"]["extra_gain"][2],
      "bonus=%s" % p["p01_bonus"])
b.tl.now = 1.0
r_before = p["resource"]
b._resolve_skill(p, "C01_A01")
ev = [e for e in b.events if e["kind"] == "skill"][-1]
check("P01 让下一个生势技能多吃 4 点",
      ev["gain"] == SKILLS["C01_A01"]["gain"][0] + 4, "实际 +%s" % ev["gain"])
check("P01 加值用掉后清零", p["p01_bonus"] == 0)

# ---------------------------------------------------------------- 10. P05 守意归元
p, b = new_battle(seed=1)
p["passives"]["C01_P05"] = 5
p["hp"] = 1000
p["max_hp"] = 2592
b.tl.now = 0.0
b._apply_p05(p, 50)
check("P05 消耗满 50 触发回血", p["hp"] > 1000, "hp=%s" % p["hp"])
check("P05 触发后进入 8 秒内置冷却", p["p05_icd_until"] == 8.0)
r1 = p["hp"]
b.tl.now = 1.0
b._apply_p05(p, 50)
check("P05 冷却中不重复回血", p["hp"] == r1, "hp=%s" % p["hp"])

# ---------------------------------------------------------------- 11. 前摇
p, b = new_battle(seed=1, mon="dummy")
p["skills"]["C01_A03"] = 1
p["resource"] = 0
b.tl.now = 0.0
b._start_skill(p, "C01_A03")
check("叠锋三破前摇 0.80 秒", abs(p["casting"]["done_at"] - 0.80) < 1e-6,
      "done_at=%s" % p["casting"]["done_at"])
check("读条期间不会再行动", b._player_act(p) is None)

# ---------------------------------------------------------------- 12. 关卡结构
from zdzm.data import zones as Z
from zdzm.core import drop

check("花果山共 18 关", len(Z.ORDER) == 18, "实际 %d" % len(Z.ORDER))
check("首关是 1-1", Z.first_key() == "1-1")
check("末关是 6-4", Z.last_key() == "6-4")
check("每关都有掉落池",
      all(Z.STAGES[k].get("pool") for k in Z.ORDER))
check("每关波次非空",
      all(Z.STAGES[k]["waves"] for k in Z.ORDER))
boss_like = [k for k in Z.ORDER if Z.STAGES[k]["type"] in ("BOSS", "OPTIONAL")]
check("BOSS 级遭遇 4 个（含鹏魔王可选）", len(boss_like) == 4, str(boss_like))
major_stages = [k for k in Z.ORDER if Z.STAGES[k]["type"] == "MAJOR"]
check("MAJOR 关 4 个", len(major_stages) == 4, str(major_stages))

# ---------------------------------------------------------------- 13. 掉落
rng = Rng(7)
st = {"char_id": "t", "pity": {}}
settlements, receipts = drop.roll(st, "HG_DROP_MACAQUE_PUBLIC", 6, rng)
check("BOSS 必掉", len(settlements) >= 2, "实际 %d" % len(settlements))
check("四字段齐全",
      all(set(s.keys()) >= {"quality", "rare_eligibility", "pity_progress", "ownership"}
          for s in settlements))
check("品质与稀有资格是独立字段",
      settlements[0]["quality"] != settlements[0]["rare_eligibility"])
rc = receipts[0]
need = ["source_profile", "encounter_instance_id", "actor_id",
        "qualification_snapshot_id", "drop_roll_id", "event_id",
        "resource_table_version", "schema_version", "owner_scope",
        "reward_slot_key", "pity_pool_key", "receipt_id"]
check("结算信封 12 字段", all(k in rc for k in need),
      "缺 %s" % [k for k in need if k not in rc])

# 保底：COMMON 池 12 次必出
st2 = {"char_id": "t", "pity": {}}
hits = 0
for _ in range(12):
    s2, _ = drop.roll(st2, "HG_DROP_MOUNTAIN_COMMON", 1, rng)
    hits += len(s2)
check("12 次判定至少出 1 件（硬保底）", hits >= 1, "实际 %d" % hits)

# 不同池互不共用
st3 = {"char_id": "t", "pity": {}}
drop.roll(st3, "HG_DROP_MOUNTAIN_COMMON", 1, rng)
check("COMMON 与 ELITE 保底池分离",
      "PITY_HG_COMMON" in st3["pity"] and "PITY_HG_ELITE" not in st3["pity"])

# ---------------------------------------------------------------- 14. push 推进
from zdzm.core.campaign import Campaign
pp = make_player("C01", 1)
camp = Campaign(pp, Rng(1), mode="push", stage="6-4")
camp.on_stage_clear()
check("最后一关 push 后转为 farm", camp.mode == "farm", "实际 %s" % camp.mode)
camp2 = Campaign(pp, Rng(1), mode="push", stage="1-1")
camp2.on_stage_clear()
check("push 推进到下一关", camp2.stage == "1-2", "实际 %s" % camp2.stage)

# ---------------------------------------------------------------- 15. 装备
from zdzm.core import gear, storage

pg = make_player("C01", 1)
base_atk = pg["atk"]
w = {"instance_id": "i1", "name": "测试长兵", "slot": "weapon", "quality": 2,
     "main": "atk", "value": 40, "ilvl": 1}
pg["equipped"]["weapon"] = w
recalc(pg)
check("装备加成进入攻击", pg["atk"] == base_atk + 40, "atk=%s" % pg["atk"])

p1 = make_player("C01", 1)
p2 = make_player("C01", 1)
p2["equipped"]["weapon"] = w
recalc(p2)
check("有武器战力更高", gear.power(p2) > gear.power(p1),
      "%.0f vs %.0f" % (gear.power(p2), gear.power(p1)))

# 自动装备：更好的才换
pg2 = make_player("C01", 1)
good = {"instance_id": "i2", "name": "好武器", "slot": "weapon", "quality": 4,
        "main": "atk", "value": 100, "ilvl": 1}
bad = {"instance_id": "i3", "name": "烂武器", "slot": "weapon", "quality": 0,
       "main": "atk", "value": 5, "ilvl": 1}
ok1, _ = gear.try_equip(pg2, good)
ok2, _ = gear.try_equip(pg2, bad)
check("好装备自动穿上", ok1 is True)
check("差装备不换", ok2 is False)
check("身上还是好武器", pg2["equipped"]["weapon"]["name"] == "好武器")

# 戒指两个槽
pg3 = make_player("C01", 1)
r1 = {"instance_id": "i4", "name": "戒指A", "slot": "ring", "quality": 2,
      "main": "crit", "value": 3, "ilvl": 1}
r2 = {"instance_id": "i5", "name": "戒指B", "slot": "ring", "quality": 3,
      "main": "crit", "value": 5, "ilvl": 1}
gear.equip(pg3, r1, "ring1")
gear.equip(pg3, r2, "ring2")
check("两个戒指槽都能用",
      pg3["equipped"]["ring1"]["name"] == "戒指A" and pg3["equipped"]["ring2"]["name"] == "戒指B")

# 强化安全
pg4 = make_player("C01", 1)
pg4["gold"] = 10 ** 6
item = {"instance_id": "i6", "name": "强化测试", "slot": "weapon", "quality": 2,
        "main": "atk", "value": 50, "ilvl": 1}
pg4["equipped"]["weapon"] = item
for _ in range(20):
    gear.strengthen(pg4, item)
check("强化上限 15", item["plus"] == 15, "plus=%s" % item["plus"])
check("强化不会降级或归零", item["plus"] == 15)

# 存档往返
ps = make_player("C01", 5)
ps["gold"] = 1234
ps["equipped"]["weapon"] = dict(w)
ps["bag"].append(dict(bad))
ps["char_id"] = "selftest_char"
path = storage.save(ps)
data = storage.load("selftest_char")
p6 = make_player("C01", 1)
storage.apply(p6, data)
recalc(p6)
check("存档读回等级", p6["level"] == 5, "level=%s" % p6["level"])
check("存档读回金币", p6["gold"] == 1234)
check("存档读回装备", p6["equipped"]["weapon"]["name"] == "测试长兵")
check("存档读回背包", len(p6["bag"]) == 1)
import os as _os
_os.remove(path)

# ---------------------------------------------------------------- 16. 连败暂停
pp2 = make_player("C01", 1)
# 用必死场景：Lv1 直接打 6-3 的蛟魔王
camp3 = Campaign(pp2, Rng(1), mode="farm", stage="6-3")
camp3.run(3000)
check("连续死亡 5 次触发暂停", camp3.paused is True,
      "死亡 %d 次 streak %d" % (camp3.deaths, camp3.death_streak))
t_before = camp3.t
camp3.run(t_before + 600)
check("暂停后不再推进", camp3.t == t_before, "%s -> %s" % (t_before, camp3.t))
camp3.resume()
check("resume 清零连败", camp3.paused is False and camp3.death_streak == 0)

# 通关要重置连败
camp4 = Campaign(make_player("C01", 20), Rng(2), mode="farm", stage="1-1")
camp4.death_streak = 3
camp4.on_stage_clear()
check("通关重置连败", camp4.death_streak == 0)

# ---------------------------------------------------------------- 17. 进阶与 lineage
pa = make_player("C01", 10)
pa["gold"] = 50000
pa["materials"] = {gear.MAT_ADVANCE: 10}
old_item = {"instance_id": "i_old", "name": "测试长兵", "slot": "weapon",
            "quality": 1, "quality_name": "精良", "main": "atk", "value": 60,
            "ilvl": 10, "plus": 3}
new_item = gear.advance(pa, old_item)
check("进阶提升物品等级", new_item["ilvl"] == 14, "ilvl=%s" % new_item["ilvl"])
check("进阶提升品质", new_item["quality"] == 2)
check("进阶保留强化等级", new_item["plus"] == 3)
check("进阶记录源实例", new_item["source_instance_id"] == "i_old")
check("进阶记录旧强化", new_item["previous_strengthen"] == 3)
check("进阶代数 +1", new_item["generation"] == 2)
check("旧实例标记 superseded", old_item["superseded_by"] == new_item["instance_id"])
check("消耗进阶材料", pa["materials"][gear.MAT_ADVANCE] == 10 - gear.ADVANCE_MATERIALS)
check("传说品质不再进阶",
      gear.can_advance(pa, dict(old_item, quality=4)) is False)

# ---------------------------------------------------------------- 18. 副本
from zdzm.core.progress import auto_learn
from zdzm.data import instances as I
from zdzm.data import artifacts as A

check("有龙宫与牛魔两个副本", set(I.INSTANCES) == {"dragon_old", "ox"})
check("龙宫是单人本", I.get("dragon_old")["type"] == "solo")
check("牛魔是团队本", I.get("ox")["type"] == "raid")
check("龙宫首通给法宝",
      I.get("dragon_old")["first_clear_reward"] == "ART_HG_TIDE_SEAL")
check("牛魔首通给套装",
      I.get("ox")["first_clear_reward"] == "EQ_HG_SET_GUARD_T1")
check("副本不参与 push 链",
      not any(k in Z.STAGES for k in I.INSTANCES))

# 副本通关发奖
pc = make_player("C01", 15)
pc["char_id"] = "x"
camp5 = Campaign(pc, Rng(1), mode="push")
camp5.enter_instance("dragon_old")
check("进入副本后模式为 instance", camp5.mode == "instance")
camp5.on_instance_clear()
check("龙宫通关获得法宝", "ART_HG_TIDE_SEAL" in pc.get("artifacts_owned", []))
check("法宝自动装备", pc.get("artifact") == "ART_HG_TIDE_SEAL")
check("副本通关后回城", camp5.mode == "town")

# 套装加成
ps1 = make_player("C01", 10)
ps2 = make_player("C01", 10)
for slot in ("weapon", "body"):
    ps2["equipped"][slot] = {
        "instance_id": "s_" + slot, "name": "镇守", "slot": slot,
        "quality": 3, "quality_name": "史诗", "main": "def", "value": 0,
        "ilvl": 20, "set_key": "EQ_HG_SET_GUARD_T1"}
recalc(ps2)
check("2 件套给防御加成", ps2["def"] > ps1["def"], "%d vs %d" % (ps2["def"], ps1["def"]))

ps3 = make_player("C01", 10)
for slot in ("weapon", "helm", "body", "boots"):
    ps3["equipped"][slot] = {
        "instance_id": "s2_" + slot, "name": "镇守", "slot": slot,
        "quality": 3, "quality_name": "史诗", "main": "def", "value": 0,
        "ilvl": 20, "set_key": "EQ_HG_SET_GUARD_T1"}
recalc(ps3)
check("4 件套比 2 件套更强", ps3["max_hp"] > ps2["max_hp"],
      "%d vs %d" % (ps3["max_hp"], ps2["max_hp"]))

# 法宝效果（终端版偏离设计，见 data/artifacts.py 顶部说明）
pt1 = make_player("C01", 10)
pt2 = make_player("C01", 10)
pt2["artifact"] = "ART_HG_TIDE_SEAL"
check("定潮玄印：生势 +15%", A.resource_gain_mult(pt2) == 1.15)
check("定潮玄印：洞明阈值 -5", A.realm_threshold_delta(pt2) == -5)
check("无装备法时生势倍率为 1", A.resource_gain_mult(pt1) == 1.0)

pf = make_player("C01", 10)
pf["artifact"] = "ART_HG_FLAME_CORE"
check("熔脉劫核：洞明伤害 +12%", A.realm_damage_mult(pf) == 1.12)
check("熔脉劫核：耗势返还 5", A.cost_refund(pf) == 5)

# 定潮玄印在战斗里把洞明阈值降到 75
pb = make_player("C01", 20)
auto_learn(pb)
pb["char_id"] = "x"
pb["artifact"] = "ART_HG_TIDE_SEAL"
recalc(pb)
pb["resource"] = 75
camp7 = Campaign(pb, Rng(1), mode="farm", stage="5-3")
camp7.battle._check_realm()
check("战势 75 即可进入洞明", pb["realm"] is True, "realm=%s" % pb["realm"])

# 熔火核吃到耗势返还
pc2 = make_player("C01", 20)
auto_learn(pc2)
pc2["char_id"] = "x"
pc2["artifact"] = "ART_HG_FLAME_CORE"
recalc(pc2)
pc2["skills"]["C01_A02"] = 1
pc2["resource"] = 100
camp8 = Campaign(pc2, Rng(1), mode="farm", stage="5-3")
camp8.battle._resolve_skill(pc2, "C01_A02")
check("耗势 30 返还 5 → 净消耗 25", pc2["resource"] == 75,
      "resource=%s" % pc2["resource"])

# ---------------------------------------------------------------- 19. 破韧
from zdzm.data import monsters as MS2
from zdzm.data.skills import SKILLS as SK2

check("技能带破韧系数", all(SK2[k].get("poise") is not None for k in SK2))
check("龙王韧性阈值 = 11（策划案）", MS2.POISE_BY_KEY["long_wang"] == 11)
check("牛魔人形阈值 = 20（策划案）", MS2.POISE_BY_KEY["niu_ren"] == 20)
check("白牛阈值 = 24（策划案）", MS2.POISE_BY_KEY["niu_bai"] == 24)
check("破韧窗口 4 秒", MS2.BROKEN_DURATION == 4.0)

pk = make_player("C01", 20)
auto_learn(pk)
pk["char_id"] = "x"
camp9 = Campaign(pk, Rng(3), mode="farm", stage="1-1")
mk2 = camp9.battle.monster
mk2["poise"] = 2.0
camp9.battle._apply_poise(pk, mk2, 3.0, 100)
check("破韧：韧性归零即触发", mk2.get("broken_until", 0) > 0,
      "broken_until=%s" % mk2.get("broken_until"))
check("破韧后韧性重置", mk2["poise"] == mk2["poise_max"])

# ---------------------------------------------------------------- 20. 六个被动
from zdzm.data.skills import PASSIVES as PS2

check("P02 有战势档位加成", PS2["C01_P02"]["dmg_mid"][0] == 2)
check("P03 标注了终端改造", "位移" in PS2["C01_P03"].get("deviation", ""))
check("P04 对显妄加破韧", PS2["C01_P04"]["break_bonus"][0] == 8)
check("P06 破隙有伤害与返还", PS2["C01_P06"]["dmg"][0] == 6 and PS2["C01_P06"]["refund"][0] == 2)
check("P07 标注了终端改造", "位移" in PS2["C01_P07"].get("deviation", ""))
check("P08 标注了队友改自身", "队友" in PS2["C01_P08"].get("deviation", ""))

# P02 实际生效：战势 40-79 时伤害更高
pm1 = make_player("C01", 20)
auto_learn(pm1)
pm1["char_id"] = "x"
pm1["passives"]["C01_P02"] = 5
pm1["resource"] = 60
campA = Campaign(pm1, Rng(1), mode="farm", stage="1-1")
m1 = campA.battle.monster
mult_mid = campA.battle._passive_dmg_mult(pm1, m1)
pm1["resource"] = 0
mult_none = campA.battle._passive_dmg_mult(pm1, m1)
check("P02 战势 40-79 有伤害加成", mult_mid > mult_none,
      "%.2f vs %.2f" % (mult_mid, mult_none))

# P03 攻速窗口
ph = make_player("C01", 20)
auto_learn(ph)
ph["char_id"] = "x"
ph["passives"]["C01_P03"] = 5
campB = Campaign(ph, Rng(1), mode="farm", stage="1-1")
h0 = campB.battle._haste_mult(ph)
ph["p03_until"] = 100.0
campB.battle.tl.now = 1.0
h1 = campB.battle._haste_mult(ph)
check("P03 窗口内攻速提升", h1 > h0, "%.2f vs %.2f" % (h1, h0))

# P08 显妄降防增强
pd = make_player("C01", 20)
auto_learn(pd)
pd["char_id"] = "x"
campC = Campaign(pd, Rng(1), mode="farm", stage="1-1")
mk = campC.battle.monster
pd["passives"]["C01_P08"] = 5
pd["skills"]["C01_A05"] = 5
pd["resource"] = 100
campC.battle._resolve_skill(pd, "C01_A05")
check("P08 让显妄降防更高", mk.get("def_down", 0) > 6,
      "def_down=%s" % mk.get("def_down"))

# ---------------------------------------------------------------- 21. 技能加点与装配
from zdzm.core.progress import auto_spend, upgrade_skill, set_loadout, auto_learn

pl = make_player("C01", 20)
auto_learn(pl)
check("只自动学 Lv1 初始技能", list(pl["skills"].keys()) == ["C01_A01"],
      str(list(pl["skills"])))
check("条件满足但未学的技能不算已学",
      "C01_A02" not in pl["skills"])
check("解锁免费，点数未被消耗", pl["skill_points"] == 19,
      "points=%d" % pl["skill_points"])
from zdzm.core.progress import learn_active as _LA
for _k in list(SKILLS):
    _LA(pl, _k)
check("学满后装配 5 个主动", len(pl["loadout"]) == 5, str(pl["loadout"]))

# 手动升级
before = pl["skills"].get("C01_A01", 1)
n = upgrade_skill(pl, "C01_A01", 4)
check("手动加点生效", pl["skills"]["C01_A01"] > before, "now %d" % pl["skills"]["C01_A01"])

# 学习是玩家动作：条件满足才可学、且免费
from zdzm.core.progress import learn_active as _LA, learn_passive as _LP0
pts_before = pl["skill_points"]
ok_learn = _LP0(pl, "C01_P01")
check("条件满足可学习", ok_learn is True)
check("学习消耗 1 点", pl["skill_points"] == pts_before - 1,
      "%d → %d" % (pts_before, pl["skill_points"]))

# 装配上限 5
set_loadout(pl, ["C01_A01", "C01_A02", "C01_A03", "C01_A04", "C01_A05", "C01_A06"])
check("装配最多 5 个", len(pl["loadout"]) == 5, str(pl["loadout"]))

# 没学过的技能不能装配
set_loadout(pl, ["C01_A06", "C01_A07"])
check("未学技能不能装配", all(k in pl["skills"] for k in pl["loadout"]),
      str(pl["loadout"]))

# AI 只用装配的技能
pq = make_player("C01", 20)
auto_learn(pq)
pq["char_id"] = "x"
auto_spend(pq)
pq["resource"] = 100
pq["realm"] = True
set_loadout(pq, ["C01_A01"])
campD = Campaign(pq, Rng(1), mode="farm", stage="1-1")
picked = []
for _ in range(20):
    pq["cd"] = {}
    k = campD.battle.ai.choose(campD.battle, pq)
    picked.append(k)
check("AI 不会选未装配的技能",
      all(k in ("C01_A01", None) for k in picked), str(set(picked)))

# 一键加点
pa2 = make_player("C01", 30)
auto_learn(pa2)
for _k in list(SKILLS):
    _LA(pa2, _k)
from zdzm.core.progress import learn_passive as _LP
for _k in list(PASSIVES):
    _LP(pa2, _k)
pts = pa2["skill_points"]
auto_spend(pa2)
check("一键加点会消耗点数", pa2["skill_points"] < pts, "剩 %d（原 %d）" % (pa2["skill_points"], pts))
check("一键加点后技能数变多",
      sum(pa2["skills"].values()) + sum(pa2["passives"].values()) > 8)

# ---------------------------------------------------------------- 22. 收集
from zdzm.core import collect as COLX
from zdzm.data import collect as COLD

check("花果山九项收集", len(COLD.COLLECTIONS) == 9)
check("前 3 项不依赖隐藏副本（龙宫/牛魔）",
      all(COLD.BY_KEY[k]["type"] not in ("instance_clear", "instance_count", "artifact")
          for k in ("C_HG_01", "C_HG_02", "C_HG_03")))

pc3 = make_player("C01", 1)
pc3["char_id"] = "x"
pc3["kill_region"] = {"MOUNTAIN": 50}
got = COLX.check(pc3)
check("击杀达标解锁收集", any(c["key"] == "C_HG_01" for c in got),
      str([c["key"] for c in got]))
check("解锁收集给称号", len(pc3.get("titles") or []) >= 1)

pc4 = make_player("C01", 1)
pc4["char_id"] = "x"
pc4["instance_counts"] = {"dragon_old": 3}
got4 = COLX.check(pc4)
check("副本次数达标解锁", any(c["key"] == "C_HG_05" for c in got4))

# 达标后不重复解锁
got5 = COLX.check(pc3)
check("已完成不重复解锁", len(got5) == 0)

# ---------------------------------------------------------------- 汇总
print()
print("通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项：" + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
