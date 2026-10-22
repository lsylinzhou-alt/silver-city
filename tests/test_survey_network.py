import pandas as pd
from core.survey_network import (
    sample_network, evaluate_access, choose_access_budget,
    explain_marginal_effect, validate_network,
)
from core.data import load_data
from core.risk import evaluate


def test_sample_roles_and_fields():
    nodes, edges = sample_network()
    assert validate_network(nodes, edges)
    assert len(nodes) == 9 and len(edges) == 10


def test_profiles_differ_for_sample():
    nodes, edges = sample_network()
    ordinary = evaluate_access(nodes, edges, "一般步行")
    wheelchair = evaluate_access(nodes, edges, "轮椅")
    assert ordinary["reachable_pairs"] >= wheelchair["reachable_pairs"]
    assert wheelchair["total_pairs"] == 9


def test_repairs_cannot_reduce_accessibility():
    nodes, edges = sample_network()
    before = evaluate_access(nodes, edges, "轮椅")
    after = evaluate_access(nodes, edges, "轮椅", {"P001", "P007", "P009"})
    assert after["reachable_pairs"] >= before["reachable_pairs"]
    assert after["min_home_pct"] >= before["min_home_pct"]


def test_budget_feasible():
    nodes, edges = sample_network()
    rated = evaluate(load_data())
    result = choose_access_budget(rated, nodes, edges, 5.0, "轮椅")
    assert result["cost_wan"] <= 5.0 + 1e-9
    assert result["coverage_pct"] >= evaluate_access(nodes, edges, "轮椅")["coverage_pct"]


def test_marginal_output():
    nodes, edges = sample_network()
    explanation = explain_marginal_effect(nodes, edges, "轮椅", {"P001", "P007"})
    assert set(explanation["项目编号"]) == {"P001", "P007"}
    assert (explanation["不选该项将减少的可通行链"] >= 0).all()


def test_verified_only_needs_verified_edges():
    nodes, edges = sample_network()
    before = evaluate_access(nodes, edges, "轮椅", verified_only=False)
    after = evaluate_access(nodes, edges, "轮椅", verified_only=True)
    assert after["reachable_pairs"] <= before["reachable_pairs"]


def test_unknown_node_rejected():
    nodes, edges = sample_network()
    edges.loc[0, "start"] = "ghost"
    try:
        validate_network(nodes, edges)
        assert False, "expected validation error"
    except ValueError:
        pass
