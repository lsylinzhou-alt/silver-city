"""Small, explicit community path model for age-friendly budget experiments.

All graph geometry and barrier labels are manually supplied. A record is not
an objective engineering certification of accessibility. Uploaded data remains
in the user's Streamlit browser session; this module performs no persistence.
"""
from itertools import combinations
from pathlib import Path
import networkx as nx
import pandas as pd
from core.optimizer import to_units

ROOT = Path(__file__).resolve().parents[1]
NODE_COLUMNS = ["node_id", "name", "lat", "lon", "kind"]
EDGE_COLUMNS = ["start", "end", "length_m", "blocked_for", "repair_project_id", "verified"]
PROFILES = ["一般步行", "助行器", "轮椅"]
DESTINATION_KINDS = {"卫生站", "公交站", "菜市场", "公共服务", "便利店"}


def sample_network():
    nodes = pd.read_csv(ROOT / "data" / "sample_nodes.csv", encoding="utf-8-sig", keep_default_na=False)
    edges = pd.read_csv(ROOT / "data" / "sample_edges.csv", encoding="utf-8-sig", keep_default_na=False)
    return nodes, edges


def _is_true(x):
    return str(x).strip().lower() in {"true", "1", "yes", "是", "已核验"}


def validate_network(nodes, edges):
    missing_nodes = set(NODE_COLUMNS) - set(nodes.columns)
    missing_edges = set(EDGE_COLUMNS) - set(edges.columns)
    if missing_nodes or missing_edges:
        raise ValueError(f"缺少必要列：节点 {sorted(missing_nodes)}，道路 {sorted(missing_edges)}")
    if len(nodes) == 0 or len(edges) == 0:
        raise ValueError("节点表和道路表都不能为空")
    ids = nodes["node_id"].astype(str).str.strip()
    if (ids == "").any() or ids.duplicated().any():
        raise ValueError("node_id 不得为空或重复")
    known = set(ids)
    for _, e in edges.iterrows():
        a, b = str(e["start"]).strip(), str(e["end"]).strip()
        if a not in known or b not in known or a == b:
            raise ValueError(f"无效道路：{a} -> {b}；检查节点编号")
        try:
            dist = float(e["length_m"])
        except (TypeError, ValueError):
            raise ValueError(f"道路 {a}-{b} 的 length_m 不是数字")
        if not 0 < dist < 100000:
            raise ValueError(f"道路 {a}-{b} 长度必须大于0")
        restrictions = {x.strip() for x in str(e["blocked_for"]).split(";") if x.strip()}
        unexpected = restrictions - set(PROFILES)
        if unexpected:
            raise ValueError(f"道路 {a}-{b} 含未知使用档案 {unexpected}")
    for _, n in nodes.iterrows():
        try:
            lat, lon = float(n["lat"]), float(n["lon"])
        except (TypeError, ValueError):
            raise ValueError(f"节点 {n['node_id']} 坐标不是数字")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"节点 {n['node_id']} 坐标超出范围")
    if not any(nodes["kind"].isin(["住宅"])) or not any(nodes["kind"].isin(DESTINATION_KINDS)):
        raise ValueError("至少需要1个住宅节点和1个生活服务目的地")
    return True


def make_survey_graph(nodes, edges, profile, finished=(), verified_only=False):
    if profile not in PROFILES:
        raise ValueError("未知通行能力档案")
    validate_network(nodes, edges)
    done = set(map(str, finished))
    g = nx.Graph()
    for _, n in nodes.iterrows():
        g.add_node(str(n["node_id"]), name=str(n["name"]), kind=str(n["kind"]),
                   lat=float(n["lat"]), lon=float(n["lon"]))
    for _, e in edges.iterrows():
        if verified_only and not _is_true(e["verified"]):
            continue
        restricted = {x.strip() for x in str(e["blocked_for"]).split(";") if x.strip()}
        project_id = str(e["repair_project_id"]).strip()
        if profile in restricted and (not project_id or project_id not in done):
            continue
        g.add_edge(str(e["start"]), str(e["end"]), weight=float(e["length_m"]), project_id=project_id)
    return g


def evaluate_access(nodes, edges, profile="轮椅", finished=(), verified_only=False):
    g = make_survey_graph(nodes, edges, profile, finished, verified_only)
    homes = nodes[nodes["kind"] == "住宅"].to_dict("records")
    destinations = nodes[nodes["kind"].isin(DESTINATION_KINDS)].to_dict("records")
    results = []
    per_home_pct = {}
    for home in homes:
        name = str(home["node_id"])
        dists, paths = nx.single_source_dijkstra(g, name, weight="weight")
        reach_count = 0
        for dest in destinations:
            end = str(dest["node_id"])
            reached = end in dists
            reach_count += int(reached)
            results.append({
                "origin_id": name, "origin": str(home["name"]),
                "destination_id": end, "destination": str(dest["name"]),
                "reachable": bool(reached),
                "distance_m": round(float(dists[end]), 1) if reached else None,
                "route": paths[end] if reached else [],
            })
        per_home_pct[str(home["name"])] = 100 * reach_count / len(destinations)
    n_reachable = sum(int(r["reachable"]) for r in results)
    return {
        "reachable_pairs": n_reachable,
        "total_pairs": len(results),
        "coverage_pct": 100 * n_reachable / len(results),
        "min_home_pct": min(per_home_pct.values()),
        "per_home_pct": per_home_pct,
        "routes": results,
    }


def choose_access_budget(projects, nodes, edges, budget_wan, profile="轮椅",
                         bonus=260.0, fairness_bonus=80.0, verified_only=False):
    """Exact enumeration <=12 projects; coverage is non-additive across projects."""
    if budget_wan < 0 or bonus < 0 or fairness_bonus < 0:
        raise ValueError("预算和权重必须为非负数")
    rows = projects.to_dict("records")
    if len(rows) > 12:
        raise ValueError("本演示优化器最多处理12个候选项目，请先筛选项目")
    baseline = evaluate_access(nodes, edges, profile, (), verified_only)
    base_coverage, base_min = baseline["coverage_pct"], baseline["min_home_pct"]
    limit = to_units(budget_wan)
    best = None
    cached = {}
    for size in range(len(rows) + 1):
        for selected in combinations(rows, size):
            cost_units = sum(to_units(r["cost_wan"]) for r in selected)
            if cost_units > limit:
                continue
            ids = frozenset(str(r["id"]) for r in selected)
            if ids not in cached:
                cached[ids] = evaluate_access(nodes, edges, profile, ids, verified_only)
            cov = cached[ids]
            proxy = sum(float(r["benefit_score"]) for r in selected)
            utility = proxy + bonus * (cov["coverage_pct"] - base_coverage) / 100.0 + fairness_bonus * (cov["min_home_pct"] - base_min) / 100.0
            candidate = (utility, -cost_units, tuple(str(r["id"]) for r in selected))
            if best is None or candidate[:2] > best[0][:2]:
                best = (candidate, list(selected), cost_units, cov, proxy)
    _, choice, spent, summary, proxy = best
    return {
        "selected": choice, "selected_ids": [str(r["id"]) for r in choice],
        "cost_wan": round(spent / 100.0, 2), "benefit_score": round(proxy, 2),
        "objective_value": round(best[0][0], 2),
        "coverage_pct": round(summary["coverage_pct"], 2),
        "min_home_pct": round(summary["min_home_pct"], 2),
    }


def explain_marginal_effect(nodes, edges, profile, selected_ids, verified_only=False):
    """Each row is the leave-one-project-out effect within the final package."""
    ids = set(map(str, selected_ids))
    all_metrics = evaluate_access(nodes, edges, profile, ids, verified_only)
    rows = []
    for project_id in sorted(ids):
        without = evaluate_access(nodes, edges, profile, ids - {project_id}, verified_only)
        without_routes = {(r["origin_id"], r["destination_id"]): r["reachable"] for r in without["routes"]}
        gained = [f"{r['origin']}→{r['destination']}" for r in all_metrics["routes"]
                  if r["reachable"] and not without_routes[(r["origin_id"], r["destination_id"])]]
        rows.append({
            "项目编号": project_id,
            "不选该项将减少的可通行链": len(gained),
            "具体链路": "、".join(gained) if gained else "无新增连通链（可能有其他收益）",
        })
    return pd.DataFrame(rows)



# ============================================
# 多群体公平性导向的预算协同优化
# ============================================

def choose_joint_budget(
    projects, nodes, edges, budget_wan,
    bonus=260.0,
    fairness_bonus=80.0,
    verified_only=False
):
    """
    在同一预算内，联合考虑三种通行能力。
    精确枚举最多12个候选改造项目。
    """

    if budget_wan < 0 or bonus < 0 or fairness_bonus < 0:
        raise ValueError("预算和权重不能为负数")

    required = {"id", "cost_wan", "benefit_score"}
    if not required.issubset(projects.columns):
        raise ValueError(
            f"项目表缺少列：{sorted(required - set(projects.columns))}"
        )

    if len(projects) > 12:
        raise ValueError("联合优化演示最多支持12个候选项目")

    if projects["id"].astype(str).duplicated().any():
        raise ValueError("项目编号不得重复")

    validate_network(nodes, edges)

    rows = projects.to_dict("records")
    costs = [to_units(row["cost_wan"]) for row in rows]

    if any(cost <= 0 for cost in costs):
        raise ValueError("项目成本必须大于0")

    limit = to_units(budget_wan)

    # 1. 计算三类群体的改造前状态
    before = {
        p: evaluate_access(nodes, edges, p, (), verified_only)
        for p in PROFILES
    }

    mean_before = (
        sum(x["coverage_pct"] for x in before.values())
        / len(PROFILES)
    )

    worst_before = min(
        x["coverage_pct"] for x in before.values()
    )

    # 2. 识别真正关联道路阻断的改造项目
    linked_ids = {
        str(x).strip()
        for x in edges["repair_project_id"]
        if str(x).strip()
    }

    # 缓存相同道路改造组合的可达性结果
    access_cache = {}
    best = None

    # 3. 枚举预算允许的项目组合
    for size in range(len(rows) + 1):

        for picked in combinations(range(len(rows)), size):

            spent = sum(costs[i] for i in picked)

            if spent > limit:
                continue

            ids = frozenset(
                str(rows[i]["id"]) for i in picked
            )

            # 与道路无关的项目不改变路网
            key = ids & linked_ids

            if key not in access_cache:
                access_cache[key] = {
                    p: evaluate_access(
                        nodes, edges, p, key, verified_only
                    )
                    for p in PROFILES
                }

            after = access_cache[key]

            # 三类群体的平均可通行率
            mean_after = (
                sum(x["coverage_pct"] for x in after.values())
                / len(PROFILES)
            )

            # 可通行率最低群体
            worst_after = min(
                x["coverage_pct"] for x in after.values()
            )

            # 原有项目收益代理分
            proxy = sum(
                float(rows[i]["benefit_score"])
                for i in picked
            )

            # 联合目标函数
            score = (
                proxy
                + bonus * (mean_after - mean_before) / 100.0
                + fairness_bonus * (
                    worst_after - worst_before
                ) / 100.0
            )

            # 总分优先，相同总分时选择低成本组合
            if (
                best is None
                or score > best[0] + 1e-9
                or (
                    abs(score - best[0]) <= 1e-9
                    and spent < best[1]
                )
            ):
                best = (
                    score, spent, picked, after, proxy,
                    mean_after, worst_after
                )

    # 4. 整理最优结果
    (
        score, spent, picked, after, proxy,
        mean_after, worst_after
    ) = best

    group_rows = []

    for p in PROFILES:

        old = before[p]
        new = after[p]

        group_rows.append({
            "通行能力档案": p,
            "改造前可通行": old["reachable_pairs"],
            "改造后可通行": new["reachable_pairs"],
            "新增链路": (
                new["reachable_pairs"] - old["reachable_pairs"]
            ),
            "改造后可通行率(%)": round(
                new["coverage_pct"], 1
            ),
            "最低楼栋可通行率(%)": round(
                new["min_home_pct"], 1
            ),
        })

    return {
        "selected": [rows[i] for i in picked],
        "selected_ids": [
            str(rows[i]["id"]) for i in picked
        ],
        "cost_wan": round(spent / 100.0, 2),
        "benefit_score": round(proxy, 2),
        "objective_value": round(score, 2),
        "mean_before_pct": round(mean_before, 2),
        "mean_after_pct": round(mean_after, 2),
        "worst_before_pct": round(worst_before, 2),
        "worst_after_pct": round(worst_after, 2),
        "group_results": group_rows,
    }



# ============================================
# 基本生活服务可达性：最低保障预算
# ============================================

def minimum_service_guarantee(
    projects, nodes, edges,
    budget_wan=10.0,
    verified_only=False
):
    """
    在三种通行能力档案下，
    要求每栋住宅至少到达一个生活服务目的地。

    精确搜索最低成本项目组合。
    最多处理12个候选项目。
    """

    if budget_wan < 0:
        raise ValueError("预算不得小于0")

    validate_network(nodes, edges)

    required = {"id", "cost_wan"}

    if not required.issubset(projects.columns):
        raise ValueError("项目表缺少id或cost_wan字段")

    if len(projects) > 12:
        raise ValueError("最多支持12个候选项目")

    rows = projects.to_dict("records")

    ids = [
        str(r["id"]).strip()
        for r in rows
    ]

    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("项目编号不能为空或重复")

    costs = [
        to_units(r["cost_wan"])
        for r in rows
    ]

    if any(c <= 0 for c in costs):
        raise ValueError("改造成本必须大于0")

    # 获取全部住宅节点
    home_ids = nodes.loc[
        nodes["kind"] == "住宅", "node_id"
    ].astype(str).tolist()

    # 计算一个组合下三种档案的可达性
    def examine(selected):
        return {
            p: evaluate_access(
                nodes, edges, p,
                selected, verified_only
            )
            for p in PROFILES
        }

    # 检查每栋住宅是否至少能到达一个目的地
    def guaranteed(metrics):
        return all(
            any(
                r["origin_id"] == home
                and r["reachable"]
                for r in metrics[p]["routes"]
            )
            for p in PROFILES
            for home in home_ids
        )

    # 先检查全部项目实施后能否满足要求
    full_result = examine(frozenset(ids))

    if not guaranteed(full_result):
        return {
            "possible": False,
            "within_budget": False,
            "reason": (
                "即使全部候选项目实施，"
                "仍有住宅无法满足基本可达性要求"
            ),
            "minimum_cost_wan": None,
            "extra_budget_wan": None,
            "selected_ids": [],
        }

    # 搜索成本最低的保障组合
    best = None
    access_cache = {}

    linked = set(
        edges["repair_project_id"]
        .astype(str).str.strip()
    ) - {""}

    for size in range(len(rows) + 1):

        for combo in combinations(
            range(len(rows)), size
        ):

            spent = sum(
                costs[i] for i in combo
            )

            # 已找到更便宜的方案时跳过
            if best is not None and spent >= best[0]:
                continue

            chosen = frozenset(
                ids[i] for i in combo
            )

            relevant = chosen & linked

            if relevant not in access_cache:
                access_cache[relevant] = examine(
                    relevant
                )

            metrics = access_cache[relevant]

            if guaranteed(metrics):
                best = (
                    spent,
                    sorted(chosen),
                    metrics
                )

    required_cost, selected_ids, metrics = best

    budget_limit = to_units(budget_wan)

    return {
        "possible": True,

        "within_budget": (
            required_cost <= budget_limit
        ),

        "minimum_cost_wan": round(
            required_cost / 100, 2
        ),

        "extra_budget_wan": round(
            max(0, required_cost - budget_limit) / 100,
            2
        ),

        "selected_ids": selected_ids,

        "profile_coverage": {
            p: {
                "reachable_pairs":
                    value["reachable_pairs"],

                "per_home_pct":
                    value["per_home_pct"]
            }
            for p, value in metrics.items()
        }
    }


# ==============================================
# 竞赛增强：最低保障约束 + 分层公平预算优化
# ==============================================

def choose_guaranteed_joint_budget(
    projects, nodes, edges, budget_wan,
    verified_only=False
):
    """
    第一层：确保各档案下每栋住宅至少可达一个目的地
    第二层：最大化最弱楼栋可达率
    第三层：最大化三群体平均可达率
    第四层：最大化改造代理收益分
    第五层：以上相同时尽量减少成本

    适用于不超过12个候选项目的精确枚举。
    """

    # 1. 检查最低保障是否可行
    guarantee = minimum_service_guarantee(
        projects,
        nodes,
        edges,
        budget_wan=budget_wan,
        verified_only=verified_only
    )

    if not guarantee["possible"]:
        return {
            "status": "候选项目无法实现保障",
            "reason": guarantee["reason"],
            "selected_ids": [],
            "minimum_cost_wan": None
        }

    if not guarantee["within_budget"]:
        return {
            "status": "预算不足",
            "selected_ids": [],
            "minimum_cost_wan": guarantee["minimum_cost_wan"],
            "budget_gap_wan": guarantee["extra_budget_wan"]
        }

    # 2. 准备项目数据
    rows = projects.to_dict("records")
    costs = [
        to_units(r["cost_wan"])
        for r in rows
    ]

    limit = to_units(budget_wan)

    linked = set(
        edges["repair_project_id"]
        .astype(str).str.strip()
    ) - {""}

    cached = {}
    best_rank = None
    best = None

    # 3. 枚举预算内的全部项目组合
    for size in range(len(rows) + 1):

        for indexes in combinations(
            range(len(rows)), size
        ):

            spent = sum(costs[i] for i in indexes)

            if spent > limit:
                continue

            ids = frozenset(
                str(rows[i]["id"])
                for i in indexes
            )

            # 只计算真正影响路网的项目
            key = ids & linked

            if key not in cached:
                cached[key] = {
                    p: evaluate_access(
                        nodes, edges, p,
                        key, verified_only
                    )
                    for p in PROFILES
                }

            metrics = cached[key]

            # 4. 最低保障硬约束
            weakest_home = min(
                x["min_home_pct"]
                for x in metrics.values()
            )

            if weakest_home <= 0:
                continue

            # 5. 计算三群体平均覆盖
            avg = sum(
                x["coverage_pct"]
                for x in metrics.values()
            ) / len(PROFILES)

            # 6. 原有项目收益代理分
            proxy = sum(
                float(rows[i]["benefit_score"])
                for i in indexes
            )

            # 7. 分层目标：按顺序比较，不做加权相加
            rank = (
                round(weakest_home, 6),
                round(avg, 6),
                round(proxy, 6),
                -spent
            )

            if best_rank is None or rank > best_rank:
                best_rank = rank
                best = (
                    indexes, spent, metrics,
                    weakest_home, avg, proxy
                )

    if best is None:
        raise RuntimeError(
            "保障方案存在，但未搜索到符合约束的组合"
        )

    # 8. 整理推荐结果
    indexes, spent, metrics, weakest_home, avg, proxy = best

    return {
        "status": "预算内可行",

        "selected_ids": [
            str(rows[i]["id"])
            for i in indexes
        ],

        "cost_wan": round(spent / 100, 2),

        "minimum_cost_wan": guarantee["minimum_cost_wan"],

        "worst_home_pct": round(weakest_home, 2),

        "mean_coverage_pct": round(avg, 2),

        "benefit_score": round(proxy, 2),

        "profile_coverage": {
            p: round(metrics[p]["coverage_pct"], 2)
            for p in PROFILES
        }
    }
