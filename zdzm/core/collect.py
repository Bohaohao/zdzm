# -*- coding: utf-8 -*-
"""收集进度判定。"""
from zdzm.data import collect as COL


def _state(p):
    return p.setdefault("collect", {})


def bump(p, key, n=1):
    """累加某个计数项。"""
    st = _state(p)
    st[key] = st.get(key, 0) + n
    return st[key]


def value_of(p, c):
    """当前进度值。"""
    st = _state(p)
    t = c["type"]
    if t == "kill_region":
        return (p.get("kill_region") or {}).get(c["region"], 0)
    if t == "region_clear":
        return (p.get("region_clears") or {}).get(c["region"], 0)
    if t == "stage_clear":
        return 1 if c["stage"] in p.get("cleared", []) else 0
    if t == "instance_clear":
        return 1 if c["instance"] in p.get("instance_clears", []) else 0
    if t == "instance_count":
        return (p.get("instance_counts") or {}).get(c["instance"], 0)
    if t == "artifact":
        return 1 if c["artifact"] in (p.get("artifacts_owned") or []) else 0
    if t == "boss_kill":
        return (p.get("boss_kills") or {}).get(c["boss"], 0)
    return st.get(c["key"], 0)


def progress(p, c):
    v = min(value_of(p, c), c["need"])
    return v, c["need"]


def check(p):
    """返回本次新解锁的收集项。"""
    done = set(p.get("collect_done") or [])
    got = []
    for c in COL.all_of():
        if c["key"] in done:
            continue
        v, need = progress(p, c)
        if v >= need:
            done.add(c["key"])
            got.append(c)
    if got:
        p["collect_done"] = sorted(done)
        titles = p.setdefault("titles", [])
        for c in got:
            if c["reward"] not in titles:
                titles.append(c["reward"])
    return got


def summary(p):
    out = []
    for c in COL.all_of():
        v, need = progress(p, c)
        out.append((c, v, need, c["key"] in set(p.get("collect_done") or [])))
    return out
