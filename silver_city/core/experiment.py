"""Baseline experiment: three methods on the same fixed candidate set."""
import pandas as pd
from core.optimizer import greedy, optimize


def comparison(df: pd.DataFrame, budget_wan: float):
    plans = [
        ("A 严重度优先", greedy(df, budget_wan, "severity")),
        ("B 收益成本比", greedy(df, budget_wan, "ratio")),
        ("C 组合优化", optimize(df, budget_wan)),
    ]
    output = []
    for name, result in plans:
        output.append({
            "方案": name,
            "投入(万元)": result["cost_wan"],
            "估计收益分": result["benefit_score"],
            "高风险点数量": result["high_count"],
            "项目数": result["count"],
            "预算利用率(%)": round(100 * result["cost_wan"] / budget_wan, 1)
                if budget_wan > 0 else 0.0,
            "选中编号": ", ".join(str(p["id"]) for p in result["selected"]),
        })
    return pd.DataFrame(output)
