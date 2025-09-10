from time import perf_counter
from contextlib import contextmanager
import logging

class TimerCollector:
    def __init__(self):
        self.timings = {}

    @contextmanager
    def timed(self, label):
        start = perf_counter()
        yield
        end = perf_counter()
        self.timings.setdefault(label, []).append(end - start)

    def report(self):
        for label, times in self.timings.items():
            avg = sum(times) / len(times)
            total = sum(times)
            logging.info(f"[{label}] runs: {len(times)}, avg: {avg:.6f}s, total: {total:.6f}s")


