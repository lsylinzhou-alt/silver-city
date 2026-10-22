"""Spatial decision simulation: synthetic routes and project selection."""
import html
import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
from core.data import load_data
from core.risk import evaluate
from core.optimizer import optimize
from core.route_optimizer import choose_spatially
from core.mobility import (
    NODES, EDGES, ORIGINS, DESTINATIONS, PROJECT_LINKS,
    accessibility_metrics, find_route,
)

st.title("④ 完整出行链 · 空间联动推演")
st.info(
    "这是研究生竞赛的**合成案例仿真**：道路、位置、通行限制和长度均为人为设定，"
    "用于演示'项目组合会怎样影响完整出行链'；不是实际社区GIS、通行安全认证或真实改造效果。"
)

try:
    rated = evaluate(load_data())
except Exception as exc:
    st.error(f"数据不可用：{exc}")
    st.stop()

budget = st.slider("年度试验预算（万元）", 0.0, 20.0, 10.0, 0.5)
spatial_weight = st.slider(
    "空间可达性改善的额外重视程度（仿真参数）", 0, 600, 280, 40,
    help="0等同于只考虑加总收益分；值越大，越偏向能打通关键步行链路的项目。"
)

# New session records are not automatically part of the hand-built demo graph;
# only P001, P007, P009 have synthetic edges mapped to them.
if len(rated) > 16:
    st.warning("空间搜索最多支持16条记录，请只保留前16条再演示。")
    rated = rated.head(16)

basic = optimize(rated, budget)
spatial = choose_spatially(rated, budget, spatial_bonus=spatial_weight)

basic_ids = {row["id"] for row in basic["selected"]}
spatial_ids = {row["id"] for row in spatial["selected"]}

before = accessibility_metrics()
after_basic = accessibility_metrics(basic_ids)
after_spatial = accessibility_metrics(spatial_ids)

st.subheader("先看关键区别：得分变高，是否等于路真正通了？")
comparison = pd.DataFrame([
    {
        "方案": "改造前",
        "改造成本(万元)": 0.0,
        "估计收益分": 0.0,
        "可通行出行链": f"{before['reachable_pairs']}/{before['total_pairs']}",
        "模拟可达比例": round(before["coverage_pct"], 1),
    },
    {
        "方案": "传统：只优化代理收益分",
        "改造成本(万元)": basic["cost_wan"],
        "估计收益分": basic["benefit_score"],
        "可通行出行链": f"{after_basic['reachable_pairs']}/{after_basic['total_pairs']}",
        "模拟可达比例": round(after_basic["coverage_pct"], 1),
    },
    {
        "方案": "增强：代理收益分＋出行链",
        "改造成本(万元)": spatial["cost_wan"],
        "估计收益分": spatial["benefit_score"],
        "可通行出行链": f"{after_spatial['reachable_pairs']}/{after_spatial['total_pairs']}",
        "模拟可达比例": round(after_spatial["coverage_pct"], 1),
    },
])
st.dataframe(comparison, use_container_width=True, hide_index=True)

c1, c2, c3 = st.columns(3)
c1.metric("改造前可通行链路", f"{before['reachable_pairs']}/9")
c2.metric("传统组合后", f"{after_basic['reachable_pairs']}/9")
c3.metric("空间协同组合后", f"{after_spatial['reachable_pairs']}/9")

st.caption(
    "分母9 = 3个假设楼栋 × 3个假设生活目的地。"
    "可达性为模型计算值，不是实际居民受益比例。"
)

st.subheader("比较两套推荐项目")
left, right = st.columns(2)
with left:
    st.markdown("**传统预算组合**")
    st.write("、".join(f"{r['id']} {r['name']}" for r in basic["selected"]) or "无项目")
with right:
    st.markdown("**空间联动预算组合**")
    st.write("、".join(f"{r['id']} {r['name']}" for r in spatial["selected"]) or "无项目")

st.subheader("路径可视化（虚拟社区地图）")
state = st.radio(
    "选择要查看的状态", ["改造前", "传统组合后", "空间协同组合后"],
    horizontal=True,
)
selected_ids = {
    "改造前": set(),
    "传统组合后": basic_ids,
    "空间协同组合后": spatial_ids,
}[state]

origin = st.selectbox("从哪栋楼出发？", ORIGINS, format_func=lambda k: NODES[k][0])
destination = st.selectbox(
    "想去哪儿？", DESTINATIONS, format_func=lambda k: NODES[k][0]
)
route, distance = find_route(origin, destination, selected_ids)
if route:
    st.success(
        f"模拟路线可通行：{NODES[origin][0]} → {NODES[destination][0]}，"
        f"路径长度约 {distance} 米（人为设定的边长）。"
    )
else:
    st.warning("当前模型下没有符合预设硬约束的通行路线；不强行给出危险替代路。")

m = folium.Map(location=[31.2310, 121.47175], zoom_start=16, control_scale=True)
for a, b, length, project_id in EDGES:
    accessible = not project_id or project_id in selected_ids
    folium.PolyLine(
        locations=[[NODES[a][1], NODES[a][2]], [NODES[b][1], NODES[b][2]]],
        color="#1c8c75" if accessible else "#c66c54",
        weight=4 if accessible else 3,
        opacity=0.85,
        dash_array=None if accessible else "6 6",
        tooltip=f"{'可通行' if accessible else '尚有障碍'}｜设定长度 {length}m"
                + (f"｜对应 {project_id}" if project_id else ""),
    ).add_to(m)
if len(route) > 1:
    folium.PolyLine(
        locations=[[NODES[n][1], NODES[n][2]] for n in route],
        color="#263d67", weight=8, opacity=0.9, tooltip="当前推荐路线"
    ).add_to(m)
for node, (name, lat, lon) in NODES.items():
    if node in ORIGINS:
        color = "blue"
    elif node in DESTINATIONS:
        color = "purple"
    else:
        color = "gray"
    folium.CircleMarker(
        location=[lat, lon], radius=7 if node in ORIGINS + DESTINATIONS else 4,
        color=color, fill=True, fill_opacity=0.9,
        tooltip=name, popup=folium.Popup(html.escape(name), max_width=200)
    ).add_to(m)
st_folium(m, height=455, use_container_width=True, returned_objects=[])
st.caption("路线底图是演示图层：蓝色为住宅、紫色为目的地；绿色为可通行、红色虚线为尚未修复的模拟障碍，深蓝为推荐路径。")

st.subheader("项目—通行障碍的关联规则")
st.dataframe(
    pd.DataFrame([{"项目编号": key, "示例作用": value} for key, value in PROJECT_LINKS.items()]),
    use_container_width=True, hide_index=True,
)
st.warning(
    "真正的竞赛研究应替换为现场人行道拓扑、坡道高差、过街点和设施编号；"
    "本案例只证明设计逻辑能运行，不能证明真实社区可达性提升。"
)


# ==========================================
# 新增：完整生活出行链改善解释
# ==========================================

st.divider()
st.subheader("🔎 改造前后完整出行链改善分析")

st.caption(
    "比较当前选择的改造方案与改造前状态，"
    "识别新获得可通行条件的生活路线。"
)

# 1. 计算改造前与当前方案的可通行情况
baseline = accessibility_metrics()
current = accessibility_metrics(selected_ids)

st.metric(
    "本方案新增可通行出行链",
    current["reachable_pairs"] - baseline["reachable_pairs"],
    help="只统计模型中从不可通行变为可通行的住宅—目的地组合"
)

# 2. 找出改造前不可通行、改造后可通行的路线
baseline_lookup = {
    (r["origin"], r["destination"]): r["reachable"]
    for r in baseline["routes"]
}

improved_routes = []

for route in current["routes"]:

    key = (route["origin"], route["destination"])

    if route["reachable"] and not baseline_lookup[key]:

        improved_routes.append({
            "住宅起点": route["origin_name"],
            "生活目的地": route["destination_name"],
            "改造前": "不可通行",
            "改造后": "模型可通行",
            "模拟路线长度(米)": route["meters"]
        })

st.markdown("#### 本轮新增可通行的生活路线")

if improved_routes:
    st.dataframe(
        pd.DataFrame(improved_routes),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("当前方案没有新增可通行的完整生活路线。")

# 3. 反事实分析：撤销某项改造，会失去哪些路线？
st.markdown("#### 关键改造项目贡献分析")

st.caption(
    "在其他已选择项目保持不变的情况下，"
    "逐一撤销一个项目，观察完整出行链的变化。"
)

linked_projects = sorted(
    set(selected_ids) & set(PROJECT_LINKS.keys())
)

contributions = []

for project_id in linked_projects:

    remaining_ids = set(selected_ids) - {project_id}

    without_project = accessibility_metrics(
        remaining_ids
    )

    # 撤销此项目后，重新变为不可通行的路线
    without_lookup = {
        (r["origin"], r["destination"]): r["reachable"]
        for r in without_project["routes"]
    }

    lost_routes = []

    for route in current["routes"]:
        key = (route["origin"], route["destination"])

        if route["reachable"] and not without_lookup[key]:
            lost_routes.append(
                f"{route['origin_name']}→"
                f"{route['destination_name']}"
            )

    contributions.append({
        "改造项目": project_id,
        "模型作用": PROJECT_LINKS[project_id],
        "撤销后损失的出行链数": len(lost_routes),
        "受影响路线": "；".join(lost_routes) if lost_routes else "无"
    })

if contributions:
    st.dataframe(
        pd.DataFrame(contributions),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info(
        "当前选择的项目中，没有与示例路网障碍"
        "直接关联的改造项目。"
    )

# 4. 研究边界说明
st.caption(
    "注意：撤销后损失的链路数量属于给定组合下的反事实分析。"
    "0条不代表项目没有价值，也不能把各项目贡献简单相加。"
    "当前示例路网只将P001、P007、P009关联到道路硬阻断，"
    "其他改造可能影响舒适性，却不直接改变本模型的通行数量。"
)

st.warning(
    "以上结果基于模拟路网与预设通行条件，"
    "尚不能证明真实社区施工后的可达性改善。"
)
