"""Budget optimization using a 0/1 knapsack DP at 0.01 wan-yuan resolution."""
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd


def to_units(wan):
    """1 integer unit equals 0.01 ten-thousand yuan = 100 CNY."""
    return int((Decimal(str(wan)) * Decimal("100")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ))


def summarize(selection):
    if not selection:
        return {"selected": [], "cost_wan": 0.0, "benefit_score": 0.0,
                "high_count": 0, "count": 0}
    return {
        "selected": selection,
        "cost_wan": round(sum(float(r["cost_wan"]) for r in selection), 2),
        "benefit_score": round(sum(float(r["benefit_score"]) for r in selection), 2),
        "high_count": sum(r.get("risk_level") == "高" for r in selection),
        "count": len(selection),
    }


def optimize(df: pd.DataFrame, budget_wan: float):
    if budget_wan < 0:
        raise ValueError("预算不能小于0")
    rows = df.to_dict("records")
    capacity = to_units(budget_wan)
    # units -> (best objective score, picked row indices)
    states = {0: (0.0, ())}

    for index, row in enumerate(rows):
        cost = to_units(row["cost_wan"])
        if cost <= 0:
            raise ValueError("候选项目成本必须为正数")
        gain = float(row["benefit_score"])
        for spent, (value, indices) in list(states.items()):
            new_spent = spent + cost
            if new_spent > capacity:
                continue
            new_value = value + gain
            if (new_spent not in states
                    or new_value > states[new_spent][0] + 1e-9):
                states[new_spent] = (new_value, indices + (index,))

    best_spent, (_, best_ids) = max(
        states.items(), key=lambda pair: (pair[1][0], -pair[0])
    )
    return summarize([rows[i] for i in best_ids])


def greedy(df: pd.DataFrame, budget_wan: float, order: str):
    if order == "severity":
        ordered = df.sort_values(
            ["severity", "risk_score", "id"],
            ascending=[False, False, True]
        )
    elif order == "ratio":
        ordered = df.assign(
            ratio=df["benefit_score"] / df["cost_wan"]
        ).sort_values(["ratio", "id"], ascending=[False, True])
    else:
        raise ValueError("未知基线类型")
    selected, used = [], 0
    cap = to_units(budget_wan)
    for row in ordered.to_dict("records"):
        cost = to_units(row["cost_wan"])
        if cost <= 0:
            raise ValueError("候选项目成本必须为正数")
        if used + cost <= cap:
            used += cost
            selected.append(row)
    return summarize(selected)
