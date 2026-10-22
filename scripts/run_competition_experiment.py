
"""银龄智城：研究生竞赛算法对比实验。

比较四种预算决策方法。
默认使用内置模拟数据，不代表真实社区改造效果。
"""

from pathlib import Path
import sys

# 获取项目根目录，保证能够导入core模块
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from core.data import load_data
from core.risk import evaluate
from core.optimizer import greedy, to_units

from core.survey_network import (
    PROFILES,
    sample_network,
    evaluate_access,
    choose_access_budget,
    choose_joint_budget,
    minimum_service_guarantee,
)

# =====================================
# 1. 实验参数
# =====================================

BUDGETS = [3.0, 5.0, 10.0]

# 当前为模拟实验
VERIFIED_ONLY = False

METHODS = {
    "严重度优先": "Severity-first",
    "轮椅单档案优化": "Wheelchair-only",
    "三群体联合优化": "Joint-3-profiles",
    "最低保障组合": "Minimum-guarantee",
}


def main():

    # =====================================
    # 2. 读取数据
    # =====================================

    projects = evaluate(load_data())
    nodes, edges = sample_network()

    if projects.empty or len(projects) > 12:
        raise ValueError(
            "实验需要1到12条候选项目"
        )

    if projects["id"].astype(str).duplicated().any():
        raise ValueError("项目编号不能重复")

    by_id = {
        str(r["id"]): r
        for r in projects.to_dict("records")
    }

    # 计算最低保障的理论成本
    guarantee = minimum_service_guarantee(
        projects,
        nodes,
        edges,
        budget_wan=max(BUDGETS),
        verified_only=VERIFIED_ONLY
    )

    guarantee_min = guarantee.get(
        "minimum_cost_wan"
    )

    output_rows = []

    # =====================================
    # 3. 统一评价函数
    # =====================================

    def add_result(budget, method, ids):

        ids = [str(i) for i in ids]

        missing = set(ids) - set(by_id)

        if missing:
            raise ValueError(
                f"存在未知改造项目：{missing}"
            )

        used_units = sum(
            to_units(by_id[i]["cost_wan"])
            for i in ids
        )

        if used_units > to_units(budget):
            raise AssertionError(
                f"{method}超出预算{budget}万元"
            )

        # 在同一组项目下评价三类档案
        scores = [
            evaluate_access(
                nodes,
                edges,
                p,
                ids,
                VERIFIED_ONLY
            )
            for p in PROFILES
        ]

        mean_cover = sum(
            x["coverage_pct"] for x in scores
        ) / len(scores)

        worst_group = min(
            x["coverage_pct"] for x in scores
        )

        worst_home = min(
            x["min_home_pct"] for x in scores
        )

        all_routes = sum(
            x["reachable_pairs"] for x in scores
        )

        proxy_score = sum(
            float(by_id[i]["benefit_score"])
            for i in ids
        )

        output_rows.append({
            "预算_万元": budget,
            "方法": method,
            "状态": "预算内可执行",
            "项目编号": "、".join(ids) or "未选择项目",
            "实际支出_万元": used_units / 100,
            "代理收益分": round(proxy_score, 2),
            "三群体平均可通行率_%": round(
                mean_cover, 2
            ),
            "最弱群体可通行率_%": round(
                worst_group, 2
            ),
            "最弱楼栋可通行率_%": round(
                worst_home, 2
            ),
            "总可通行出行链数": all_routes,
            "满足每栋至少一个目的地": (
                "是" if worst_home > 0 else "否"
            ),
            "最低保障理论成本_万元": guarantee_min,
        })

    # =====================================
    # 4. 三档预算对比
    # =====================================

    for budget in BUDGETS:

        # 方法A：严重度优先
        severity = greedy(
            projects,
            budget,
            "severity"
        )

        # 方法B：轮椅单档案优化
        single = choose_access_budget(
            projects,
            nodes,
            edges,
            budget,
            profile="轮椅",
            verified_only=VERIFIED_ONLY
        )

        # 方法C：三群体联合优化
        joint = choose_joint_budget(
            projects,
            nodes,
            edges,
            budget,
            verified_only=VERIFIED_ONLY
        )

        add_result(
            budget,
            "严重度优先",
            [r["id"] for r in severity["selected"]]
        )

        add_result(
            budget,
            "轮椅单档案优化",
            single["selected_ids"]
        )

        add_result(
            budget,
            "三群体联合优化",
            joint["selected_ids"]
        )

        # 方法D：最低保障方案
        if (
            guarantee["possible"]
            and to_units(guarantee_min) <= to_units(budget)
        ):

            add_result(
                budget,
                "最低保障组合",
                guarantee["selected_ids"]
            )

        else:

            output_rows.append({
                "预算_万元": budget,
                "方法": "最低保障组合",
                "状态": (
                    "预算不足，不可执行"
                    if guarantee["possible"]
                    else "现有项目无法满足保障"
                ),
                "项目编号": "未采用",
                "实际支出_万元": None,
                "代理收益分": None,
                "三群体平均可通行率_%": None,
                "最弱群体可通行率_%": None,
                "最弱楼栋可通行率_%": None,
                "总可通行出行链数": None,
                "满足每栋至少一个目的地": "不适用",
                "最低保障理论成本_万元": guarantee_min,
            })

    # =====================================
    # 5. 导出CSV结果
    # =====================================

    result_dir = ROOT / "outputs" / "results"
    chart_dir = ROOT / "outputs" / "charts"

    result_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    chart_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    report = pd.DataFrame(output_rows)

    csv_path = (
        result_dir / "competition_experiment.csv"
    )

    report.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    # =====================================
    # 6. 绘制论文式对比图
    # =====================================

    usable = report[
        report["状态"] == "预算内可执行"
    ]

    chart_configs = [
        (
            "三群体平均可通行率_%",
            "Average accessibility - simulation",
            "competition_average.png"
        ),
        (
            "最弱楼栋可通行率_%",
            "Worst-home accessibility - simulation",
            "competition_worst_home.png"
        )
    ]

    for field, title, filename in chart_configs:

        fig, ax = plt.subplots(
            figsize=(8, 4.8)
        )

        for cn, en in METHODS.items():

            subset = usable[
                usable["方法"] == cn
            ].sort_values("预算_万元")

            if not subset.empty:

                ax.plot(
                    subset["预算_万元"],
                    subset[field],
                    marker="o",
                    label=en
                )

        ax.set(
            xlabel="Budget (10,000 CNY)",
            ylabel="Accessibility (%)",
            title=title
        )

        ax.set_xticks(BUDGETS)
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.22)
        ax.legend(fontsize=8)

        fig.tight_layout()

        fig.savefig(
            chart_dir / filename,
            dpi=170
        )

        plt.close(fig)

    # =====================================
    # 7. 终端输出
    # =====================================

    print("竞赛实验完成")
    print("注意：当前使用模拟路网")

    print(
        "最低保障理论成本：",
        guarantee_min,
        "万元"
    )

    print("实验CSV：", csv_path)
    print("实验图表目录：", chart_dir)

    print(
        report[
            [
                "预算_万元",
                "方法",
                "状态",
                "实际支出_万元",
                "三群体平均可通行率_%",
                "最弱楼栋可通行率_%"
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()