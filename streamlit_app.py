"""IT863 Internet of Things, Assignment 01 - interactive simulations.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Community Cloud, main file streamlit_app.py (see README)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "simulations"))

import network_model as nm  # noqa: E402

import q2_rts_cts as q2  # noqa: E402
import q3_forest_fire_wsn as q3  # noqa: E402

REPO_URL = "https://github.com/ali-Hamza817/IoT-Assignment-01"
NODE_RANGE, AP_RANGE = 100.0, 200.0          # metres, as given in the assignment
FONT = dict(family="Times New Roman, Times, serif", color="black", size=14)
BLUE, LIGHT_BLUE, ORANGE, VIOLET, GREY = "#2a78d6", "#cfe0f7", "#eb6834", "#6250d6", "#c8c8c8"

st.set_page_config(page_title="IT863 Assignment 01 - Simulations", page_icon="📡", layout="wide")


def plot_layout(fig, x_range, y_range, height=720, tick=None):
    """White plot with black axes; `tick` (metres) adds calibrated grid lines and labels at that step."""
    grid = dict(dtick=tick, tick0=0, showgrid=True, gridcolor="#e3e3e3", gridwidth=1) if tick else dict(showgrid=False)
    fig.update_layout(
        font=FONT, height=height, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=10), showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.1, x=0, font=dict(size=13)),
        xaxis=dict(range=x_range, zeroline=False, linecolor="black", mirror=True, **grid,
                   constrain="domain", title=dict(text="x (metres)", font=dict(color="black")),
                   tickfont=dict(color="black")),
        yaxis=dict(range=y_range, zeroline=False, linecolor="black", mirror=True, **grid,
                   constrain="domain", scaleanchor="x", scaleratio=1,
                   title=dict(text="y (metres)", font=dict(color="black")), tickfont=dict(color="black")),
    )
    return fig


def how_to(text):
    st.markdown(f"**How to use:** {text}")


# ====================================================================== Question 1
def q1_network(area, spacing, moved):
    """Square grid from (spacing/2, spacing/2); the AP takes the last top-right grid position."""
    grid = nm.grid_positions(area, spacing, spacing / 2)
    last = int(np.lexsort((grid[:, 0], grid[:, 1]))[-1])
    ap = grid[last].copy()
    nodes = np.delete(grid, last, axis=0)
    if moved is not None and len(moved) == len(nodes):
        nodes = moved
    return nodes, ap


def q1_figure(net, area, show_path, path):
    pos, n = net.positions, net.n
    small = n <= 150
    fig = go.Figure()
    lx, ly = [], []
    for i in range(n):
        for j in net.neighbours[i]:
            if j > i:
                lx += [pos[i][0], pos[j][0], None]
                ly += [pos[i][1], pos[j][1], None]
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color=GREY, width=1), hoverinfo="skip",
                             name="Link between nodes (≤ 100 m)"))
    fig.add_shape(type="circle", x0=net.ap[0] - AP_RANGE, x1=net.ap[0] + AP_RANGE, y0=net.ap[1] - AP_RANGE,
                  y1=net.ap[1] + AP_RANGE, line=dict(color="black", dash="dash", width=1))
    fig.add_shape(type="rect", x0=0, y0=0, x1=area, y1=area, line=dict(color="black", width=1.5))

    px = [pos[i][0] if i >= 0 else net.ap[0] for i in path or []]
    py = [pos[i][1] if i >= 0 else net.ap[1] for i in path or []]
    if show_path and path:
        fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=BLUE, width=5), hoverinfo="skip",
                                 name="Path of the packet"))
    reach = net.hops > 0
    if show_path:
        on_path = set(path or [])
        colour = [LIGHT_BLUE if i in on_path else ("#d9d9d9" if net.hops[i] == 1 else "white") for i in range(n)]
        marker = dict(size=27 if small else 10, color=colour, line=dict(color="black", width=1))
    else:
        marker = dict(size=27 if small else 10, color=net.load.tolist(),
                      colorscale=[[0, "white"], [0.3, "#cfe0f7"], [0.7, "#86b6ef"], [1, "#4f8fe0"]],
                      line=dict(color="black", width=1), showscale=True,
                      colorbar=dict(title=dict(text="packets sent per minute", side="right"), thickness=14))
    hover = [f"N{i + 1}<br>" + (f"{net.hops[i]} transmission(s) to the AP<br>sends {net.load[i]} packet(s) per minute"
                                 if reach[i] else "cannot reach the AP") for i in range(n)]
    fig.add_trace(go.Scatter(x=pos[:, 0], y=pos[:, 1], mode="markers+text" if small else "markers",
                             text=[str(i + 1) for i in range(n)], textfont=dict(size=11, color="black"),
                             marker=marker, hovertext=hover, hoverinfo="text", name="IoT node (click one)"))
    node_trace = len(fig.data) - 1
    if (~reach).any():
        fig.add_trace(go.Scatter(x=pos[~reach, 0], y=pos[~reach, 1], mode="markers", hoverinfo="skip",
                                 marker=dict(symbol="x", size=16 if small else 10, color="black"),
                                 name="Cannot reach the AP"))
    fig.add_trace(go.Scatter(x=[net.ap[0]], y=[net.ap[1]], mode="markers+text", text=["AP"],
                             textposition="top center", marker=dict(symbol="triangle-up", size=24, color="black"),
                             hoverinfo="skip", name="AP (Access Point), range 200 m"))
    if show_path and path:
        packet = dict(symbol="square", size=16, color=ORANGE, line=dict(color="black", width=1))
        fig.add_trace(go.Scatter(x=[px[0]], y=[py[0]], mode="markers", hoverinfo="skip", name="Packet",
                                 marker=packet))
        k = len(fig.data) - 1
        fig.frames = [go.Frame(data=[go.Scatter(x=[px[s]], y=[py[s]])], traces=[k], name=str(s))
                      for s in range(len(path))]
        fig.update_layout(updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.02, xanchor="left", yanchor="bottom",
            buttons=[dict(label="▶  Send the packet", method="animate",
                          args=[None, dict(frame=dict(duration=450, redraw=True), transition=dict(duration=250),
                                           fromcurrent=False, mode="immediate")])])])
    pad = area * 0.03
    tick = 100 if area <= 1500 else 200
    return plot_layout(fig, [-pad, area + pad], [-pad, area + pad], tick=tick), node_trace


def question1():
    st.subheader("Question 1: IoT nodes on a grid")
    how_to("change the area or the distance between nodes, then click any node (or pick it in the list) and "
           "press “Send the packet” to watch it travel to the AP (Access Point). Nodes reach 100 m, the AP reaches "
           "200 m.")
    c1, c2, c3 = st.columns(3)
    area = c1.slider("Area size (metres)", 500, 2000, 1000, 100)
    spacing = c2.slider("Distance between nodes (metres)", 50, 200, 100, 10)
    show = c3.radio("Show", ["Path of a packet", "Traffic load"], horizontal=True)

    moved = st.session_state.get(f"q1-moved-{area}-{spacing}")
    nodes, ap = q1_network(area, spacing, moved)
    net = nm.Network(nodes, ap, NODE_RANGE, AP_RANGE)
    s = net.summary()

    clicked = st.session_state.get("q1_chart")
    points = clicked.get("selection", {}).get("points", []) if clicked else []
    if points:
        stamp = (points[0].get("curve_number"), points[0].get("point_index"))
        if stamp != st.session_state.get("q1_last_click") and stamp[0] == st.session_state.get("q1_node_trace"):
            st.session_state["q1_source"] = int(stamp[1])
        st.session_state["q1_last_click"] = stamp
    if st.session_state.get("q1_source", 0) >= s["nodes"]:
        st.session_state["q1_source"] = 0
    source = st.selectbox("Packet starts at node", range(s["nodes"]), format_func=lambda i: f"N{i + 1}",
                          key="q1_source", disabled=show != "Path of a packet")
    path = net.shortest_path(source)

    m = st.columns(3)
    m[0].metric("IoT nodes needed", s["nodes"])
    m[1].metric("Nodes that reach the AP", f"{s['connected']} of {s['nodes']}")
    if show == "Path of a packet":
        m[2].metric(f"Transmissions from N{source + 1} to the AP", len(path) - 1 if path else "no route")
        if path:
            st.markdown("**Route:** " + " → ".join(f"N{i + 1}" for i in path[:-1])
                        + f" → AP  ({len(path) - 2} IoT-to-IoT hops + 1 final hop to the AP)")
    else:
        m[2].metric("Busiest node", f"N{s['busiest'] + 1}: {s['busiest_load']} packets per minute")
        st.markdown("**Traffic load:** every node sends its own packet plus the packets it relays, so the nodes next "
                    "to the AP carry the most traffic (darker circles).")
    if s["unreachable"]:
        st.markdown(f"**Not connected:** {s['unreachable']} node(s) cannot reach the AP (marked ×) because the nodes "
                    "are more than 100 m apart.")

    fig, node_trace = q1_figure(net, area, show == "Path of a packet", path)
    st.session_state["q1_node_trace"] = node_trace
    st.plotly_chart(fig, width="stretch", key="q1_chart", on_select="rerun", selection_mode="points")

    with st.expander("Optional: move nodes by hand"):
        st.write("Edit an x or y value to move a node. Press the button to go back to the grid.")
        table = pd.DataFrame({"node": [f"N{i + 1}" for i in range(net.n)], "x (metres)": nodes[:, 0],
                              "y (metres)": nodes[:, 1]}).set_index("node")
        edited = st.data_editor(table, key=f"q1-editor-{area}-{spacing}", width="stretch", height=260,
                                column_config={c: st.column_config.NumberColumn(c, min_value=0.0,
                                                                                max_value=float(area), step=1.0)
                                               for c in table.columns})
        new_positions = edited.to_numpy(float)
        if not np.allclose(new_positions, nodes):
            st.session_state[f"q1-moved-{area}-{spacing}"] = new_positions
            st.rerun()
        if st.button("Reset to the grid"):
            st.session_state.pop(f"q1-moved-{area}-{spacing}", None)
            st.session_state.pop(f"q1-editor-{area}-{spacing}", None)
            st.rerun()


# ====================================================================== Question 2
LANE_Y = {"A": "Sensor A", "AP": "Access Point", "B": "Sensor B"}
Q2_SCENARIOS = {
    "Without RTS/CTS (Request to Send / Clear to Send)": dict(
        events=q2.HIDDEN_EVENTS, end=32, video="q2_hidden.mp4",
        steps=["A senses the channel idle and sends its DATA frame.",
               "B cannot hear A, so B also senses the channel idle and sends.",
               "Both frames overlap at the AP (Access Point): collision.",
               "No ACK (Acknowledgement) arrives, so both sensors must send again."],
        result="Collision: both readings are lost and must be resent."),
    "With RTS/CTS (Request to Send / Clear to Send)": dict(
        events=q2.RTS_CTS_EVENTS, end=44, video="q2_rtscts.mp4",
        steps=["A sends a short RTS (Request to Send) to the AP (Access Point).",
               "The AP replies CTS (Clear to Send) to A; B overhears it and waits (NAV, Network Allocation Vector).",
               "A sends its DATA safely; the AP replies with ACK (Acknowledgement).",
               "B's waiting time ends and B sends its own reading the same way."],
        result="No collision: B waits, and both readings are delivered."),
}


def q2_timeline(events, end):
    fig = go.Figure()
    for lane, start, stop, label, colour, *_ in events:
        fig.add_trace(go.Bar(y=[LANE_Y[lane]], x=[stop - start], base=[start], orientation="h", showlegend=False,
                             marker=dict(color=colour, line=dict(color="black", width=0.6)),
                             text=[label if stop - start >= 2 else ""], textposition="inside",
                             insidetextanchor="middle", textfont=dict(color="black", size=12), hoverinfo="skip"))
    fig.update_layout(font=FONT, height=250, barmode="overlay", plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(range=[0, end], title=dict(text="time", font=dict(color="black")), showgrid=False,
                                 linecolor="black", showticklabels=False),
                      yaxis=dict(categoryorder="array", categoryarray=["Sensor B", "Access Point", "Sensor A"],
                                 linecolor="black", tickfont=dict(color="black")))
    return fig


def question2():
    st.subheader("Question 2: Hidden terminals and RTS/CTS (Request to Send / Clear to Send)")
    how_to("choose a case and press play on the video. Sensors A and B both reach the AP (Access Point) but cannot "
           "hear each other.")
    choice = st.radio("Case", list(Q2_SCENARIOS), horizontal=True)
    sc = Q2_SCENARIOS[choice]
    left, right = st.columns([1.15, 1])
    with left:
        st.video(str(ROOT / "media" / "videos" / sc["video"]))
    with right:
        st.markdown("**What happens:**")
        st.markdown("\n".join(f"{k}. {step}" for k, step in enumerate(sc["steps"], 1)))
        st.markdown(f"**Result:** {sc['result']}")
    st.markdown("**Timing of the whole exchange:**")
    st.plotly_chart(q2_timeline(sc["events"], sc["end"]), width="stretch")


# ====================================================================== Question 3
@st.cache_data
def q3_model(n_nodes):
    net = q3.build_network(n_nodes=n_nodes)
    return net, q3.transmissions_per_round(net)


def q3_figure(net):
    pos = net.positions
    fig = go.Figure()
    mx, my = [], []
    for m, h in zip(net.members, net.member_head):
        mx += [pos[m][0], pos[h][0], None]
        my += [pos[m][1], pos[h][1], None]
    fig.add_trace(go.Scattergl(x=mx, y=my, mode="lines", line=dict(color="#86b6ef", width=1), hoverinfo="skip",
                               name="Sensor to its cluster head"))
    rx, ry = [], []
    for a, b in q3.route_segments(net, net.heads):
        rx += [a[0], b[0], None]
        ry += [a[1], b[1], None]
    fig.add_trace(go.Scattergl(x=rx, y=ry, mode="lines", line=dict(color=VIOLET, width=2), opacity=0.6,
                               hoverinfo="skip", name="Route to the base station"))
    fig.add_trace(go.Scattergl(x=pos[net.members, 0], y=pos[net.members, 1], mode="markers", hoverinfo="skip",
                               marker=dict(size=5, color=BLUE), name="Sensor"))
    fig.add_trace(go.Scattergl(x=pos[net.heads, 0], y=pos[net.heads, 1], mode="markers", hoverinfo="skip",
                               marker=dict(symbol="star", size=12, color=ORANGE, line=dict(color="black", width=0.6)),
                               name="Cluster head (combines readings)"))
    fig.add_trace(go.Scatter(x=[net.base[0]], y=[net.base[1]], mode="markers", hoverinfo="skip",
                             marker=dict(symbol="triangle-up", size=20, color="black"), name="Base station"))
    fig.add_shape(type="rect", x0=0, y0=0, x1=net.size, y1=net.size, line=dict(color="black", width=1))
    return plot_layout(fig, [-40, net.size + 40], [-80, net.size + 40])


def question3():
    st.subheader("Question 3: Forest-fire WSN (Wireless Sensor Network)")
    how_to("move the slider to change the number of sensors in the 2 km × 2 km forest. Cluster heads (stars) combine "
           "their sensors' readings and forward them over several hops to the base station.")
    n_nodes = st.slider("Number of sensors", 200, 2000, 1000, 100)
    net, tx = q3_model(n_nodes)
    without, with_agg = tx["clustered_no_aggregation"], tx["clustered_aggregation"]
    m = st.columns(3)
    m[0].metric("Transmissions per round without aggregation", f"{without:,}")
    m[1].metric("Transmissions per round with aggregation", f"{with_agg:,}")
    m[2].metric("Transmissions saved by aggregation", f"{100 * (without - with_agg) / without:.0f} %")
    st.plotly_chart(q3_figure(net), width="stretch")


# ====================================================================== page
QUESTIONS = {"1": ("Question 1 — IoT grid", question1),
             "2": ("Question 2 — RTS/CTS (Request to Send / Clear to Send)", question2),
             "3": ("Question 3 — Forest WSN (Wireless Sensor Network)", question3)}

st.title("IT863 Internet of Things — Assignment 01: Simulations")
st.write("Military College of Signals, NUST (National University of Sciences and Technology) • "
         "MSSE 32 • Ali Hamza (536657) • "
         f"Instructor: Prof. Dr. Javed Iqbal • [Source code on GitHub]({REPO_URL})")

start_q = st.query_params.get("q", "1")
chosen = st.radio("Simulation", list(QUESTIONS), index=list(QUESTIONS).index(start_q) if start_q in QUESTIONS else 0,
                  format_func=lambda k: QUESTIONS[k][0], horizontal=True, label_visibility="collapsed")
st.query_params["q"] = chosen
st.divider()
QUESTIONS[chosen][1]()
