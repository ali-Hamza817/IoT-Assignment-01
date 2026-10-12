"""Checks that the simulations reproduce the numbers quoted in the report, and that the app runs."""
from pathlib import Path

import numpy as np
import pytest

import q1_grid_deployment as q1
import q2_rts_cts as q2
import q3_forest_fire_wsn as q3

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


# ---------------------------------------------------------------- Question 1
@pytest.fixture(scope="module")
def hops():
    return q1.hop_counts()


def test_q1_grid_and_ap_position():
    assert len(q1.NODES) == 99
    assert tuple(q1.XY[0]) == (50, 50)
    assert tuple(q1.AP) == (950, 950)


def test_q1_every_node_reaches_the_ap(hops):
    assert len(hops) == 99


def test_q1_node_links_never_exceed_100_m():
    for i in q1.NODES:
        assert all(q1.distance(i, j) <= 100 for j in q1.neighbours(i))


def test_q1_direct_nodes(hops):
    direct = {q1.name(i): round(q1.distance(i, q1.AP_INDEX), 1) for i in q1.NODES if hops[i] == 1}
    assert direct == {"N80": 200.0, "N89": 141.4, "N90": 100.0, "N98": 200.0, "N99": 100.0}


def test_q1_shortest_path_from_n1(hops):
    path = q1.shortest_path_n1(hops)
    assert [q1.name(i) for i in path[:-1]] == ["N1", "N11", "N21", "N31", "N41", "N51", "N61", "N71", "N81",
                                                "N82", "N83", "N84", "N85", "N86", "N87", "N88", "N89"]
    assert len(path) - 2 == 16          # IoT-to-IoT hops
    assert len(path) - 1 == 17          # transmissions including the final AP hop


def test_q1_every_generated_path_is_shortest(hops):
    for s in q1.NODES:
        assert len(q1.shortest_path(s, hops)) - 1 == hops[s]


def test_q1_forwarding_load(hops):
    load, flow = q1.forwarding_load(hops)
    assert sum(load[i] for i in q1.NODES if hops[i] == 1) == 99
    assert (load[79], load[97], load[88], load[0]) == (44, 36, 17, 1)    # N80, N98, N89, N1
    assert sum(v for (i, p), v in flow.items() if p == q1.AP_INDEX) == 99


# ---------------------------------------------------------------- Question 2
def test_q2_cts_is_addressed_to_a_only():
    ctses = [e for e in q2.RTS_CTS_EVENTS if e[3].startswith("CTS")]
    assert [e[3] for e in ctses] == ["CTS to A", "CTS to B"]


def test_q2_rts_cts_keeps_b_silent_while_a_sends():
    nav = [e for e in q2.RTS_CTS_EVENTS if e[0] == "B" and "NAV" in e[3]][0]
    data = [e for e in q2.RTS_CTS_EVENTS if e[0] == "A" and e[3].startswith("DATA")][0]
    assert nav[1] <= data[1] and nav[2] >= data[2]
    assert not any(e[0] == "B" and e[3].startswith("DATA") for e in q2.RTS_CTS_EVENTS)


def test_q2_hidden_terminal_frames_overlap():
    a = [e for e in q2.HIDDEN_EVENTS if e[0] == "A" and e[3].startswith("DATA")][0]
    b = [e for e in q2.HIDDEN_EVENTS if e[0] == "B" and e[3].startswith("DATA")][0]
    assert a[1] < b[2] and b[1] < a[2]


# ---------------------------------------------------------------- Question 3
@pytest.fixture(scope="module")
def network():
    return q3.build_network()


def test_q3_default_network(network):
    assert network.n == 1000
    assert len(network.heads) == 135 and len(network.members) == 865
    assert (network.hops > 0).all()


def test_q3_aggregation_reduces_transmissions(network):
    tx = q3.transmissions_per_round(network)
    assert tx["flat"] == 16279
    assert tx["clustered_aggregation"] < tx["flat"] < tx["clustered_no_aggregation"]


def test_q3_parameters_are_respected():
    net = q3.build_network(n_nodes=300, radio_range=250, head_fraction=0.2, seed=7)
    assert net.n == 300
    assert np.all(net.positions >= 0) and np.all(net.positions <= 2000)


# ---------------------------------------------------------------- interactive app
def test_app_runs_every_page_without_errors():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["IoT nodes needed"] == "99"
    assert metrics["Transmissions from N1 to the AP"] == "17"

    at.selectbox[0].set_value(44).run()                              # Question 1: packet from N45
    assert not at.exception
    sliders = {s.label: s for s in at.slider}
    sliders["Distance between nodes (metres)"].set_value(150).run()  # too far apart: nodes cut off
    assert not at.exception
    radio = {r.label: r for r in at.radio}
    radio["Show"].set_value("Traffic load").run()
    assert not at.exception

    at.radio[0].set_value("2").run()                                 # Question 2
    radio = {r.label: r for r in at.radio}
    radio["Case"].set_value("With RTS/CTS (Request to Send / Clear to Send)").run()
    assert not at.exception

    at.radio[0].set_value("3").run()                                 # Question 3
    at.slider[0].set_value(1500).run()
    assert not at.exception
    assert any("saved by aggregation" in m.label for m in at.metric)


# ---------------------------------------------------------------- general network model (environment)
def test_model_reproduces_question_1():
    import network_model as nm

    pos = nm.grid_positions(1000, 100, 50)
    net = nm.Network(pos[:-1], pos[-1], 100, 200)
    hops = q1.hop_counts()
    load, _ = q1.forwarding_load(hops)
    assert all(net.hops[i] == hops[i] for i in q1.NODES)
    assert all(net.load[i] == load[i] for i in q1.NODES)
    path = net.shortest_path(0)
    assert path is not None and len(path) - 1 == 17


def test_model_detects_unreachable_nodes():
    import network_model as nm

    net = nm.Network(np.array([(50, 50), (150, 50), (900, 900)]), np.array([1000, 1000]), 100, 200)
    assert list(net.hops) == [-1, -1, 1]
    assert net.shortest_path(0) is None
    assert net.summary()["unreachable"] == 2

