"""Run baseline comparisons and export reproducible CSV and PNG files."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from core.data import load_data
from core.risk import evaluate
from core.experiment import comparison
from core.optimizer import optimize

output_csv = ROOT / "outputs" / "results" / "experiment_comparison.csv"
output_fig = ROOT / "outputs" / "charts" / "experiment_comparison.png"
output_weights = ROOT / "outputs" / "results" / "sensitivity.csv"
for f in [output_csv, output_fig, output_weights]:
    f.parent.mkdir(parents=True, exist_ok=True)

base = load_data()
if base.empty:
    raise SystemExit("No records to evaluate")

data = evaluate(base)
records = []
for budget in [3.0, 5.0, 10.0]:
    result = comparison(data, budget)
    result.insert(0, "预算(万元)", budget)
    records.append(result)
comparison_df = pd.concat(records, ignore_index=True)
comparison_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

# English chart labels avoid missing Chinese glyphs in Matplotlib.
fig, ax = plt.subplots(figsize=(8, 4.6))
methods = ["A: Severity", "B: Benefit/Cost", "C: Optimized"]
for idx, budget in enumerate([3.0, 5.0, 10.0]):
    subset = comparison_df[comparison_df["预算(万元)"] == budget]
    vals = subset["估计收益分"].tolist()
    xs = [0 + idx*0.24, 1 + idx*0.24, 2 + idx*0.24]
    ax.bar(xs, vals, width=0.22, label=f"Budget {budget:g}")
ax.set_xticks([0.24, 1.24, 2.24], methods)
ax.set_ylabel("Estimated benefit score (proxy)")
ax.set_title("Demo: Budget allocation baselines")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(output_fig, dpi=170)
plt.close(fig)

weights = []
for weight in [0.25, 0.35, 0.45]:
    rated = evaluate(base, severity_weight=weight)
    sol = optimize(rated, 5.0)
    weights.append({
        "severity_weight": weight,
        "selected_ids": ",".join(str(x["id"]) for x in sol["selected"]),
        "selected_count": sol["count"],
        "cost_wan": sol["cost_wan"],
    })
pd.DataFrame(weights).to_csv(output_weights, index=False, encoding="utf-8-sig")

print("Saved:")
print(output_csv)
print(output_fig)
print(output_weights)
print("IMPORTANT: Source records marked '模拟' are synthetic, not field evidence.")
