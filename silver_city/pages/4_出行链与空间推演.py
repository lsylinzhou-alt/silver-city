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
