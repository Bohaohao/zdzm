# -*- coding: utf-8 -*-
"""战斗循环：事件堆驱动，产出事件列表。

M2 覆盖：普攻连段、8 个主动技能、耗势与生势、洞明追加、
        P01 势行不滞、P05 守意归元、技能 CD 与前摇。
"""
from zdzm.core.timeline import Timeline
from zdzm.core import state as S
from zdzm.core.progress import auto_learn
from zdzm.data import classes as C
from zdzm.data.skills import SKILLS, PASSIVES
from zdzm.data import artifacts as A
from zdzm.data import monsters as MS

DEF_K = 400.0      # 防御曲线常数：def/(def+K) 为减伤比例，上限 75%
DECAY_INTERVAL = 0.5
RESPAWN_DELAY = 0.4
HEAL_INTERVAL = 5.0      # 通用被动「回春」每 5 秒结算一次


def _res_gen(p):
    """归元：资源获取倍率（破妄 = 生势）。"""
    from zdzm.data import common_passives as CP
    return CP.multipliers(p)["res_gen"]


class Battle:
    def __init__(self, player, spawn_fn, rng, ai=None, on_kill=None,
                 start_time=0.0, on_event=None):
        self.player = player
        self.spawn_fn = spawn_fn
        self.rng = rng
        self.ai = ai
        self.on_kill = on_kill
        self.on_event = on_event
        self.tl = Timeline()
        self.tl.now = start_time
        self.monster = None
        self.events = []
        self.kills = 0
        self.over = False
        self.cleared = False

        if not player["skills"]:
            auto_learn(player)

        self._spawn()
        self.tl.push(start_time, "ready", actor=player["id"])
        self.tl.push(start_time, "decay", actor=player["id"])

    # ---------------------------------------------------------------- 事件产出
    def _emit(self, kind, **kw):
        ev = {"t": round(self.tl.now, 3), "kind": kind}
        ev.update(kw)
        self.events.append(ev)
        if self.on_event:
            self.on_event(ev)
        return ev

    # ---------------------------------------------------------------- 主循环
    def run(self, until):
        while not self.tl.empty() and not self.over:
            if self.tl.peek_time() > until:
                break
            kind, kw = self.tl.pop()
            getattr(self, "_on_" + kind)(**kw)
        # 正常跑满则推进到 until；清关/死亡时保留真实结束时刻
        if not self.over:
            self.tl.now = max(self.tl.now, until)
        return self.events

    # ---------------------------------------------------------------- 事件分发
    def _on_ready(self, actor):
        a = self._actor(actor)
        if a is None or not a["alive"]:
            return
        if S.is_player(a):
            self._player_act(a)
        else:
            self._monster_act(a)

    def _on_cast_done(self, actor):
        p = self.player
        c = p["casting"]
        p["casting"] = None
        if not c or not p["alive"]:
            return
        m = self.monster
        if m is None or not m["alive"]:
            self._schedule(p)
            return
        self._resolve_skill(p, c["skill"])
        if not self.over:
            self._schedule(p)

    def _on_decay(self, actor):
        p = self.player
        cls = C.CLASSES[p["cls"]]
        if p["alive"] and p["resource"] > 0:
            idle = self.tl.now - p["last_valid_attack_at"]
            if idle >= self._decay_after(p):
                loss = min(p["resource"], cls["decay_per_sec"] * DECAY_INTERVAL)
                before = p["resource"]
                p["resource"] -= loss
                self._emit("decay", src=p["id"], loss=loss,
                           before=before, resource=p["resource"])
                self._check_realm()
        if not self.over:
            self.tl.push_delay(DECAY_INTERVAL, "decay", actor=p["id"])

    def _on_spawn(self):
        if self.over:
            return
        self._spawn()
        if self.monster is None:
            return
        self.tl.push(self.tl.now, "ready", actor=self.monster["id"])

    # ---------------------------------------------------------------- 玩家行动
    def _player_act(self, p):
        now = self.tl.now
        if p["casting"]:
            return
        m = self.monster
        if m is None or not m["alive"]:
            self.tl.push(now + 0.2, "ready", actor=p["id"])
            return

        # 回春：每 5 秒回一次最大生命百分比
        from zdzm.data import common_passives as CP
        heal_pct = CP.multipliers(p)["heal"]
        if heal_pct > 0:
            due = p.get("next_heal_at", 0)
            if now >= due:
                p["next_heal_at"] = now + HEAL_INTERVAL
                if p["hp"] < p["max_hp"]:
                    amt = int(p["max_hp"] * heal_pct)
                    if amt > 0:
                        p["hp"] = min(p["max_hp"], p["hp"] + amt)
                        self._emit("heal", src=p["id"], value=amt,
                                   hp_after=p["hp"], max_hp=p["max_hp"])

        key = self.ai.choose(self, p) if self.ai else None
        if key:
            self._start_skill(p, key)
        else:
            self._do_normal(p)

    def _start_skill(self, p, key):
        sk = SKILLS[key]
        now = self.tl.now
        if sk["cast"] > 0:
            p["casting"] = {"skill": key, "done_at": now + sk["cast"]}
            self.tl.push(now + sk["cast"], "cast_done", actor=p["id"])
            self._emit("cast_start", src=p["id"], key=key, name=sk["name"],
                       cast=sk["cast"])
        else:
            self._resolve_skill(p, key)
            if not self.over:
                self._schedule(p)

    def _do_normal(self, p):
        cls = C.CLASSES[p["cls"]]
        now = self.tl.now
        m = self.monster

        if now > p["combo_expire_at"]:
            p["combo"] = 0
        seg = p["combo"]

        dmg, crit = self._deal_damage(p, m)
        gain = cls["combo_gain"][seg] * A.resource_gain_mult(p) * _res_gen(p)
        before = p["resource"]
        gain = int(round(gain))
        p["resource"] = min(p.get("resource_max", cls["resource_max"]), before + gain)
        overflow = before + gain - p["resource"]

        p["combo"] = (seg + 1) % 3
        p["combo_expire_at"] = now + cls["combo_window"]
        p["last_valid_attack_at"] = now

        self._apply_poise(p, m, 1.0, dmg)

        self._emit("attack", src=p["id"], dst=m["id"], name=m["name"],
                   value=dmg, crit=crit, hp_after=m["hp"], max_hp=m["max_hp"],
                   combo=seg + 1, gain=gain, overflow=overflow,
                   resource=p["resource"])

        self._check_realm()
        self._schedule(p)
        if m["hp"] <= 0:
            self._kill(m)

    # ---------------------------------------------------------------- 技能结算
    def _resolve_skill(self, p, key):
        sk = SKILLS[key]
        lv = p["skills"].get(key, 0)
        if lv <= 0:
            return
        cls = C.CLASSES[p["cls"]]
        m = self.monster
        now = self.tl.now

        cost = sk["cost"]
        if cost > p["resource"]:
            return
        if cost:
            p["resource"] -= cost
            self._apply_p05(p, cost)
            refund = A.cost_refund(p)
            if refund:
                p["resource"] = min(p.get("resource_max", cls["resource_max"]), p["resource"] + refund)
            self._emit("spend", src=p["id"], cost=cost, refund=refund,
                       resource=p["resource"])

        mult = sk["mult"][lv - 1]
        total = 0
        crits = 0
        for _ in range(sk["hits"]):
            if m["hp"] <= 0:
                break
            d, c = self._deal_damage(p, m, mult)
            total += d
            if c:
                crits += 1

        # 洞明追加（回响不独立暴击）
        add_dmg = 0
        if p["realm"] and sk.get("realm_add"):
            add_dmg, _ = self._deal_damage(p, m, sk["realm_add"][lv - 1], can_crit=False)
            total += add_dmg

        # 生势
        gain = sk["gain"][lv - 1]
        if sk["hits"] > 1:
            gain = gain * sk["hits"] + sk.get("gain_bonus", [0] * 5)[lv - 1]
        gain = gain * A.resource_gain_mult(p) * _res_gen(p)
        if p["p01_bonus"] and now < p["p01_until"]:
            gain += p["p01_bonus"]
            p["p01_bonus"] = 0
        overflow = 0
        if gain:
            before = p["resource"]
            gain = int(round(gain))
            p["resource"] = min(p.get("resource_max", cls["resource_max"]), before + gain)
            overflow = before + gain - p["resource"]

        # P06 破隙连裁：洞明耗势留下破隙，下一个不同耗势消耗
        lv6 = p["passives"].get("C01_P06", 0)
        if lv6 > 0 and cost > 0 and p["realm"]:
            if p.get("p06_last") and p["p06_last"] != key and now < p.get("p06_until", 0):
                ps6 = PASSIVES["C01_P06"]
                bonus = total * ps6["dmg"][lv6 - 1] / 100.0
                total = int(total + bonus)
                refund6 = ps6["refund"][lv6 - 1]
                p["resource"] = min(p.get("resource_max", cls["resource_max"]), p["resource"] + refund6)
                if lv6 >= 5:
                    p["cd"]["C01_A06"] = max(now, p["cd"].get("C01_A06", 0) - ps6["mastery_cd"])
                p["p06_last"] = None
                p["p06_until"] = 0
                self._emit("gap", src=p["id"], name="破隙", bonus=int(bonus), refund=refund6)
            else:
                p["p06_last"] = key
                p["p06_until"] = now + PASSIVES["C01_P06"]["window"]

        # P03/P07：A04/A07 之后的窗口
        if key in ("C01_A04", "C01_A07"):
            if p["passives"].get("C01_P03"):
                p["p03_until"] = now + PASSIVES["C01_P03"]["window"]
            lv7 = p["passives"].get("C01_P07", 0)
            if lv7 > 0:
                extra = PASSIVES["C01_P07"]["dr"][lv7 - 1]
                cur = p.get("dr_buff")
                base_v = cur["value"] if cur and now < cur["until"] else 0
                p["dr_buff"] = {"until": now + PASSIVES["C01_P07"]["window"],
                                "value": min(60, base_v + extra)}

        # P01：耗势命中后挂上加值
        if cost > 0 and p["passives"].get("C01_P01"):
            plv = p["passives"]["C01_P01"]
            ps = PASSIVES["C01_P01"]
            p["p01_bonus"] = ps["extra_gain"][plv - 1]
            p["p01_until"] = now + ps["window"]

        # 自身减伤
        if sk.get("self_dr"):
            p["dr_buff"] = {"until": now + sk["dr_dur"],
                            "value": sk["self_dr"] * 100}

        # 显妄：降低目标物防
        if sk.get("debuff_def"):
            ddef = sk["debuff_def"][lv - 1]
            ddur = sk["debuff_dur"][lv - 1]
            lv8 = p["passives"].get("C01_P08", 0)
            if lv8 > 0:
                ddef += PASSIVES["C01_P08"]["def_extra"][lv8 - 1]
                ddur += PASSIVES["C01_P08"]["dur_extra"][lv8 - 1]
            m["def_down"] = ddef
            m["def_down_until"] = now + ddur

        self._apply_poise(p, m, sk.get("poise", 0) * sk["hits"], total)

        p["cd"][key] = now + sk["cd"][lv - 1]
        p["last_valid_attack_at"] = now

        self._emit("skill", src=p["id"], dst=m["id"], key=key, name=sk["name"],
                   value=total, crits=crits, hits=sk["hits"],
                   cost=cost, gain=gain, overflow=overflow,
                   add=add_dmg, realm=p["realm"],
                   hp_after=m["hp"], max_hp=m["max_hp"],
                   resource=p["resource"])

        self._check_realm()
        if m["hp"] <= 0:
            self._kill(m)

    def _passive_dmg_mult(self, p, dst):
        mult = 1.0
        # P02 锋随势涨
        lv2 = p["passives"].get("C01_P02", 0)
        if lv2 > 0:
            ps2 = PASSIVES["C01_P02"]
            if p["realm"]:
                mult *= 1 + ps2["dmg_realm"][lv2 - 1] / 100.0
            elif 40 <= p["resource"] <= 79:
                mult *= 1 + ps2["dmg_mid"][lv2 - 1] / 100.0
        # P08 精通：对显妄目标伤害 +10%
        lv8 = p["passives"].get("C01_P08", 0)
        if lv8 >= 5 and self.tl.now < dst.get("def_down_until", 0):
            mult *= 1 + PASSIVES["C01_P08"]["mastery_dmg"] / 100.0
        return mult

    def _apply_poise(self, p, m, amount, dmg):
        """扣韧性，归零则进入破韧窗口。"""
        if amount <= 0 or m.get("poise_max", 0) <= 0:
            return
        if self.tl.now < m.get("broken_until", 0):
            return
        # P04 妄痕可见：对显妄目标破韧提高
        lv4 = p["passives"].get("C01_P04", 0)
        if lv4 > 0 and self.tl.now < m.get("def_down_until", 0):
            amount *= 1 + PASSIVES["C01_P04"]["break_bonus"][lv4 - 1] / 100.0
        m["poise"] = m.get("poise", 0) - amount
        if m["poise"] <= 0:
            m["poise"] = m.get("poise_max", 0)
            m["broken_until"] = self.tl.now + MS.BROKEN_DURATION
            self._emit("break", src=p["id"], dst=m["id"], name=m["name"],
                       duration=MS.BROKEN_DURATION)

    # ---------------------------------------------------------------- 被动
    def _apply_p05(self, p, cost):
        lv = p["passives"].get("C01_P05", 0)
        if lv <= 0:
            return
        ps = PASSIVES["C01_P05"]
        now = self.tl.now
        p["p05_meter"] += cost
        if p["p05_meter"] < ps["cost_threshold"]:
            return
        if now < p["p05_icd_until"]:
            return
        p["p05_meter"] -= ps["cost_threshold"]
        heal = int(round(p["max_hp"] * ps["heal_pct"][lv - 1]))
        before = p["hp"]
        p["hp"] = min(p["max_hp"], p["hp"] + heal)
        p["dr_buff"] = {"until": now + ps["dr_dur"], "value": ps["dr"][lv - 1]}
        p["p05_icd_until"] = now + ps["icd"]
        self._emit("p05", src=p["id"], heal=p["hp"] - before,
                   hp=p["hp"], max_hp=p["max_hp"], dr=ps["dr"][lv - 1])

    def _decay_after(self, p):
        """P01 五级精通：衰减等待由 4 秒提高到 6 秒。"""
        if p["passives"].get("C01_P01", 0) >= 5:
            return 6.0
        return C.CLASSES[p["cls"]]["decay_after"]

    # ---------------------------------------------------------------- 怪物
    def _monster_act(self, m):
        p = self.player
        if not p["alive"]:
            return
        dmg, crit = self._deal_damage(m, p)
        self._emit("hurt", src=m["id"], dst=p["id"], name=m["name"],
                   value=dmg, crit=crit, hp_after=p["hp"], max_hp=p["max_hp"])

        if p["hp"] <= 0:
            p["alive"] = False
            self._emit("death", actor=p["id"], name=p["name"], by=m["name"])
            self.over = True
            return

        if not self.over:
            self.tl.push(self.tl.now + 1.0 / m["aps"], "ready", actor=m["id"])

    # ---------------------------------------------------------------- 结算
    def _deal_damage(self, src, dst, mult=1.0, can_crit=True):
        now = self.tl.now
        raw = src["atk"] * mult * self.rng.uniform(0.9, 1.1)

        # 防御按比例减伤，避免高防时低级怪完全打不动
        d = dst["def"]
        if S.is_player(src) and dst.get("def_down"):
            if now < dst.get("def_down_until", 0):
                d *= (1 - dst["def_down"] / 100.0)
        reduction = d / (d + DEF_K) if d > 0 else 0.0
        raw *= (1.0 - min(reduction, 0.75))

        if S.is_player(src) and src.get("realm"):
            raw *= A.realm_damage_mult(src)
        if S.is_player(src):
            raw *= self._passive_dmg_mult(src, dst)

        # 目标处于破韧窗口时受伤加成
        if not S.is_player(dst) and now < dst.get("broken_until", 0):
            raw *= MS.BROKEN_TAKEN_MULT

        crit = can_crit and self.rng.chance(src["crit"])
        if crit:
            raw *= src["crit_mult"]
        dmg = max(1, int(round(raw)))

        if S.is_player(dst) and dst.get("dr_buff"):
            if now < dst["dr_buff"]["until"]:
                dmg = max(1, int(round(dmg * (1 - dst["dr_buff"]["value"] / 100.0))))

        dst["hp"] = max(0, dst["hp"] - dmg)
        if S.is_player(src):
            src["damage_done"] += dmg
            src["hits"] += 1
        return dmg, crit

    def _kill(self, m):
        m["alive"] = False
        self.kills += 1
        self._emit("kill", actor=m["id"], name=m["name"], xp=m.get("xp", 0),
                   gold=m.get("gold", (0, 0)), tier=m.get("tier", "COMMON"))
        if self.on_kill:
            self.on_kill(m)
        if not self.over:
            self.tl.push_delay(RESPAWN_DELAY, "spawn")

    def _check_realm(self):
        p = self.player
        cls = C.CLASSES[p["cls"]]
        want = p["resource"] >= p.get("realm_threshold", cls["realm_threshold"]) + A.realm_threshold_delta(p)
        if want and not p["realm"]:
            p["realm"] = True
            self._emit("realm", src=p["id"], state="enter",
                       name=cls["realm_name"], resource=p["resource"])
        elif not want and p["realm"]:
            p["realm"] = False
            self._emit("realm", src=p["id"], state="exit",
                       name=cls["realm_name"], resource=p["resource"])

    # ---------------------------------------------------------------- 工具
    def _schedule(self, p):
        cls = C.CLASSES[p["cls"]]
        aps = cls["aps"] * self._haste_mult(p)
        self.tl.push(self.tl.now + 1.0 / aps, "ready", actor=p["id"])

    def _haste_mult(self, p):
        lv = p["passives"].get("C01_P03", 0)
        if lv > 0 and self.tl.now < p.get("p03_until", 0):
            return 1 + PASSIVES["C01_P03"]["haste"][lv - 1] / 100.0
        return 1.0

    def _actor(self, aid):
        if self.player["id"] == aid:
            return self.player
        if self.monster and self.monster["id"] == aid:
            return self.monster
        return None

    def _spawn(self):
        m = self.spawn_fn()
        if m is None:
            self.monster = None
            self.over = True
            self.cleared = True
            return
        self.monster = m
        self._emit("spawn", actor=m["id"], name=m["name"], hp=m["max_hp"],
                   tier=m.get("tier", "COMMON"), level=m.get("level", 1))
