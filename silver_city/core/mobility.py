"""Demonstration-only, transparent neighborhood mobility graph.

The graph is fictional: distances, coordinates and barriers are deliberately
constructed to test whether budget choices improve complete travel chains.
It must NEVER be treated as observed GIS evidence.
"""
from functools import lru_cache
import networkx as nx

# All positions are synthetic and for drawing a miniature map only.
NODES = {
    "h1": ("2号楼", 31.23055, 121.47060),
    "h2": ("1号楼", 31.23165, 121.47130),
    "h3": ("南门住宅", 31.23005, 121.47250),
    "a": ("西侧路口", 31.23080, 121.47110),
    "b": ("社区中庭", 31.23120, 121.47180),
    "c": ("南门路口", 31.23050, 121.47210),
    "shop": ("菜市场", 31.23125, 121.47065),
    "clinic": ("社区卫生站", 31.23180, 121.47230),
    "bus": ("公交站", 31.23015, 121.47290),
}

# (start, end, representative length in metres, linked improvement project)
# P001: stair-free entrance; P007: clinic entrance; P009: south crossing.
EDGES = [
    ("h1", "a", 45, None),
    ("h2", "b", 55, "P001"),
    ("h3", "c", 60, "P009"),
    ("a", "b", 115, None),
    ("b", "c", 125, None),
    ("a", "shop", 90, None),
    ("b", "clinic", 75, "P007"),
    ("c", "bus", 65, None),
    ("a", "bus", 420, None),
    ("a", "c", 315, None),
]

ORIGINS = ["h1", "h2", "h3"]
DESTINATIONS = ["shop", "clinic", "bus"]
PROJECT_LINKS = {
    "P001": "修复1号楼入口的通行连续性",
    "P007": "改善社区卫生站入口的无台阶通达",
    "P009": "改善南门步道连续性",
}


def make_graph(completed_projects=()):
    """Known inaccessible edges are removed, not merely penalized."""
    done = set(completed_projects)
    graph = nx.Graph()
    for node, (name, latitude, longitude) in NODES.items():
        graph.add_node(node, name=name, lat=latitude, lon=longitude)
    for a, b, length, project_id in EDGES:
        if project_id is None or project_id in done:
            graph.add_edge(a, b, length=length, project_id=project_id)
    return graph


@lru_cache(maxsize=64)
def _compute(done_ids):
    graph = make_graph(done_ids)
    records = []
    for home in ORIGINS:
        for dest in DESTINATIONS:
            try:
                route = nx.shortest_path(graph, home, dest, weight="length")
                meters = nx.shortest_path_length(graph, home, dest, weight="length")
                reachable = True
            except nx.NetworkXNoPath:
                route = []
                meters = None
                reachable = False
            records.append({
                "origin": home,
                "destination": dest,
                "origin_name": NODES[home][0],
                "destination_name": NODES[dest][0],
                "reachable": reachable,
                "meters": meters,
                "route": route,
            })
    count = sum(r["reachable"] for r in records)
    all_lengths = [r["meters"] for r in records if r["meters"] is not None]
    return {
        "reachable_pairs": count,
        "total_pairs": len(records),
        "coverage_pct": 100.0 * count / len(records),
        "average_meters_of_reachable_routes":
            round(sum(all_lengths) / len(all_lengths), 1) if all_lengths else None,
        "routes": records,
    }


def accessibility_metrics(selected_project_ids=()):
    """Return new copies to avoid callers modifying cache contents."""
    linked_ids = frozenset(PROJECT_LINKS)
    done = tuple(sorted(set(selected_project_ids) & linked_ids))
    summary = _compute(done)
    return {
        **{key: value for key, value in summary.items() if key != "routes"},
        "routes": [dict(item, route=list(item["route"])) for item in summary["routes"]],
    }


def find_route(origin, destination, selected_project_ids=()):
    """Return [node ids] and length or an empty route when impassable."""
    graph = make_graph(selected_project_ids)
    try:
        return (
            nx.shortest_path(graph, origin, destination, weight="length"),
            nx.shortest_path_length(graph, origin, destination, weight="length"),
        )
    except nx.NetworkXNoPath:
        return [], None
