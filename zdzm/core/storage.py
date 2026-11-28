# -*- coding: utf-8 -*-
"""存档：本地 JSON，字段为未来云存档预留。"""
import json
import os
import time
import uuid

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".zdzm")
SCHEMA = 1

PERSIST = [
    "char_id", "cls", "level", "xp", "gold",
    "nickname",                              # 玩家自定义昵称
    "skills", "passives", "skill_points",
    "common",                                # 通用被动等级
    "equipped", "bag", "pity",
    "chapter_unlocks", "route_completion",
    "region_clears", "collect_done", "titles",
    "stage", "mode",
]


def save_path(char_id):
    return os.path.join(SAVE_DIR, "%s.json" % char_id)


def ensure_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def serialize(p, campaign=None):
    d = {"schema_version": SCHEMA, "saved_at": time.time()}
    for k in PERSIST:
        if k in p:
            d[k] = p[k]
    if campaign is not None:
        d["stage"] = campaign.stage
        d["mode"] = campaign.mode
        d["cleared"] = campaign.cleared
        d["deaths"] = campaign.deaths
    return d


def save(p, campaign=None):
    ensure_dir()
    if not p.get("char_id"):
        p["char_id"] = uuid.uuid4().hex[:12]
    d = serialize(p, campaign)
    path = save_path(p["char_id"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def load(char_id):
    path = save_path(char_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_saves():
    ensure_dir()
    out = []
    for fn in os.listdir(SAVE_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(SAVE_DIR, fn), encoding="utf-8") as f:
                d = json.load(f)
            out.append({
                "char_id": d.get("char_id", fn[:-5]),
                "nickname": d.get("nickname", ""),
                "cls": d.get("cls", "C01"),
                "level": d.get("level", 1),
                "stage": d.get("stage", "1-1"),
                "saved_at": d.get("saved_at", 0),
            })
        except Exception:
            continue
    out.sort(key=lambda x: -x["saved_at"])
    return out


def delete(char_id):
    path = save_path(char_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def delete_all():
    ensure_dir()
    n = 0
    for fn in os.listdir(SAVE_DIR):
        if fn.endswith(".json"):
            os.remove(os.path.join(SAVE_DIR, fn))
            n += 1
    return n


def apply(p, data):
    """把存档写回 player。"""
    for k in PERSIST:
        if k in data:
            p[k] = data[k]
    return data
