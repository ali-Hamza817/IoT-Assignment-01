"""Question 1 - IoT grid deployment over 1,000 m x 1,000 m.

Grid positions are (50 + 100 i, 50 + 100 j) for i, j = 0..9, so the first node N1 is at (50, 50).
The last top-right position (950, 950) is the AP (Access Point); the other 99 positions are IoT nodes.
Node numbering is row by row from the bottom-left: N = 10 x (row - 1) + column.

Computes connectivity, the nodes that reach the AP directly, the shortest path from N1, and the
forwarding load per node, and draws three diagrams (media/figures/q1_*.pdf / .png) plus results/q1.json.

Usage
  python q1_grid_deployment.py
"""
import json
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from common import BLUE, RESULTS, save_figure

SPACING = 100.0
R_NODE = 100.0                       # node-to-node range (metres)
R_AP = 200.0                         # AP range (metres)
EPS = 1e-6
FONT = "Times New Roman"

XY = np.array([(50 + SPACING * c, 50 + SPACING * r) for r in range(10) for c in range(10)])
AP_INDEX = 99                        # position (950, 950)
AP = XY[AP_INDEX]
NODES = list(range(99))              # indices of the 99 IoT nodes, N1 .. N99


def name(i):
    return f"N{i + 1}"


def distance(a, b):
    return float(np.linalg.norm(XY[a] - XY[b]))


def neighbours(i):
    return [j for j in NODES if j != i and distance(i, j) <= R_NODE + EPS]


def hop_counts():
    """Number of wireless transmissions each node needs to reach the AP (breadth-first search)."""
    hops = {i: 1 for i in NODES if distance(i, AP_INDEX) <= R_AP + EPS}
    queue = deque(hops)
    while queue:
        u = queue.popleft()
        for v in neighbours(u):
            if v not in hops:
                hops[v] = hops[u] + 1
                queue.append(v)
    return hops


def forwarding_load(hops):
    """Packets each node transmits per minute (own packet + relayed packets), and packets per minute
    on every link. Every node forwards to a neighbour one hop closer to the AP; packets are shared
    evenly (round robin) between equally close neighbours."""
    load = {i: 1 for i in NODES}
    flow = {}
    for i in sorted(NODES, key=lambda k: -hops[k]):
        if hops[i] == 1:
            flow[(i, AP_INDEX)] = load[i]
            continue
        parents = [j for j in neighbours(i) if hops[j] == hops[i] - 1]
        base, extra = divmod(load[i], len(parents))
        for m, p in enumerate(parents):
            share = base + (1 if m < extra else 0)
            if share:
                load[p] += share
                flow[(i, p)] = share
    return load, flow


def shortest_path(src, hops):
    """A shortest path from node `src` to the AP, as a list of indices ending with AP_INDEX.

    Every step moves to a neighbour one hop closer to the AP. Among equally short choices the walk
    goes up while below row 9 and right otherwise, so the drawn route stays easy to follow."""
    path = [src]
    u = src
    while hops[u] > 1:
        parents = [j for j in neighbours(u) if hops[j] == hops[u] - 1]
        preferred = u + 10 if u // 10 < 8 else u + 1
        u = preferred if preferred in parents else parents[0]
        path.append(u)
    return path + [AP_INDEX]


def shortest_path_n1(hops):
    """N1 up the left column to N81, right along row 9 to N89, then the AP (141.4 metres)."""
    return shortest_path(0, hops)


# ------------------------------------------------------------------ drawing
def base_axes(figsize=(7.0, 7.6)):
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes((0.08, 0.17, 0.88, 0.8))
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1000)
    ax.set_aspect("equal")
    ax.set_facecolor("white")
    ax.set_xticks(np.arange(0, 1001, 100))
    ax.set_yticks(np.arange(0, 1001, 100))
    ax.tick_params(labelsize=9, colors="black")
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color("black")
    ax.set_axisbelow(True)
    ax.grid(True, color="#d9d9d9", linewidth=0.6, zorder=0)       # 100 m calibration lines
    ax.set_xlabel("x (metres)", fontfamily=FONT, color="black")
    ax.set_ylabel("y (metres)", fontfamily=FONT, color="black")
    for i in NODES:
        for j in neighbours(i):
            if j > i:
                ax.plot(*np.c_[XY[i], XY[j]], color="#c8c8c8", lw=0.8, zorder=1)
    return fig, ax


def draw_nodes(ax, fill=None, size=15):
    for i in NODES:
        fc = "white" if fill is None else fill(i)
        ax.add_patch(Circle(XY[i], size + 6, fc=fc, ec="black", lw=0.8, zorder=3))
        ax.text(XY[i][0], XY[i][1], str(i + 1), ha="center", va="center", fontsize=7, color="black", fontfamily=FONT,
                zorder=4)
    ax.scatter(*AP, marker="^", s=330, c="black", zorder=5)
    ax.text(AP[0], AP[1] + 32, "AP", ha="center", fontsize=9, fontweight="bold", color="black",
            fontfamily=FONT, zorder=5)


def figure_layout(direct):
    fig, ax = base_axes()
    ax.add_patch(Circle(AP, R_AP, fill=False, ec="black", lw=1, ls="--", zorder=2))
    for i in direct:
        ax.plot(*np.c_[XY[i], AP], color="black", lw=1.2, zorder=2)
    draw_nodes(ax, fill=lambda i: "#d9d9d9" if i in direct else "white")
    legend = [
        Line2D([], [], marker="o", ls="", ms=9, mfc="white", mec="black", label="IoT node"),
        Line2D([], [], marker="o", ls="", ms=9, mfc="#d9d9d9", mec="black",
               label="Node in direct range of the AP (Access Point)"),
        Line2D([], [], marker="^", ls="", ms=11, color="black", label="AP (Access Point) at (950, 950)"),
        Line2D([], [], color="black", ls="--", lw=1, label="AP (Access Point) range, 200 metres"),
        Line2D([], [], color="#c8c8c8", lw=1, label="Node-to-node link, 100 metres"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False,
               prop={"family": FONT, "size": 10}, labelcolor="black")
    save_figure(fig, "q1_layout")


def figure_path(path):
    fig, ax = base_axes()
    pts = np.array([XY[i] for i in path])
    ax.plot(pts[:, 0], pts[:, 1], color=BLUE, lw=3, zorder=2, solid_capstyle="round")
    on_path = set(path)
    draw_nodes(ax, fill=lambda i: "#cfe0f7" if i in on_path else "white")
    for k, i in enumerate(path[:-1]):
        dx, dy = (-38, 0) if XY[i][0] < 100 else (0, -38)
        ax.text(XY[i][0] + dx, XY[i][1] + dy, f"{k + 1}", ha="center", va="center", fontsize=7.5,
                color="black", fontfamily=FONT, fontstyle="italic", zorder=4)
    legend = [
        Line2D([], [], color=BLUE, lw=3, label="Shortest path N1 to AP (Access Point)"),
        Line2D([], [], ls="", label="italic numbers = transmission number (1 to 17)"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.02), ncol=2, frameon=False,
               prop={"family": FONT, "size": 10}, labelcolor="black")
    save_figure(fig, "q1_path")


def figure_load(load, flow):
    """Forwarding load: node number and packets per minute in every circle, arrows sized by link traffic."""
    fig = plt.figure(figsize=(7.0, 8.4))
    ax = fig.add_axes((0.08, 0.2, 0.88, 0.77))
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1000)
    ax.set_aspect("equal")
    ax.set_facecolor("white")
    ax.set_xticks(np.arange(0, 1001, 100))
    ax.set_yticks(np.arange(0, 1001, 100))
    ax.tick_params(labelsize=9, colors="black")
    ax.set_axisbelow(True)
    ax.grid(True, color="#d9d9d9", linewidth=0.6, zorder=0)       # 100 m calibration lines
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color("black")
    ax.set_xlabel("x (metres)", fontfamily=FONT, color="black")
    ax.set_ylabel("y (metres)", fontfamily=FONT, color="black")

    peak = max(load.values())
    shade = LinearSegmentedColormap.from_list("load", ["#ffffff", "#cfe0f7", "#86b6ef", "#4f8fe0"])
    ax.add_patch(Circle(AP, R_AP, fill=False, ec="black", lw=1, ls="--", zorder=1))
    for (i, p), packets in flow.items():
        # a straight 200 m link to the AP would pass through another node: curve it around that node
        bend = 0.0
        if p == AP_INDEX and distance(i, p) > 150:
            bend = -0.22 if XY[i][1] == AP[1] else 0.22
        ax.annotate("", XY[p], XY[i], zorder=2,
                    arrowprops=dict(arrowstyle="-|>,head_length=0.35,head_width=0.2", color="#3a78c9",
                                    lw=0.7 + 4.5 * packets / peak, alpha=0.75, shrinkA=15, shrinkB=17,
                                    connectionstyle=f"arc3,rad={bend}"))
    for i in NODES:
        ax.add_patch(Circle(XY[i], 30, fc=shade(load[i] / peak), ec="black", lw=0.8, zorder=3))
        ax.text(XY[i][0], XY[i][1] + 9, str(i + 1), ha="center", va="center", fontsize=8.5, fontweight="bold",
                color="black", fontfamily=FONT, zorder=4)
        ax.text(XY[i][0], XY[i][1] - 11, str(load[i]), ha="center", va="center", fontsize=7.5,
                color="black", fontfamily=FONT, zorder=4)
    ax.scatter(*AP, marker="^", s=380, c="black", zorder=5)
    ax.text(AP[0], AP[1] + 36, "AP", ha="center", fontsize=10, fontweight="bold", color="black", fontfamily=FONT)

    bar_ax = fig.add_axes((0.2, 0.085, 0.6, 0.018))
    bar = fig.colorbar(plt.cm.ScalarMappable(cmap=shade, norm=plt.Normalize(0, peak)), cax=bar_ax,
                       orientation="horizontal")
    bar.set_label("Packets the node transmits per minute (its own + relayed)", fontfamily=FONT, fontsize=10,
                  color="black")
    bar.ax.tick_params(labelsize=9, colors="black")
    bar.outline.set_edgecolor("black")
    fig.text(0.5, 0.02, "In each circle: node number (top, bold) and packets per minute (bottom).   "
             "Arrow width = traffic on that link.", ha="center", fontsize=10, color="black", fontfamily=FONT)
    save_figure(fig, "q1_load")

def main():
    hops = hop_counts()
    assert len(hops) == len(NODES), "some node cannot reach the AP"
    direct = sorted(i for i in NODES if hops[i] == 1)
    path = shortest_path_n1(hops)
    assert len(path) - 1 == hops[0], "path is not a shortest path"
    load, flow = forwarding_load(hops)
    results = {
        "iot_nodes": len(NODES),
        "all_connected": True,
        "max_transmissions": max(hops.values()),
        "direct_nodes": {name(i): round(distance(i, AP_INDEX), 1) for i in direct},
        "path_n1": [name(i) for i in path[:-1]] + ["AP"],
        "n1_iot_hops": len(path) - 2,
        "n1_transmissions": len(path) - 1,
        "load_direct_nodes": {name(i): load[i] for i in direct},
        "packets_per_minute_at_ap": sum(load[i] for i in direct),
        "top_loads": {name(i): load[i] for i in sorted(NODES, key=lambda k: -load[k])[:8]},
    }
    figure_layout(direct)
    figure_path(path)
    figure_load(load, flow)
    (RESULTS / "q1.json").write_text(json.dumps(results, indent=1))
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
