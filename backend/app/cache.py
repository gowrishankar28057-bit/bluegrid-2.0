"""Bounded, expiring, per-process run storage for local analysis and exports."""
from collections import OrderedDict
from threading import RLock
from time import monotonic
from uuid import uuid4


class RunCache:
    def __init__(self, maximum=32, ttl_seconds=3600, clock=monotonic):
        self.maximum = maximum
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self.runs = OrderedDict()
        self.lock = RLock()

    def _expire(self):
        now = self.clock()
        for key in list(self.runs):
            if self.runs[key][0] <= now:
                del self.runs[key]

    def put(self, result):
        with self.lock:
            self._expire()
            key = str(uuid4())
            result["run_id"] = key
            self.runs[key] = (self.clock() + self.ttl_seconds, result)
            while len(self.runs) > self.maximum:
                self.runs.popitem(last=False)
            return result

    def get(self, key):
        with self.lock:
            self._expire()
            return self.runs.get(key, (None, None))[1]
