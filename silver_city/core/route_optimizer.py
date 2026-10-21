"""Small-instance spatially aware budget selection.

A multi-objective proof of concept: maximize the sum of proxy scores plus a
spatial accessibility bonus. The spatial bonus is explicitly an assumption.
This enumerates subsets (N<=16), and should NOT be used at city scale.
"""
from itertools import combinations
from core.mobility import accessibility_metrics
from core.optimizer import summarize, to_units


def choose_spatially(df, budget_wan, spatial_bonus=280.0):
    if budget_wan < 0:
        raise ValueError("预算不能为负")
    if spatial_bonus < 0:
        raise ValueError("空间改善奖励系数不能为负")
    records = df.to_dict("records")
    if len(records) > 16:
        raise ValueError("空间联动演示版最多16个候选项目")
    limit = to_units(budget_wan)
    before = accessibility_metrics()["coverage_pct"]
    best_score = float("-inf")
    best_cost = float("inf")
    best_choice = ()
    best_coverage = before

    for length in range(len(records) + 1):
        for choices in combinations(records, length):
            spent = sum(to_units(row["cost_wan"]) for row in choices)
            if spent > limit:
                continue
            coverage = accessibility_metrics(row["id"] for row in choices)["coverage_pct"]
            proxy = sum(float(row["benefit_score"]) for row in choices)
            objective = proxy + spatial_bonus * (coverage - before) / 100.0
            if (objective > best_score + 1e-9 or
                    (abs(objective - best_score) <= 1e-9 and spent < best_cost)):
                best_score = objective
                best_cost = spent
                best_choice = choices
                best_coverage = coverage

    result = summarize(list(best_choice))
    result.update({
        "coverage_pct": round(best_coverage, 2),
        "objective_value": round(best_score, 2),
        "spatial_bonus": spatial_bonus,
    })
    return result
