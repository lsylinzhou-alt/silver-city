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
