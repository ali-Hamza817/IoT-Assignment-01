"""General multi-hop IoT network model used by the interactive Question 1 environment.

Nodes are arbitrary (x, y) positions; two nodes are linked when their distance is at most the node range,
and a node reaches the AP (Access Point) directly when it is within the AP range. Breadth-first search gives
the number of transmissions from every node to the AP, a shortest path from any node, and the forwarding
load when every node generates packets at a fixed rate (packets shared evenly between equally close
next hops).
"""
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import KDTree

EPS = 1e-6


def grid_positions(area, spacing, offset):
    """Square grid inside an area x area square, first node at (offset, offset)."""
    coords = np.arange(offset, area + EPS, spacing)
    return np.array([(x, y) for y in coords for x in coords], dtype=float).reshape(-1, 2)


def random_positions(count, area, seed):
    return np.random.default_rng(seed).uniform(0, area, (count, 2))


@dataclass
class Network:
    positions: np.ndarray                 # (n, 2) node coordinates in metres
    ap: np.ndarray                        # AP coordinates
    node_range: float
    ap_range: float
    rate: int = 1                         # packets generated per node per minute
    neighbours: list = field(init=False)
    hops: np.ndarray = field(init=False)  # transmissions to reach the AP; -1 = unreachable
    load: np.ndarray = field(init=False)  # packets transmitted per minute (own + relayed)
    flow: dict = field(init=False)        # (node, next hop) -> packets per minute; next hop -1 = AP

    def __post_init__(self):
        self.positions = np.asarray(self.positions, float).reshape(-1, 2)
        self.ap = np.asarray(self.ap, float)
        n = len(self.positions)
        self.neighbours = [[] for _ in range(n)]
        if n:
            for i, j in KDTree(self.positions).query_pairs(self.node_range + EPS):
                self.neighbours[i].append(j)
                self.neighbours[j].append(i)
        for nb in self.neighbours:
            nb.sort()
        self._hop_counts()
        self._forwarding_load()

    @property
    def n(self):
        return len(self.positions)

    def distance_to_ap(self, i):
        return float(np.linalg.norm(self.positions[i] - self.ap))

    def _hop_counts(self):
        self.hops = np.full(self.n, -1)
        queue = deque()
        for i in range(self.n):
            if self.distance_to_ap(i) <= self.ap_range + EPS:
                self.hops[i] = 1
                queue.append(i)
        while queue:
            u = queue.popleft()
            for v in self.neighbours[u]:
                if self.hops[v] < 0:
                    self.hops[v] = self.hops[u] + 1
                    queue.append(v)

    def next_hops(self, i):
        if self.hops[i] == 1:
            return [-1]
        return [j for j in self.neighbours[i] if self.hops[j] == self.hops[i] - 1]

    def _forwarding_load(self):
        """Whole packets per minute; a node shares its packets round robin between equally close next hops."""
        self.load = np.where(self.hops > 0, int(self.rate), 0).astype(int)
        self.flow = {}
        for i in sorted(np.flatnonzero(self.hops > 0), key=lambda k: -self.hops[k]):
            parents = self.next_hops(i)
            base, extra = divmod(int(self.load[i]), len(parents))
            for m, p in enumerate(parents):
                share = base + (1 if m < extra else 0)
                if share:
                    self.flow[(int(i), int(p))] = share
                    if p >= 0:
                        self.load[p] += share

    def shortest_path(self, src):
        """A shortest path from `src` to the AP (list of node indices, the AP shown as -1), or None.

        Among equally short next hops the route first moves vertically towards the AP's row while staying
        at least one node range away from it, then heads for the AP: an L-shaped route that is easy to
        follow (on the assignment grid: N1 up to N81, along to N89, then the AP)."""
        if self.hops[src] < 0:
            return None
        path = [src]
        u = src
        while self.hops[u] > 1:
            dy_u = abs(self.ap[1] - self.positions[u][1])

            def preference(j, dy_u=dy_u):
                dy_j = abs(self.ap[1] - self.positions[j][1])
                vertical = dy_j < dy_u - EPS and dy_j >= self.node_range - EPS
                return (not vertical, self.distance_to_ap(j), j)

            u = min(self.next_hops(u), key=preference)
            path.append(u)
        return path + [-1]

    def summary(self):
        ok = self.hops > 0
        direct = np.flatnonzero(self.hops == 1)
        busiest = int(np.argmax(self.load)) if self.n else -1
        return {
            "nodes": self.n,
            "connected": int(ok.sum()),
            "unreachable": int((~ok).sum()),
            "direct": [int(i) for i in direct],
            "max_transmissions": int(self.hops[ok].max()) if ok.any() else 0,
            "mean_transmissions": float(self.hops[ok].mean()) if ok.any() else 0.0,
            "packets_at_ap": int(self.load[direct].sum()),
            "busiest": busiest,
            "busiest_load": int(self.load[busiest]) if self.n else 0,
        }
