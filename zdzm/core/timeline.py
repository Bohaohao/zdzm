# -*- coding: utf-8 -*-
"""离散事件时间轴。

不按固定帧推进，而是维护一个最小堆，每次直接跳到"下一个事件发生的时刻"。
这保证了策划案里的秒级设计（连段窗口 1.4s、断循环 4s、猎印 6s）可以原样使用。
"""
import heapq

# 浮点误差容忍：同一时刻的事件按入堆顺序处理
EPS = 1e-9


class Timeline:
    def __init__(self):
        self.now = 0.0
        self._heap = []
        self._seq = 0

    def push(self, t, kind, **kw):
        """排入一个事件。t 必须 >= now。"""
        t = max(t, self.now)
        heapq.heappush(self._heap, (round(t, 6), self._seq, kind, kw))
        self._seq += 1

    def push_delay(self, delay, kind, **kw):
        self.push(self.now + delay, kind, **kw)

    def pop(self):
        t, _, kind, kw = heapq.heappop(self._heap)
        self.now = t
        return kind, kw

    def peek_time(self):
        return self._heap[0][0] if self._heap else None

    def empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)
