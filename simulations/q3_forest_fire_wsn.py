"""Question 3 - forest-fire WSN (Wireless Sensor Network): clustered multi-hop architecture.

Places sensor nodes at random over a square forest, forms clusters for one round (cluster heads elected
as in LEACH, Low-Energy Adaptive Clustering Hierarchy), routes every node to the base station over
minimum-energy multi-hop paths, and counts the transmissions one round of readings needs with and without
aggregation. The functions take parameters so the interactive simulation can vary them; running this file
draws the report diagram media/figures/q3_architecture (.pdf / .png) with the default settings.

Usage
  python q3_forest_fire_wsn.py
"""
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from common import BLUE, ORANGE, VIOLET, save_figure

FONT = "Times New Roman"
K = 2000                                      # bits per reading
E_ELEC, EPS_FS, EPS_MP = 50e-9, 10e-12, 0.0013e-12
D0 = np.sqrt(EPS_FS / EPS_MP)                 # free-space / multipath crossover, about 87.7 metres


@dataclass
class Network:
    size: float                               # forest side length in metres
    positions: np.ndarray                     # (n, 2) node coordinates in metres
    base: np.ndarray                          # base-station coordinates
    parent: np.ndarray                        # next hop towards the base station (n = base, -1 = none)
    hops: np.ndarray                          # transmissions from each node to the base station (-1 = none)
    heads: np.ndarray                         # indices of cluster heads (incl. isolated nodes)
    members: np.ndarray                       # indices of member nodes
    member_head: np.ndarray                   # cluster head of each member

    @property
    def n(self):
        return len(self.positions)


def tx_energy(d):
    """First-order radio model: energy to send one reading over distance d."""
    d = np.asarray(d, float)
    return K * E_ELEC + K * np.where(d < D0, EPS_FS * d ** 2, EPS_MP * d ** 4)


def build_network(n_nodes=1000, size=2000.0, radio_range=200.0, head_fraction=0.10, seed=2026):
    """Random deployment, minimum-energy routes to the base station and one round of clustering."""
    rng = np.random.default_rng(seed)
    pos = rng.uniform([0, 0], [size, size], (n_nodes, 2))
    base = np.array([size / 2, -20.0])

    pairs = np.array(sorted(cKDTree(pos).query_pairs(radio_range))).reshape(-1, 2)
    d_pair = np.linalg.norm(pos[pairs[:, 0]] - pos[pairs[:, 1]], axis=1)
    d_base = np.linalg.norm(pos - base, axis=1)
    near = np.flatnonzero(d_base <= radio_range)
    cost = tx_energy(d_pair) + K * E_ELEC
    graph = csr_matrix((np.r_[cost, cost, tx_energy(d_base[near]) + K * E_ELEC],
                        (np.r_[pairs[:, 0], pairs[:, 1], near],
                         np.r_[pairs[:, 1], pairs[:, 0], np.full(len(near), n_nodes)])),
                       shape=(n_nodes + 1, n_nodes + 1))
    dist, pred = dijkstra(graph, directed=False, indices=n_nodes, return_predecessors=True)
    reachable = np.isfinite(dist[:n_nodes])
    parent = np.where(reachable, pred[:n_nodes], -1)
    hops = np.full(n_nodes, -1)
    for i in np.argsort(dist[:n_nodes]):
        if reachable[i]:
            hops[i] = 1 if parent[i] == n_nodes else hops[parent[i]] + 1

    heads = rng.random(n_nodes) < head_fraction
    if not heads.any():
        heads[rng.integers(n_nodes)] = True
    head_idx = np.flatnonzero(heads)
    members = np.flatnonzero(~heads)
    d, j = cKDTree(pos[head_idx]).query(pos[members], distance_upper_bound=radio_range)
    isolated = ~np.isfinite(d)
    heads[members[isolated]] = True           # no head in range: the node reports for itself
    return Network(size, pos, base, parent, hops, np.flatnonzero(heads), members[~isolated],
                   head_idx[j[~isolated]])


def route_segments(net, sources):
    """Line segments of the multi-hop routes from `sources` to the base station (shared hops drawn once)."""
    seen, segments = set(), []
    for s in sources:
        u = s
        while u != net.n and net.parent[u] >= 0 and u not in seen:
            seen.add(u)
            v = net.parent[u]
            segments.append((net.positions[u], net.base if v == net.n else net.positions[v]))
            u = v
    return segments


def transmissions_per_round(net):
    """Transmissions needed for one reading from every connected node.

    flat:                   every reading travels its own multi-hop route
    clustered, no aggregation: one hop to the cluster head, then every reading is relayed separately
    clustered + aggregation:   one hop to the cluster head, then one fused packet per cluster
    """
    ok = net.hops > 0
    flat = int(net.hops[ok].sum())
    member_ok = ok[net.members] & ok[net.member_head]
    head_ok = net.heads[ok[net.heads]]
    readings_per_head = 1 + np.bincount(net.member_head[member_ok], minlength=net.n)
    no_agg = int(member_ok.sum() + (readings_per_head[head_ok] * net.hops[head_ok]).sum())
    agg = int(member_ok.sum() + net.hops[head_ok].sum())
    return {"flat": flat, "clustered_no_aggregation": no_agg, "clustered_aggregation": agg}


def draw_architecture(net):
    fig = plt.figure(figsize=(7.0, 8.2))
    ax = fig.add_axes((0.03, 0.19, 0.94, 0.79))
    size = net.size
    ax.set_xlim(-40, size + 40)
    ax.set_ylim(-130, size + 40)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), size, size, fc="white", ec="black", lw=0.8, zorder=0))
    pos = net.positions
    ax.add_collection(LineCollection(list(np.stack([pos[net.members], pos[net.member_head]], 1)), colors=BLUE,
                                     linewidths=0.4, alpha=0.55, zorder=2))
    backbone = []
    for h in net.heads:                       # every head's full route, as in the report diagram
        u = h
        while u != net.n and net.parent[u] >= 0:
            v = net.parent[u]
            backbone.append((pos[u], net.base if v == net.n else pos[v]))
            u = v
    ax.add_collection(LineCollection(backbone, colors=VIOLET, linewidths=1.0, alpha=0.45, zorder=3))
    ax.scatter(pos[net.members, 0], pos[net.members, 1], s=6, c=BLUE, lw=0, zorder=4)
    ax.scatter(pos[net.heads, 0], pos[net.heads, 1], s=55, marker="*", c=ORANGE, ec="black", lw=0.3, zorder=5)
    ax.scatter(*net.base, marker="^", s=260, c="black", zorder=6, clip_on=False)
    ax.text(net.base[0], net.base[1] - 90, "Base station (forest edge)", ha="center", va="center", fontsize=11,
            color="black", fontfamily=FONT)
    legend = [
        Line2D([], [], marker="o", ls="", ms=4, color=BLUE, label="Sensor node (cluster member)"),
        Line2D([], [], marker="*", ls="", ms=11, mfc=ORANGE, mec="black", mew=0.4,
               label="Cluster head (aggregates its members' readings)"),
        Line2D([], [], color=BLUE, lw=1, alpha=0.7, label="Member to cluster head (one short hop)"),
        Line2D([], [], color=VIOLET, lw=1.5, alpha=0.7, label="Multi-hop route from cluster head to base station"),
        Line2D([], [], marker="^", ls="", ms=10, color="black", label="Base station"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=1, frameon=False,
               prop={"family": FONT, "size": 11}, labelcolor="black", handletextpad=0.6)
    save_figure(fig, "q3_architecture")


def main():
    net = build_network()
    draw_architecture(net)
    print(f"[q3_architecture] {len(net.heads)} cluster heads, {len(net.members)} members")
    print(transmissions_per_round(net))


if __name__ == "__main__":
    main()
