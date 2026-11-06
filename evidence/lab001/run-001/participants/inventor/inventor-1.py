import pickle
import zlib
from collections import deque

class Engine:
    def __init__(self, snapshot=None):
        if snapshot is None:
            self.bal = {}
            self.receipts = {}
            self.jobs = {}
            self.done = {}
            self.wait = {}
            self.remaining = {}
            self.sums = {}
            self.queue = deque()
        else:
            (self.bal, self.receipts, self.jobs, self.done, self.wait,
             self.remaining, self.sums, self.queue) = pickle.loads(zlib.decompress(snapshot))

    def handle(self, message):
        op = message['op']
        if op == 'balance':
            return {'total': self.bal.get(message['key'], 0)}
        if op == 'credit':
            ident, key, delta = message['id'], message['key'], message['delta']
            old = self.receipts.get(ident)
            if old is not None:
                if old[0] != key or old[1] != delta:
                    return {'ok': False, 'error': 'conflict'}
                return {'ok': True, 'total': old[2]}
            total = self.bal.get(key, 0) + delta
            self.bal[key] = total
            self.receipts[ident] = (key, delta, total)
            return {'ok': True, 'total': total}
        if op == 'define':
            ident = message['id']
            parents = tuple(message['parents'])
            weight = message['weight']
            old = self.jobs.get(ident)
            if old is not None:
                if old != (parents, weight):
                    return {'ok': False, 'error': 'conflict'}
                return {'ok': True}
            self.jobs[ident] = (parents, weight)
            missing = 0
            value = weight
            for parent in parents:
                if parent in self.done:
                    value += self.done[parent]
                else:
                    missing += 1
                    self.wait.setdefault(parent, []).append(ident)
            self.remaining[ident] = missing
            self.sums[ident] = value
            if not missing:
                self.queue.append(ident)
            return {'ok': True}
        if op == 'run':
            while self.queue:
                ident = self.queue.popleft()
                value = self.sums.pop(ident)
                del self.remaining[ident]
                self.done[ident] = value
                for child in self.wait.pop(ident, ()):
                    self.sums[child] += value
                    count = self.remaining[child] - 1
                    self.remaining[child] = count
                    if not count:
                        self.queue.append(child)
            return {'done': self.done.copy()}
        if op == 'result':
            ident = message['id']
            if ident in self.done:
                return {'ready': True, 'value': self.done[ident]}
            return {'ready': False, 'value': None}

    def snapshot(self):
        return zlib.compress(pickle.dumps((self.bal, self.receipts, self.jobs,
            self.done, self.wait, self.remaining, self.sums, self.queue), protocol=5), 1)
