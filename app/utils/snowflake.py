import time, threading

class Snowflake:
    def __init__(self, datacenter_id=0, worker_id=0):
        self.datacenter_id = datacenter_id & 0x1F
        self.worker_id = worker_id & 0x1F
        self.sequence = 0
        self.last_ts = -1
        self.lock = threading.Lock()

    def _timestamp(self):
        return int(time.time() * 1000)

    def next_id(self):
        with self.lock:
            ts = self._timestamp()
            if ts == self.last_ts:
                self.sequence = (self.sequence + 1) & 0xFFF
                if self.sequence == 0:
                    while ts <= self.last_ts:
                        ts = self._timestamp()
            else:
                self.sequence = 0
            self.last_ts = ts
            return ((ts - 1672531200000) << 22) | (self.datacenter_id << 17) | (self.worker_id << 12) | self.sequence
