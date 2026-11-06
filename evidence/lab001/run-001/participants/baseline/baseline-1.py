import pickle
import zlib
from collections import deque

class Engine:
    def __init__(self, snapshot=None):
        if snapshot is None:
            self.balances = {}
            self.receipts = {}
            self.jobs = {}
            self.done = {}
        else:
            self.balances, self.receipts, self.jobs, self.done = pickle.loads(zlib.decompress(snapshot))
        self.waiters = {}
        self.remaining = {}
        self.queue = deque()
        for job, (parents, weight) in self.jobs.items():
            if job not in self.done:
                missing = 0
                for p in parents:
                    if p not in self.done:
                        missing += 1
                        self.waiters.setdefault(p, []).append(job)
                self.remaining[job] = missing
                if missing == 0:
                    self.queue.append(job)

    def handle(self, message):
        op = message['op']
        if op == 'balance':
            return {'total': self.balances.get(message['key'], 0)}
        if op == 'credit':
            ident, key, delta = message['id'], message['key'], message['delta']
            old = self.receipts.get(ident)
            if old is not None:
                if old[0] != key or old[1] != delta:
                    return {'ok': False, 'error': 'conflict'}
                return {'ok': True, 'total': old[2]}
            total = self.balances.get(key, 0) + delta
            self.balances[key] = total
            self.receipts[ident] = (key, delta, total)
            return {'ok': True, 'total': total}
        if op == 'define':
            ident = message['id']
            parents, weight = tuple(message['parents']), message['weight']
            old = self.jobs.get(ident)
            if old is not None:
                if old != (parents, weight):
                    return {'ok': False, 'error': 'conflict'}
                return {'ok': True}
            self.jobs[ident] = (parents, weight)
            missing = 0
            for p in parents:
                if p not in self.done:
                    missing += 1
                    self.waiters.setdefault(p, []).append(ident)
            self.remaining[ident] = missing
            if missing == 0:
                self.queue.append(ident)
            return {'ok': True}
        if op == 'result':
            ident = message['id']
            if ident in self.done:
                return {'ready': True, 'value': self.done[ident]}
            return {'ready': False, 'value': None}
        if op == 'run':
            while self.queue:
                ident = self.queue.popleft()
                parents, weight = self.jobs[ident]
                value = weight + sum(self.done[p] for p in parents)
                self.done[ident] = value
                del self.remaining[ident]
                for child in self.waiters.pop(ident, ()):
                    n = self.remaining[child] - 1
                    self.remaining[child] = n
                    if n == 0:
                        self.queue.append(child)
            return {'done': self.done.copy()}
        raise ValueError('unknown operation')

    def snapshot(self):
        return zlib.compress(pickle.dumps((self.balances, self.receipts, self.jobs, self.done), protocol=5), 6)
