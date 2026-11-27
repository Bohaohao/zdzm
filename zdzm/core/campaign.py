# -*- coding: utf-8 -*-
"""关卡调度：farm / push 两种挂机模式。

push 规则（docs/DESIGN.md §6.3）：
  1. 从当前关逐关推进
  2. 清完全部波次才算通过
  3. 死亡 = 本次挑战失败，回营地，重试本关
  4. 不做战力评估、不自动降级
  5. 到篇章最后一关转为 farm，不跨篇章
"""
from zdzm.core.combat import Battle
from zdzm.core.ai import Ai
from zdzm.core import state as S
from zdzm.core import drop
from zdzm.core import gear
from zdzm.core import collect as COL
from zdzm.core.rng import Rng
from zdzm.core.progress import auto_learn
from zdzm.data import zones as Z
from zdzm.data import instances as I
from zdzm.data import artifacts as A
from zdzm.data import monsters as MS
from zdzm.data import classes as C

MAX_DEATH_STREAK = 5
DEATH_GOLD_LOSS = 0.05
DEATH_XP_LOSS = 0.05
RETRY_DELAY = 1.0


class Campaign:
    def __init__(self, player, rng, mode="push", stage=None, log_kill=None, say=None,
                 on_event=None):
        self.p = player
        self.rng = rng
        self.mode = mode
        self.stage = stage or Z.first_key()
        self.instance = None
        self.waves = []
        self.wave = 0
        self.idx = 0
        self.cleared = []
        self.deaths = 0
        self.death_streak = 0
        self.paused = False
        self.battle = None
        self.loot = []
        self.receipts = []
        self.log_kill = log_kill
        self.say = say or (lambda kind, **kw: None)
        self.on_event = on_event
        self.t = 0.0
        self.p.setdefault("pity", {})
        self.new_battle()

    # ---------------------------------------------------------------- 出怪
    def enter_region(self, region_key):
        """进入一个副本：从入口阶段打到该区域最后一个阶段，全部完成才算通关。"""
        stages = Z.region_stages(region_key)
        if not stages:
            return False
        self.region = region_key
        self.region_stages = stages
        self.region_idx = 0
        self.stage = stages[0]
        self.mode = "region"
        self.resume()
        self.new_battle()
        return True

    def farm_region(self, region_key):
        """循环刷一个副本：必须从入口开始，打完最后阶段才算一轮。"""
        stages = Z.region_stages(region_key)
        if not stages:
            return False
        self.region = region_key
        self.region_stages = stages
        self.region_idx = 0
        self.stage = stages[0]
        self.mode = "region_loop"
        self.resume()
        self.new_battle()
        return True

    def region_progress(self):
        """当前副本进度 (已完成阶段数, 总阶段数)。"""
        if self.mode != "region":
            return 0, 0
        return self.region_idx, len(self.region_stages or [])

    def enter_instance(self, key):
        """进入副本：不参与 push 链，必须手动进入。"""
        inst = I.get(key)
        if inst is None:
            return False
        self.mode = "instance"
        self.instance = key
        self.waves = []
        self.stage_names = []
        for st in inst["stages"]:
            self.waves.extend(st["waves"])
            self.stage_names.append(st["name"])
        self.wave = 0
        self.idx = 0
        self.t = self.battle.tl.now if self.battle else self.t
        self.new_battle()
        self.say("instance_enter", name=inst["name"], level=inst["level"])
        return True

    def spawn(self):
        if self.mode == "instance":
            inst = I.get(self.instance)
            while self.wave < len(self.waves):
                w = self.waves[self.wave]
                if self.idx < len(w):
                    key = w[self.idx]
                    self.idx += 1
                    return MS.scale(key, inst["level"])
                self.wave += 1
                self.idx = 0
            return None
        st = Z.get(self.stage)
        while self.wave < len(st["waves"]):
            w = st["waves"][self.wave]
            if self.idx < len(w):
                key = w[self.idx]
                self.idx += 1
                return MS.scale(key, st["level"])
            self.wave += 1
            self.idx = 0
        return None

    def new_battle(self):
        self.wave = 0
        self.idx = 0
        self.battle = Battle(self.p, self.spawn, self.rng, ai=Ai(),
                             on_kill=self.on_kill, start_time=self.t,
                             on_event=self.on_event)

    # ---------------------------------------------------------------- 回调
    def _check_collect(self):
        got = COL.check(self.p)
        for c in got:
            self.say("collect", name=c["name"], reward=c["reward"])

    def on_kill(self, mon):
        # 收集计数
        reg = None
        if self.mode != "instance" and self.stage in Z.STAGES:
            reg = Z.STAGES[self.stage]["region"]
        if reg:
            kr = self.p.setdefault("kill_region", {})
            kr[reg] = kr.get(reg, 0) + 1
        if mon.get("tier") == "BOSS":
            bk = self.p.setdefault("boss_kills", {})
            bk[mon["key"]] = bk.get(mon["key"], 0) + 1
        self._check_collect()

        gold = self.rng.randint(*mon.get("gold", (0, 0)))
        self.p["gold"] = self.p.get("gold", 0) + gold
        self.gain_xp(mon.get("xp", 0))

        if self.mode == "instance":
            settlements, receipts = [], []      # 副本统一在通关时结算
        else:
            st = Z.get(self.stage)
            settlements, receipts = drop.roll(
                self.p, st["pool"], st["level"], self.rng)
        for s in settlements:
            self.loot.append(s)
        self.receipts.extend(receipts)

        # MAJOR/BOSS 掉进阶材料
        tier = mon.get("tier", "COMMON")
        mat = {"MAJOR": 1, "BOSS": 3}.get(tier, 0)
        if mat:
            mats = self.p.setdefault("materials", {})
            mats[gear.MAT_ADVANCE] = mats.get(gear.MAT_ADVANCE, 0) + mat

        for st in settlements:
            it = st["item"]
            ok, old = gear.try_equip(self.p, it)
            if ok:
                if old:
                    self.put_bag(old)
                st["equipped"] = True
            else:
                self.put_bag(it)

        if self.log_kill:
            self.log_kill(mon, gold, settlements)

    def save_now(self):
        """立即落盘。等级 / 技能 / 装备变动后调用。"""
        try:
            from zdzm.core import storage
            storage.save(self.p, self)
        except Exception:
            pass

    def put_bag(self, item):
        """背包上限 100 格；满了自动把新拾取的卖掉。"""
        p = self.p
        if len(p["bag"]) < gear.BAG_MAX:
            p["bag"].append(item)
            self.save_now()
            return
        g = gear.sell_price(item)
        p["gold"] = p.get("gold", 0) + g
        self.say("bag_full", name=item["name"], gold=g)
        self.save_now()

    def gain_xp(self, xp):
        before_level = self.p["level"]
        p = self.p
        p["xp"] = p.get("xp", 0) + xp
        while p["level"] < 60:
            need = C.xp_to_next(p["level"])
            if p["xp"] < need:
                break
            p["xp"] -= need
            p["level"] += 1
            self.say("levelup", level=p["level"])
            S.recalc(p)
            auto_learn(p)
            gear.auto_strengthen(p)
            gear.auto_advance(p)
            p["hp"] = p["max_hp"]
            p["mp"] = p.get("max_mp", 0)

        if p["level"] != before_level:
            self.save_now()

    # ---------------------------------------------------------------- 关卡推进
    def on_stage_clear(self):
        if self.mode == "instance":
            self.on_instance_clear()
            return
        self.cleared.append(self.stage)
        if self.mode in ("region", "region_loop"):
            cl = self.p.setdefault("cleared", [])
            if self.stage not in cl:
                cl.append(self.stage)
            self.death_streak = 0
            self._check_collect()
            self.region_idx += 1
            if self.region_idx >= len(self.region_stages):
                # 整个副本完成
                rk = self.region
                self.p.setdefault("region_clears", {})
                self.p["region_clears"][rk] = self.p["region_clears"].get(rk, 0) + 1
                self.save_now()
                self.say("region_clear", region=rk,
                         name=Z.REGIONS_BY_KEY[rk]["name"],
                         stages=len(self.region_stages))
                self.t = self.battle.tl.now + 1.5
                if self.mode == "region_loop":
                    # 循环：从头再来
                    self.region_idx = 0
                    self.stage = self.region_stages[0]
                    self.new_battle()
                    return
                self.mode = "town"
                return
            prev = self.stage
            self.stage = self.region_stages[self.region_idx]
            self.say("region_stage", prev=prev, cur=self.stage,
                     name=Z.get(self.stage)["name"])
            self.t = self.battle.tl.now + 1.0
            self.new_battle()
            return
        cl = self.p.setdefault("cleared", [])
        if self.stage not in cl:
            cl.append(self.stage)
        self.death_streak = 0          # 只有通关才重置连败
        self._check_collect()
        self.say("stage_clear", stage=self.stage, mode=self.mode)
        if self.mode == "farm":
            self.t = self.battle.tl.now + RETRY_DELAY
            self.new_battle()
            return
        nxt = Z.next_key(self.stage)
        self.t = self.battle.tl.now + RETRY_DELAY
        if nxt is None:
            self.mode = "farm"          # 篇章末尾，转循环
        else:
            self.stage = nxt
        self.new_battle()

    def on_instance_clear(self):
        key = self.instance
        inst = I.get(key)

        # encounter 级结算：通关时一次性 roll 通关池
        settlements, receipts = drop.roll(
            self.p, inst["pool"], inst["level"], self.rng)
        for s2 in settlements:
            it = s2["item"]
            ok, old = gear.try_equip(self.p, it)
            if ok:
                if old:
                    self.put_bag(old)
                s2["equipped"] = True
            else:
                self.put_bag(it)
        self.receipts.extend(receipts)
        self.loot.extend(settlements)
        if self.say:
            self.say("instance_loot", name=inst["name"], count=len(settlements))
        ic = self.p.setdefault("instance_counts", {})
        ic[key] = ic.get(key, 0) + 1
        first = key not in self.p.get("instance_clears", [])
        if first:
            self.p.setdefault("instance_clears", []).append(key)
            self.grant_first_clear(inst)
        self._check_collect()
        self.say("instance_clear", name=inst["name"], first=first,
                 reward=inst.get("first_clear_reward"))
        self.mode = "town"          # 出副本，等玩家决定下一步
        self.instance = None
        self.t = self.battle.tl.now + 2.0

    def grant_first_clear(self, inst):
        reward = inst.get("first_clear_reward")
        p = self.p
        if not reward:
            return
        if reward.startswith("ART_"):
            p.setdefault("artifacts_owned", [])
            if reward not in p["artifacts_owned"]:
                p["artifacts_owned"].append(reward)
            p["artifact"] = reward
            S.recalc(p)
            if p["hp"] > p["max_hp"]:
                p["hp"] = p["max_hp"]
            self.say("artifact_gain", key=reward, name=A.artifact(reward)["name"])
        elif reward.startswith("EQ_HG_SET"):
            sd = A.set_def(reward)
            slots = sd["pieces"]
            for slot in slots:
                it = {
                    "instance_id": "set_%s_%s" % (reward[-6:], slot),
                    "name": "镇守·" + gear.SLOT_NAMES.get(slot, slot),
                    "slot": slot if slot != "ring" else "ring",
                    "quality": 3, "quality_name": "史诗",
                    "main": "def" if slot != "weapon" else "atk",
                    "value": 55 if slot == "weapon" else 26,
                    "ilvl": 20,
                    "set_key": reward,
                }
                old = gear.equip(p, it, slot)
                if old:
                    self.put_bag(old)
            S.recalc(p)
            self.say("set_gain", key=reward, name=sd["name"])

    def on_death(self):
        self.deaths += 1
        self.death_streak += 1
        self.say("death", stage=self.stage, level=self.p["level"],
                 streak=self.death_streak)
        if self.death_streak >= MAX_DEATH_STREAK:
            self.paused = True
            self.say("paused", stage=self.stage, streak=self.death_streak)
            return
        p = self.p
        p["gold"] = int(p.get("gold", 0) * (1 - DEATH_GOLD_LOSS))
        p["xp"] = int(p.get("xp", 0) * (1 - DEATH_XP_LOSS))
        p["alive"] = True
        p["hp"] = p["max_hp"]
        p["resource"] = 0
        p["realm"] = False
        p["cd"] = {}
        p["casting"] = None
        p["p01_bonus"] = 0
        p["p05_meter"] = 0
        self.t = self.battle.tl.now + 3.0      # 回营地再战
        self.new_battle()

    # ---------------------------------------------------------------- 主循环
    def resume(self):
        """玩家手动恢复：清空连败、解除暂停。"""
        self.paused = False
        self.death_streak = 0

    def run(self, until):
        while self.t < until and not self.paused and self.mode != "town":
            self.battle.run(until)
            self.t = self.battle.tl.now
            if self.battle.cleared:
                self.on_stage_clear()
                continue
            if not self.p["alive"]:
                self.on_death()
                continue
            break
        return self.t
