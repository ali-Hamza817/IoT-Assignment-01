"""Question 2 - hidden terminals and the RTS/CTS (Request to Send / Clear to Send) handshake.

Produces two animated simulations (frames for the report, MP4 videos, GIF previews):
  q2_hidden  - without RTS/CTS: sensors A and B cannot hear each other and collide at the AP (Access Point)
  q2_rtscts  - with RTS/CTS: the AP answers A with CTS; B overhears it and stays silent (NAV timer)

Usage
  python q2_rts_cts.py
"""
import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

from common import AQUA, AXIS, BLUE, CRITICAL, GREEN, GRID, INK, INK2, ORANGE, VIOLET, FrameWriter

A_XY = np.array([-2.3, -0.55])
B_XY = np.array([2.3, -0.55])
AP_XY = np.array([0.0, 0.75])

# light fills so every label can be black; the darker hue is used for outlines and arrows
C_RTS, C_CTS, C_DATA, C_ACK, C_NAV, C_WAIT = "#d4cdf7", "#c2ecdc", "#c9def8", "#c8e6c8", "#f8e0a3", "#e4e3de"
C_COLLISION = "#f5c6c6"
OUTLINE = {C_RTS: VIOLET, C_CTS: AQUA, C_DATA: BLUE, C_ACK: GREEN}
LANES = {"A": 2, "AP": 1, "B": 0}
FULL_FORM = {"RTS": "Request to Send", "CTS": "Clear to Send", "ACK": "Acknowledgement", "DATA": "soil reading"}
LEGEND = ("Wait = DIFS (Distributed Inter-Frame Space): the sensor checks that the channel is free before sending\n"
          "RTS (Request to Send)  |  CTS (Clear to Send)  |  ACK (Acknowledgement)  |  "
          "NAV (Network Allocation Vector): timer that keeps a sensor silent")

# Timing diagrams: (lane, start, end, label, fill colour[, hatch]); time is in arbitrary slots.
HIDDEN_EVENTS = [
    ("A", 0, 5, "Wait", C_WAIT), ("A", 5, 19, "DATA (A)", C_DATA),
    ("B", 6, 10, "Wait", C_WAIT), ("B", 10, 24, "DATA (B)", C_DATA),
    ("AP", 5, 10, "receiving A", AXIS), ("AP", 10, 24, "COLLISION - both frames lost", C_COLLISION),
    ("A", 19, 23, "no ACK", C_WAIT, "//"), ("B", 24, 28, "no ACK", C_WAIT, "//"),
    ("A", 23, 32, "send again", C_WAIT), ("B", 28, 32, "send again", C_WAIT),
]
RTS_CTS_EVENTS = [
    ("A", 0, 5, "Wait", C_WAIT), ("A", 5, 8, "RTS", C_RTS),
    ("AP", 9, 12, "CTS to A", C_CTS),
    ("A", 13, 27, "DATA (A)", C_DATA),
    ("AP", 28, 31, "ACK to A", C_ACK),
    ("B", 12, 31, "NAV: B stays silent", C_NAV, "//"),
    ("B", 31, 36, "Wait", C_WAIT), ("B", 36, 39, "RTS", C_RTS),
    ("AP", 40, 42, "CTS to B", C_CTS),
    ("A", 42, 44, "NAV", C_NAV, "//"),
]


# ------------------------------------------------------------------ drawing
def draw_scene(ax):
    """Field with sensors A and B, the access point and the obstacle between the sensors."""
    ax.set_xlim(-3.6, 3.6)
    ax.set_ylim(-1.75, 1.55)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((-3.6, -1.75), 7.2, 0.5, fc="#efe9df", ec="none", zorder=0))
    for c in (A_XY, B_XY):
        ax.plot(*np.c_[c, AP_XY], color=GRID, lw=1, ls=(0, (1, 2)), zorder=1)
    ax.text(0, -1.55, "A and B cannot hear each other", fontsize=7.5, color="black", ha="center")
    ax.add_patch(Polygon([[-0.45, -1.25], [-0.45, -0.05], [0, 0.25], [0.45, -0.05], [0.45, -1.25]],
                         closed=True, fc="#d6d3cb", ec="#8f8a7e", zorder=3))
    ax.text(0, -0.75, "barn /\nobstacle", ha="center", va="center", fontsize=7, color="black", zorder=4)
    for c, lab in ((A_XY, "A"), (B_XY, "B")):
        ax.plot([c[0], c[0]], [c[1] - 0.25, c[1] - 0.6], color=INK2, lw=2, zorder=4)
        ax.add_patch(Circle((c[0], c[1]), 0.25, fc=C_DATA, ec=BLUE, lw=1.5, zorder=5))
        ax.text(c[0], c[1], lab, ha="center", va="center", color="black", fontsize=11, fontweight="bold", zorder=6)
        ax.text(c[0], c[1] - 0.95, f"soil sensor {lab}", ha="center", fontsize=7.5, color="black")
    ax.add_patch(Polygon([AP_XY + [-0.28, -0.22], AP_XY + [0.28, -0.22], AP_XY + [0, 0.26]],
                         fc=ORANGE, ec="white", lw=1.5, zorder=5))
    ax.text(AP_XY[0] + 0.75, AP_XY[1] + 0.05, "Access Point (AP)\nWi-Fi (Wireless Fidelity)", ha="left",
            va="center", fontsize=7.5, fontweight="bold", color="black", linespacing=1.3)


def draw_frame_in_flight(ax, src, dst, frac, color, label):
    """A frame travelling from src to its addressee dst; the abbreviation is followed by its full form."""
    p = (1 - frac) * src + frac * dst
    ax.annotate("", dst, src, arrowprops=dict(arrowstyle="-|>", color=OUTLINE[color], lw=1.6, alpha=0.6,
                                              shrinkA=16, shrinkB=16), zorder=6)
    ax.add_patch(FancyBboxPatch(p - [0.3, 0.13], 0.6, 0.26, boxstyle="round,pad=0.02",
                                fc=color, ec=OUTLINE[color], lw=1, zorder=8))
    ax.text(p[0], p[1], label, ha="center", va="center", fontsize=7, color="black", fontweight="bold", zorder=9)
    ax.text(p[0], p[1] + 0.24, f"({FULL_FORM[label]})", ha="center", va="center", fontsize=6,
            color="black", fontweight="bold", zorder=9,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))


def draw_overheard(ax, listener, addressee):
    """The CTS is a radio signal: a nearby sensor it is not addressed to still hears it."""
    ax.plot(*np.c_[AP_XY, listener], color=AQUA, lw=1.2, ls=(0, (2, 2)), zorder=5)
    ax.text(listener[0], listener[1] + 0.5, f"overhears the CTS\n(it is for {addressee})", ha="center",
            fontsize=7, color="black", fontweight="bold")


def draw_blocked(ax, src, dst):
    mid = 0.5 * (src + dst)
    stop = src + 0.82 * (mid - src)
    ax.plot([src[0], stop[0]], [src[1], stop[1]], color=CRITICAL, lw=1.2, ls=(0, (2, 2)), zorder=6)
    ax.text(stop[0], stop[1], "x", color="black", fontsize=12, fontweight="bold", ha="center", va="center",
            zorder=7)


def draw_timeline(ax, events, t, t_end):
    """Timing diagram revealed up to time t. events: (lane, start, end, label, colour[, hatch])."""
    ax.set_xlim(0, t_end)
    ax.set_ylim(-0.6, 2.6)
    ax.set_yticks([2, 1, 0])
    ax.set_yticklabels(["Sensor A", "Access Point", "Sensor B"], fontsize=8, fontweight="bold", color=INK)
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    for y in (0, 1, 2):
        ax.axhline(y, color=GRID, lw=0.8, zorder=0)
    for lane, start, end, label, colour, *style in events:
        if start >= t:
            continue
        shown_end = min(end, t)
        y = LANES[lane]
        height = 0.3 if colour == C_WAIT else 0.5
        ax.add_patch(Rectangle((start, y - height / 2), shown_end - start, height, fc=colour, ec="white",
                               lw=0.8, hatch=style[0] if style else None,
                               alpha=0.55 if colour == C_NAV else 0.95, zorder=2))
        fits = len(label) * 6.5 * 0.62 / 72 < 0.85 * 7.2 * (shown_end - start) / t_end
        if label and fits:
            ax.text((start + shown_end) / 2, y, label, ha="center", va="center", fontsize=6.5,
                    color="black", fontweight="bold", zorder=3)
    ax.axvline(t, color=INK, lw=1, zorder=5)
    ax.text(t_end, -0.55, "time ->", ha="right", fontsize=7, color="black")


def render_animation(name, events, script, t_end, title):
    """script: (t0, t1, caption, overlay) entries; overlay(ax, t, progress) draws on the scene."""
    writer = FrameWriter(name, fps=5)
    times = np.arange(0, t_end + 0.01, 0.5)
    for t in times:
        fig = plt.figure(figsize=(7.2, 5.2))
        ax = fig.add_axes((0.02, 0.35, 0.96, 0.47))
        draw_scene(ax)
        caption = ""
        for t0, t1, text, overlay in script:
            if t0 <= t < t1 or (t >= t_end and t1 >= t_end):
                overlay(ax, t, min(1.0, 0.0 if t1 == t0 else (t - t0) / (t1 - t0)))
                caption = text
        fig.text(0.02, 0.97, title, fontsize=11, fontweight="bold", color="black", va="top")
        fig.text(0.02, 0.915, caption, fontsize=8.5, color="black", va="top", linespacing=1.4)
        draw_timeline(fig.add_axes((0.13, 0.09, 0.85, 0.24)), events, t, t_end)
        fig.text(0.5, 0.008, LEGEND, fontsize=6.5, color="black", ha="center", linespacing=1.4)
        writer.add(fig, hold=10 if t >= times[-1] else 1)
        plt.close(fig)
    writer.close()


# ------------------------------------------------------------------ the two simulations
def animate_hidden_terminal():
    def a_checks(ax, t, f):
        ax.text(A_XY[0], A_XY[1] + 0.5, "channel free", ha="center", fontsize=7.5, color="black", fontweight="bold")

    def b_checks(ax, t, f):
        ax.text(B_XY[0], B_XY[1] + 0.5, "channel free (!)", ha="center", fontsize=7.5, color="black",
                fontweight="bold")
        draw_blocked(ax, B_XY, A_XY)

    def a_data(ax, t, f):
        draw_frame_in_flight(ax, A_XY, AP_XY, min(1, f * 1.6), C_DATA, "DATA")
        draw_blocked(ax, A_XY, B_XY)

    def b_data(ax, t, f):
        draw_frame_in_flight(ax, B_XY, AP_XY, min(1, f * 1.6), C_DATA, "DATA")

    def collision(ax, t, f):
        r = 0.24 + 0.05 * math.sin(t * 3)
        ang = np.linspace(0, 2 * np.pi, 17)
        rr = np.where(np.arange(17) % 2, r, r * 1.9)
        ax.add_patch(Polygon(np.c_[AP_XY[0] + rr * np.cos(ang), AP_XY[1] + rr * np.sin(ang)],
                             fc=C_COLLISION, ec=CRITICAL, lw=1.2, zorder=10))
        ax.text(AP_XY[0], AP_XY[1], "!", ha="center", va="center", color="black", fontsize=14, fontweight="bold",
                zorder=11)

    def no_ack(ax, t, f):
        for c in (A_XY, B_XY):
            ax.text(c[0], c[1] + 0.5, "no ACK (Acknowledgement)", ha="center", fontsize=7, color="black")

    both = "Both signals reach the AP (Access Point) at the same time: COLLISION."
    script = [
        (0, 5, "1) A checks that the channel is free.", a_checks),
        (5, 6, "2) A sends its DATA to the AP (Access Point).", a_data),
        (6, 10, "3) B cannot hear A, so B also finds the channel free.", b_checks),
        (6, 10, "3) B cannot hear A, so B also finds the channel free.", a_data),
        (10, 19, both, a_data),
        (10, 24, both, b_data),
        (10, 24, both, collision),
        (24, 32.1, "4) No ACK (Acknowledgement) comes back, so both sensors must send again.", no_ack),
    ]
    render_animation("q2_hidden", HIDDEN_EVENTS, script, 32,
                     "Without RTS/CTS (Request to Send / Clear to Send): collision")


def animate_rts_cts():
    def a_checks(ax, t, f):
        ax.text(A_XY[0], A_XY[1] + 0.5, "checks channel is free", ha="center", fontsize=7, color="black")

    def rts(ax, t, f):
        draw_frame_in_flight(ax, A_XY, AP_XY, f, C_RTS, "RTS")
        draw_blocked(ax, A_XY, B_XY)
        ax.text(B_XY[0], B_XY[1] + 0.5, "hears nothing", ha="center", fontsize=7.5, color="black")

    def cts_to_a(ax, t, f):
        draw_frame_in_flight(ax, AP_XY, A_XY, f, C_CTS, "CTS")
        draw_overheard(ax, B_XY, "A")

    def nav_timer(ax, t, t0=12, t1=31):
        left = max(0, (t1 - t) / (t1 - t0))
        x, y = B_XY[0] - 0.55, B_XY[1] + 0.42
        ax.add_patch(Rectangle((x, y), 1.1, 0.16, fc="white", ec="#c9a227", lw=1, zorder=7))
        ax.add_patch(Rectangle((x, y), 1.1 * left, 0.16, fc="#f0c54a", ec="none", zorder=8))
        ax.text(B_XY[0], B_XY[1] + 0.68, "NAV (Network Allocation Vector) timer: silent", ha="center",
                fontsize=7, color="black", fontweight="bold")

    def data(ax, t, f):
        draw_frame_in_flight(ax, A_XY, AP_XY, f, C_DATA, "DATA")
        nav_timer(ax, t)

    def ack(ax, t, f):
        draw_frame_in_flight(ax, AP_XY, A_XY, f, C_ACK, "ACK")
        nav_timer(ax, t)

    def b_free(ax, t, f):
        ax.text(B_XY[0], B_XY[1] + 0.5, "timer ended: B may send", ha="center", fontsize=7, color="black",
                fontweight="bold")

    def b_rts(ax, t, f):
        draw_frame_in_flight(ax, B_XY, AP_XY, f, C_RTS, "RTS")

    def cts_to_b(ax, t, f):
        draw_frame_in_flight(ax, AP_XY, B_XY, f, C_CTS, "CTS")
        draw_overheard(ax, A_XY, "B")

    script = [
        (0, 5, "1) A checks that the channel is free.", a_checks),
        (5, 8, "2) A sends RTS (Request to Send) to the AP (Access Point).", rts),
        (8, 12, "3) The AP (Access Point) replies CTS (Clear to Send) to A.\n"
                "    B cannot hear A, but B hears this CTS, so it starts its NAV (Network Allocation Vector) timer.",
         cts_to_a),
        (12, 27, "4) A sends its DATA. B stays silent: no collision.", data),
        (27, 31, "5) The AP (Access Point) sends ACK (Acknowledgement) to A.", ack),
        (31, 36, "6) B's timer ends. Now B checks the channel and sends its own RTS (Request to Send).", b_free),
        (36, 39, "6) B's timer ends. Now B checks the channel and sends its own RTS (Request to Send).", b_rts),
        (39, 44.1, "7) The AP (Access Point) replies CTS (Clear to Send) to B; this time A hears it and waits.",
         cts_to_b),
    ]
    render_animation("q2_rtscts", RTS_CTS_EVENTS, script, 44,
                     "With RTS/CTS (Request to Send / Clear to Send): no collision")


def main():
    animate_hidden_terminal()
    animate_rts_cts()


if __name__ == "__main__":
    main()
