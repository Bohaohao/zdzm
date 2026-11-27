# -*- coding: utf-8 -*-
"""可注入随机源。core 里禁止直接 import random。"""
import random


class Rng:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self._r = random.Random(self.seed)

    def rand(self):
        return self._r.random()

    def chance(self, pct):
        """pct 为百分数。"""
        return self._r.random() * 100.0 < pct

    def uniform(self, a, b):
        return self._r.uniform(a, b)

    def randint(self, a, b):
        return self._r.randint(a, b)

    def choice(self, seq):
        return self._r.choice(seq)

    def weighted(self, pairs):
        """pairs = [(item, weight), ...]"""
        total = sum(w for _, w in pairs)
        if total <= 0:
            return pairs[0][0] if pairs else None
        r = self._r.random() * total
        acc = 0.0
        for item, w in pairs:
            acc += w
            if r <= acc:
                return item
        return pairs[-1][0]

    def fork(self, tag):
        """派生子种子，便于回放时按用途分离。"""
        return Rng((self.seed * 1000003 + abs(hash(tag))) & 0x7FFFFFFF)
