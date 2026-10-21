import pandas as pd
from core.risk import evaluate
from core.optimizer import optimize, greedy
from core.experiment import comparison


def example_df():
    return pd.DataFrame([
        {"id": "A", "cost_wan": 2.0, "benefit_score": 80.0,
         "severity": 5, "risk_score": 90.0, "risk_level": "高"},
        {"id": "B", "cost_wan": 1.0, "benefit_score": 60.0,
         "severity": 4, "risk_score": 70.0, "risk_level": "中"},
        {"id": "C", "cost_wan": 3.0, "benefit_score": 130.0,
         "severity": 5, "risk_score": 88.0, "risk_level": "高"},
    ])


def test_knapsack_finds_best_combination():
    answer = optimize(example_df(), 3.0)
    assert set(p["id"] for p in answer["selected"]) == {"A", "B"}
    assert answer["cost_wan"] == 3.0
    assert answer["benefit_score"] == 140.0


def test_decimal_budget_is_exact():
    df = example_df().iloc[:2].copy()
    df.loc[df.index[0], "cost_wan"] = 0.1
    df.loc[df.index[1], "cost_wan"] = 0.2
    answer = optimize(df, 0.3)
    assert answer["count"] == 2
    assert answer["cost_wan"] == 0.3


def test_zero_budget_selects_nothing():
    assert optimize(example_df(), 0.0)["count"] == 0


def test_risk_increases_with_severity():
    rows = pd.DataFrame([
        {"issue_type": "路面破损", "severity": 5, "people": 50,
         "frequency": 4, "improvement": 3},
        {"issue_type": "路面破损", "severity": 1, "people": 50,
         "frequency": 4, "improvement": 3},
    ])
    out = evaluate(rows)
    assert out.iloc[0]["risk_score"] > out.iloc[1]["risk_score"]


def test_three_baselines_respect_budget():
    table = comparison(example_df(), 3.0)
    assert len(table) == 3
    assert all(table["投入(万元)"] <= 3.0)
