"""Spatially aware planning demonstration; all sample roads and impacts are synthetic."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from core.data import load_data
from core.mobility import accessibility_metrics
from core.optimizer import optimize
from core.route_optimizer import choose_spatially
from core.risk import evaluate

out = ROOT / "outputs" / "results"
charts = ROOT / "outputs" / "charts"
out.mkdir(parents=True, exist_ok=True)
charts.mkdir(parents=True, exist_ok=True)

records = []
data = evaluate(load_data())
if len(data) > 16:
    raise SystemExit("Spatial experiment currently supports <=16 rows")

for budget in [3.0, 5.0, 10.0, 15.0]:
    baseline = optimize(data, budget)
    route = choose_spatially(data, budget, spatial_bonus=280)
    for label, answer in [("Proxy only", baseline), ("Proxy + route", route)]:
        cov = accessibility_metrics(row["id"] for row in answer["selected"])
        records.append({
            "budget_wan": budget,
            "algorithm": label,
            "spent_wan": answer["cost_wan"],
            "proxy_score": answer["benefit_score"],
            "accessible_chains_out_of_9": cov["reachable_pairs"],
            "coverage_percent": round(cov["coverage_pct"], 2),
            "project_ids": ",".join(str(p["id"]) for p in answer["selected"]),
            "source": "synthetic route graph and project records",
        })
frame = pd.DataFrame(records)
frame.to_csv(out / "spatial_comparison.csv", index=False, encoding="utf-8-sig")

fig, ax = plt.subplots(figsize=(8.3, 4.7))
budgets = [3.0, 5.0, 10.0, 15.0]
for i, method in enumerate(["Proxy only", "Proxy + route"]):
    values = [float(frame[(frame["budget_wan"] == b) &
                   (frame["algorithm"] == method)]["coverage_percent"].iloc[0])
              for b in budgets]
    xs = [x + (i - 0.5) * 0.32 for x in range(len(budgets))]
    ax.bar(xs, values, width=0.31, label=method)
ax.set_xticks(range(len(budgets)), [f"{b:g}" for b in budgets])
ax.set_xlabel("Budget (10k CNY)")
ax.set_ylabel("Accessible daily-trip chains (%)")
ax.set_ylim(0, 110)
ax.set_title("Synthetic neighborhood: before/after budget selection")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(charts / "spatial_comparison.png", dpi=170)
plt.close(fig)

sens = []
for reward in [0.0, 140.0, 280.0, 560.0]:
    solution = choose_spatially(data, 5.0, spatial_bonus=reward)
    sens.append({
        "spatial_bonus": reward,
        "cost_wan": solution["cost_wan"],
        "proxy_score": solution["benefit_score"],
        "coverage_percent": solution["coverage_pct"],
        "project_ids": ",".join(p["id"] for p in solution["selected"]),
    })
pd.DataFrame(sens).to_csv(out / "spatial_sensitivity.csv", index=False, encoding="utf-8-sig")
print("Synthetic spatial experiment completed:")
print(out / "spatial_comparison.csv")
print(out / "spatial_sensitivity.csv")
print(charts / "spatial_comparison.png")
