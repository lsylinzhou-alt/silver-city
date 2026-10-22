"""Compare additive proxy allocation and network-aware allocation on 3 budgets.

To run with a real field-survey package, provide three CSV inputs that have
already been anonymized and manually reviewed. No input is downloaded.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from core.data import load_data
from core.risk import evaluate
from core.optimizer import optimize
from core.survey_network import sample_network, validate_network, evaluate_access, choose_access_budget


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", type=Path, default=None, help="survey node CSV")
    ap.add_argument("--edges", type=Path, default=None, help="survey edge CSV")
    ap.add_argument("--projects", type=Path, default=None, help="survey project CSV")
    args = ap.parse_args()
    supplied = [args.nodes, args.edges, args.projects]
    if any(v is not None for v in supplied) and not all(v is not None for v in supplied):
        ap.error("Actual-case run requires --nodes, --edges, and --projects together")
    is_survey = all(v is not None for v in supplied)
    if is_survey:
        nodes = pd.read_csv(args.nodes, encoding="utf-8-sig", keep_default_na=False)
        edges = pd.read_csv(args.edges, encoding="utf-8-sig", keep_default_na=False)
        raw = pd.read_csv(args.projects, encoding="utf-8-sig", keep_default_na=False)
        if not {"source_type", "verified"}.issubset(raw.columns):
            raise ValueError("Survey project CSV must contain source_type and verified")
        raw = raw[(raw["source_type"] == "实地调查") &
                  (raw["verified"].astype(str).str.lower().isin(["true", "1", "yes"]))]
        if raw.empty:
            raise ValueError("No verified field-survey projects in the supplied CSV")
    else:
        nodes, edges = sample_network()
        raw = load_data()
    validate_network(nodes, edges)
    rated = evaluate(raw)
    if len(rated) > 12:
        raise ValueError("Use <= 12 projects; explicitly select a shortlist before experiments")
    records = []
    for profile in ["一般步行", "助行器", "轮椅"]:
        before = evaluate_access(nodes, edges, profile, verified_only=is_survey)
        for budget in [3.0, 5.0, 10.0]:
            traditional = optimize(rated, budget)
            enhanced = choose_access_budget(rated, nodes, edges, budget, profile,
                                             bonus=260.0, fairness_bonus=80.0,
                                             verified_only=is_survey)
            basic_ids = [str(r["id"]) for r in traditional["selected"]]
            basic_metrics = evaluate_access(nodes, edges, profile, basic_ids,
                                            verified_only=is_survey)
            for name, cost, benefit, cov, min_cov, ids in [
                ("Before", 0.0, 0.0, before["coverage_pct"], before["min_home_pct"], ""),
                ("Proxy", traditional["cost_wan"], traditional["benefit_score"],
                 basic_metrics["coverage_pct"], basic_metrics["min_home_pct"], ",".join(basic_ids)),
                ("Spatial", enhanced["cost_wan"], enhanced["benefit_score"],
                 enhanced["coverage_pct"], enhanced["min_home_pct"], ",".join(enhanced["selected_ids"])),
            ]:
                records.append({
                    "scenario": "field-survey" if is_survey else "synthetic-demo",
                    "profile": profile, "budget_wan": budget, "method": name,
                    "cost_wan": cost, "proxy_benefit_score": benefit,
                    "route_coverage_pct": round(cov, 2),
                    "min_home_coverage_pct": round(min_cov, 2),
                    "project_ids": ids,
                })
    output = pd.DataFrame(records)
    results = ROOT / "outputs" / "results"
    charts = ROOT / "outputs" / "charts"
    results.mkdir(parents=True, exist_ok=True)
    charts.mkdir(parents=True, exist_ok=True)
    filename = "field_network_experiment" if is_survey else "demo_network_experiment"
    csv_path = results / f"{filename}.csv"
    output.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Use English axis labels for robust font coverage.
    subset = output[(output["profile"] == "轮椅") & (output["budget_wan"] == 10.0)]
    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    ax.bar(subset["method"], subset["route_coverage_pct"])
    ax.set_ylabel("Accessible OD pairs (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Wheelchair routing: budget 100,000 CNY")
    ax.set_xlabel("Budget decision method")
    fig.tight_layout()
    fig_path = charts / f"{filename}.png"
    fig.savefig(fig_path, dpi=170)
    plt.close(fig)
    print("Analysis source:", "verified field-survey CSV" if is_survey else "SYNTHETIC DEMO ONLY")
    print("Saved:", csv_path)
    print("Saved:", fig_path)
    print("Rows:", len(output))

if __name__ == "__main__":
    main()
