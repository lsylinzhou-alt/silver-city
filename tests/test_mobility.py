import pandas as pd
from core.mobility import accessibility_metrics, find_route
from core.route_optimizer import choose_spatially
from core.risk import evaluate
from core.data import seed_rows
from core.optimizer import optimize


def test_synthetic_route_improves_when_barrier_fixed():
    baseline = accessibility_metrics()
    improved = accessibility_metrics(["P001", "P007", "P009"])
    assert baseline["reachable_pairs"] < improved["reachable_pairs"]
    assert improved["reachable_pairs"] == improved["total_pairs"] == 9


def test_no_route_is_reported_as_missing():
    before, length = find_route("h2", "clinic", [])
    assert before == [] and length is None
    after, length2 = find_route("h2", "clinic", ["P001", "P007"])
    assert after and length2 > 0


def test_spatial_optimizer_respects_budget():
    df = evaluate(pd.DataFrame(seed_rows()))
    answer = choose_spatially(df, 5.0, spatial_bonus=300)
    assert answer["cost_wan"] <= 5.0
    assert answer["coverage_pct"] >= accessibility_metrics()["coverage_pct"]


def test_spatial_weight_zero_is_equivalent_to_proxy_optimum():
    df = evaluate(pd.DataFrame(seed_rows()))
    result = choose_spatially(df, 5.0, spatial_bonus=0)
    traditional = optimize(df, 5.0)
    assert result["benefit_score"] == traditional["benefit_score"]


def test_cloud_data_format_retained():
    rows = pd.DataFrame(seed_rows())
    assert {"source_type", "verified", "photo_path"}.issubset(rows.columns)
