"""Experimental walkability tool: synthetic demo or optional uploaded surveys."""
import html
from io import StringIO

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from core.data import load_data
from core.optimizer import optimize
from core.risk import evaluate
from core.survey_network import (
    PROFILES, DESTINATION_KINDS, sample_network, validate_network,
    evaluate_access, choose_access_budget, choose_joint_budget,
    explain_marginal_effect, make_survey_graph, minimum_service_guarantee
)

st.title("⑤ 片区路网与人群差异评价")
st.caption("竞赛增强实验：不同通行限制下的完整生活路径，与有限预算的组合选择联动。")
st.warning(
    "本页默认使用**人工构造的虚拟路网**。上传调查CSV只代表你们提供了数据，"
    "不自动证明道路满足无障碍规范；现场测量和专业复核仍然必须进行。"
)

st.subheader("步骤1｜选取路网数据")
st.write("首次测试请选择默认演示；若有实际调查，可上传两张CSV表。上传内容只用于当前页面会话，不会自动写入仓库。")
left, right = st.columns(2)
with left:
    nodes_upload = st.file_uploader("① 节点表 nodes.csv", type=["csv"], key="survey_nodes")
with right:
    edges_upload = st.file_uploader("② 道路表 edges.csv", type=["csv"], key="survey_edges")

if (nodes_upload is None) != (edges_upload is None):
    st.error("请同时上传节点表和道路表，或者两者都不上传以使用示例数据。")
    st.stop()
is_uploaded = nodes_upload is not None
try:
    if is_uploaded:
        nodes = pd.read_csv(nodes_upload, encoding="utf-8-sig", keep_default_na=False)
        edges = pd.read_csv(edges_upload, encoding="utf-8-sig", keep_default_na=False)
    else:
        nodes, edges = sample_network()
    validate_network(nodes, edges)
except Exception as exc:
    st.error(f"路网数据检查失败：{exc}")
    st.stop()

if is_uploaded:
    st.success("已读取用户上传的数据；下面结果仍需要现场核验，并检查坐标系及道路连接是否正确。")
else:
    st.info("当前为教学示例：9个虚构节点、10段虚构道路，仅用于验证算法。")

with st.expander("查看CSV字段格式、下载可修改的演示模板"):
    st.write("节点必需列：`node_id,name,lat,lon,kind`；kind包括住宅、路口、卫生站、公交站、菜市场、公共服务等。")
    st.write("道路必需列：`start,end,length_m,blocked_for,repair_project_id,verified`。")
    st.write("blocked_for用分号分隔，如`轮椅;助行器`；无已知阻断则留空；repair_project_id必须与问题项目表的id一致。")
    st.write("verified表明人工核验状态；未核验的路段不能用作真实安全通行证明。")
    st.download_button("下载节点表示例", nodes.to_csv(index=False).encode("utf-8-sig"),
                       "nodes_template.csv", "text/csv")
    st.download_button("下载道路表示例", edges.to_csv(index=False).encode("utf-8-sig"),
                       "edges_template.csv", "text/csv")
    st.dataframe(nodes, hide_index=True)
    st.dataframe(edges, hide_index=True)

st.subheader("步骤2｜关联候选改造项目")
projects_upload = st.file_uploader(
    "③ 改造项目表 problems.csv（实际调查时建议上传；须含id、cost_wan及4个评价指标）",
    type=["csv"], key="survey_projects"
)
try:
    if projects_upload is not None:
        project_data = pd.read_csv(projects_upload, encoding="utf-8-sig", keep_default_na=False)
    else:
        project_data = load_data()
    if is_uploaded and projects_upload is not None:
        if not {"source_type", "verified"}.issubset(project_data.columns):
            raise ValueError("实际项目表必须含 source_type 和 verified 字段")
        project_data = project_data[
            (project_data["source_type"] == "实地调查") &
            (project_data["verified"].astype(str).str.lower().isin(["true", "1", "yes"]))
        ]
    rated = evaluate(project_data)
except Exception as exc:
    st.error(f"项目表读取失败：{exc}")
    st.stop()

if is_uploaded and projects_upload is None:
    st.warning("当前使用了上传路网+仓库中演示项目的混合数据，结果只能用于技术排查。正式实验必须上传实地调查项目表。")
if rated.empty:
    st.error("当前没有可计算的候选项目。请上传含已核验记录的项目表或先使用示例。")
    st.stop()

match_ids = set(str(v).strip() for v in edges["repair_project_id"] if str(v).strip())
project_ids = set(rated["id"].astype(str))
missing_repair_ids = sorted(match_ids - project_ids)
if missing_repair_ids:
    st.warning("道路修复编号在项目表中找不到：" + ", ".join(missing_repair_ids) + "。这些道路在当前方案中无法通过选项自动修复。")

rated = rated.sort_values("benefit_score", ascending=False)
choices = rated["id"].astype(str).tolist()
preselected = choices[:min(len(choices), 12)]
chosen_ids = st.multiselect("本次参与优化的项目（最多12个）", choices, default=preselected)
if len(chosen_ids) > 12:
    st.error("为保证演示运行速度，请最多选择12个项目")
    st.stop()
selected_projects = rated[rated["id"].astype(str).isin(chosen_ids)].copy()

st.subheader("步骤3｜设置不同用户和预算")
profile = st.selectbox("通行能力档案（由用户选择，不按年龄自动判断）", PROFILES, index=2)
verified_only = st.checkbox(
    "仅把人工核验的道路当作已知可通行路段",
    value=is_uploaded,
    help="建议实际调查模式始终勾选；未核验路段将从可用图中排除。"
)
col_a, col_b, col_c = st.columns(3)
with col_a:
    budget = st.slider("预算上限（万元）", 0.0, 20.0, 5.0, 0.5)
with col_b:
    route_weight = st.slider("出行链改善权重", 0.0, 600.0, 260.0, 20.0)
with col_c:
    fairness_weight = st.slider("弱覆盖楼栋优先权重", 0.0, 300.0, 80.0, 20.0)

try:
    before = evaluate_access(nodes, edges, profile, (), verified_only)
    baseline = optimize(selected_projects, budget)
    improved = choose_access_budget(
        selected_projects, nodes, edges, budget, profile,
        route_weight, fairness_weight, verified_only
    )
    baseline_ids = [str(row["id"]) for row in baseline["selected"]]
    improved_ids = improved["selected_ids"]
    after_base = evaluate_access(nodes, edges, profile, baseline_ids, verified_only)
    after_new = evaluate_access(nodes, edges, profile, improved_ids, verified_only)
except Exception as exc:
    st.error(f"优化或可达性分析失败：{exc}")
    st.stop()

st.subheader("步骤4｜比较同预算下的不同决策")
comparisons = pd.DataFrame([
    {"方案": "改造前", "支出(万元)": 0.0, "估计收益分": 0.0,
     "完整可达链": before["reachable_pairs"], "总链数": before["total_pairs"],
     "最低楼栋可达率(%)": round(before["min_home_pct"], 1)},
    {"方案": "仅优化加总收益", "支出(万元)": baseline["cost_wan"],
     "估计收益分": baseline["benefit_score"],
     "完整可达链": after_base["reachable_pairs"], "总链数": after_base["total_pairs"],
     "最低楼栋可达率(%)": round(after_base["min_home_pct"], 1)},
    {"方案": "出行链+弱覆盖楼栋协同", "支出(万元)": improved["cost_wan"],
     "估计收益分": improved["benefit_score"],
     "完整可达链": after_new["reachable_pairs"], "总链数": after_new["total_pairs"],
     "最低楼栋可达率(%)": round(after_new["min_home_pct"], 1)},
])
st.dataframe(comparisons, hide_index=True, use_container_width=True)
st.bar_chart(comparisons.set_index("方案")["完整可达链"])
st.caption("同预算下的改善是指定路网、障碍标签、权重和人工项目成本的**模型结果**，不是实际施工后的验证值。")

st.subheader("步骤5｜查看推荐理由")
st.write("空间协同组合：", "、".join(improved_ids) if improved_ids else "当前预算未选择项目")
if improved_ids:
    effects = explain_marginal_effect(nodes, edges, profile, improved_ids, verified_only)
    st.dataframe(effects, hide_index=True, use_container_width=True)
    st.caption("边际贡献为‘整套方案中不实施某一项’的差额；多项改造可能共同打通一条链，因此不可简单累加。")
    selected_out = pd.DataFrame(improved["selected"])
    st.download_button("导出空间优化项目清单", selected_out.to_csv(index=False).encode("utf-8-sig"),
                       "silver_city_route_plan.csv", "text/csv")

st.subheader("步骤6｜不同通行能力下是否都受益？")
profile_rows = []
for p in PROFILES:
    x_before = evaluate_access(nodes, edges, p, (), verified_only)
    x_after = evaluate_access(nodes, edges, p, improved_ids, verified_only)
    profile_rows.append({"档案": p, "改造前可达链": x_before["reachable_pairs"],
                         "改造后可达链": x_after["reachable_pairs"],
                         "改造后最低楼栋可达率(%)": round(x_after["min_home_pct"], 1)})
st.dataframe(pd.DataFrame(profile_rows), hide_index=True, use_container_width=True)
st.caption("人群档案仅表示使用者选择的通行约束，不能用老年人、助行器或轮椅标签代替个体的实际通行能力测量。")

st.subheader("步骤7｜地图检查路径和证据状态")
active = st.radio("地图中的状态", ["改造前", "加总收益方案后", "空间协同方案后"], horizontal=True)
selected = {"改造前": set(), "加总收益方案后": set(baseline_ids),
            "空间协同方案后": set(improved_ids)}[active]
coordinates = {str(n["node_id"]): (float(n["lat"]), float(n["lon"])) for _, n in nodes.iterrows()}
center = [sum(lat for lat, lon in coordinates.values()) / len(coordinates),
          sum(lon for lat, lon in coordinates.values()) / len(coordinates)]
map_view = folium.Map(location=center, zoom_start=16, control_scale=True)
usable = make_survey_graph(nodes, edges, profile, selected, verified_only)
for _, e in edges.iterrows():
    a, b = str(e["start"]), str(e["end"])
    ready = usable.has_edge(a, b)
    verified = str(e["verified"]).lower() in {"true", "1", "yes", "是", "已核验"}
    folium.PolyLine([coordinates[a], coordinates[b]],
                    color="#198a72" if ready else "#c56954",
                    weight=4, dash_array=None if ready else "6 6",
                    tooltip=f"{a}-{b} | {'模型可通行' if ready else '受阻/未核验'} | "
                            f"关联改造: {e['repair_project_id'] or '无'} | "
                            f"{'已核验' if verified else '未核验'}"
                   ).add_to(map_view)
for _, n in nodes.iterrows():
    node_id = str(n["node_id"])
    kind = str(n["kind"])
    color = "blue" if kind == "住宅" else ("purple" if kind in DESTINATION_KINDS else "gray")
    folium.CircleMarker(coordinates[node_id], radius=7 if color != "gray" else 4,
                        fill=True, fill_opacity=0.9, color=color,
                        tooltip=f"{n['name']} | {kind}",
                        popup=folium.Popup(html.escape(str(n["name"])), max_width=250)).add_to(map_view)
st_folium(map_view, height=450, use_container_width=True, returned_objects=[])
st.info("绿色表示符合当前人工设定的路段通行规则；并不构成实际安全保证。红色表示受阻或因未核验被排除。")

if is_uploaded:
    st.warning("真实案例汇报必须同步给出：调查日期、照片/测量依据、数据来源、样本规模、工程成本出处、坐标系及专业复核范围。")


# ============================================
# 竞赛增强：同一改造方案下的多群体剩余障碍
# ============================================

st.divider()
st.subheader("步骤8｜多群体受益与剩余出行障碍")

st.caption(
    "以下比较的是针对当前选定档案优化出的同一组项目，"
    "并不是同时对所有档案进行联合优化。"
)

group_results = []
blocked_by_profile = {}

# 分别计算三种通行能力下的改造效果
for user_profile in PROFILES:

    before_group = evaluate_access(
        nodes, edges, user_profile, (), verified_only
    )

    after_group = evaluate_access(
        nodes, edges, user_profile, improved_ids, verified_only
    )

    # 收集改造后仍然不能通行的生活路线
    blocked = [
        f"{r['origin']} → {r['destination']}"
        for r in after_group["routes"]
        if not r["reachable"]
    ]

    blocked_by_profile[user_profile] = blocked

    group_results.append({
        "通行能力档案": user_profile,
        "改造前可通行": before_group["reachable_pairs"],
        "改造后可通行": after_group["reachable_pairs"],
        "新增链路": (
            after_group["reachable_pairs"]
            - before_group["reachable_pairs"]
        ),
        "剩余不可通行": len(blocked),
        "改造后可通行率(%)": round(
            after_group["coverage_pct"], 1
        )
    })

# 显示多群体对比表
group_df = pd.DataFrame(group_results)

st.dataframe(
    group_df,
    use_container_width=True,
    hide_index=True
)

# 显示改造前后的对比柱状图
st.bar_chart(
    group_df.set_index("通行能力档案")[
        ["改造前可通行", "改造后可通行"]
    ],
    stack=False
)

# 找出当前模型中可通行率最低的档案
weakest = min(
    group_results,
    key=lambda row: row["改造后可通行率(%)"]
)

st.info(
    f"当前模型中，可通行率最低的档案为："
    f"{weakest['通行能力档案']}"
    f"（{weakest['改造后可通行率(%)']:.1f}%）。"
)

# 查看具体没有打通的路线
inspect_profile = st.selectbox(
    "选择档案，查看改造后仍无法通行的路线",
    PROFILES,
    key="group_unreachable_details"
)

remaining = blocked_by_profile[inspect_profile]

if remaining:

    st.warning("仍有以下生活路线未被打通：")

    for label in remaining:
        st.write("• " + label)

else:
    st.success(
        "当前模拟网络中，该档案的"
        "住宅—目的地组合均可通行。"
    )

st.caption(
    "这些结论仅反映路网数据与预设通行规则。"
    "不同档案的新增链路数不能直接代表实际受益人数；"
    "某档案新增为0，也可能是因为改造前已全部可通行。"
)


# ============================================
# 步骤9：单群体与多群体联合优化对比
# ============================================

st.divider()
st.subheader("步骤9｜多群体联合优化决策对比")

st.caption(
    f"原空间方案针对【{profile}】档案优化；"
    "联合方案在同一预算下同时考虑三种档案。"
)

# 一、运行新增的联合优化算法
try:
    with st.spinner("正在计算三类档案的联合改造方案……"):
        joint_plan = choose_joint_budget(
            selected_projects,
            nodes,
            edges,
            budget_wan=budget,
            bonus=route_weight,
            fairness_bonus=fairness_weight,
            verified_only=verified_only,
        )

except Exception as exc:
    st.error(f"多群体联合优化失败：{exc}")
    st.stop()

# 二、比较同一批项目对三类档案的影响
single_group_metrics = {}
joint_group_metrics = []
compare_rows = []

for p in PROFILES:

    before_p = evaluate_access(
        nodes, edges, p, (), verified_only
    )

    single_p = evaluate_access(
        nodes, edges, p, improved_ids, verified_only
    )

    joint_p = evaluate_access(
        nodes, edges, p,
        joint_plan["selected_ids"], verified_only
    )

    single_group_metrics[p] = single_p
    joint_group_metrics.append(joint_p)

    compare_rows.append({
        "通行能力档案": p,
        "改造前可通行": before_p["reachable_pairs"],
        "单群体方案后": single_p["reachable_pairs"],
        "联合方案后": joint_p["reachable_pairs"],
        "联合相对单群体差异": (
            joint_p["reachable_pairs"]
            - single_p["reachable_pairs"]
        )
    })

compare_df = pd.DataFrame(compare_rows)

st.markdown("#### 三类人群的可通行链路对比")

st.dataframe(
    compare_df,
    hide_index=True,
    use_container_width=True
)

# 并排柱状图，避免堆叠造成误解
st.bar_chart(
    compare_df.set_index("通行能力档案")[
        ["单群体方案后", "联合方案后"]
    ],
    stack=False
)

# 三、比较预算与最弱群体
single_worst = min(
    x["coverage_pct"]
    for x in single_group_metrics.values()
)

joint_worst = min(
    x["coverage_pct"]
    for x in joint_group_metrics
)

st.markdown("#### 预算使用与公平性指标")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "单群体方案支出",
    f"{improved['cost_wan']:.2f} 万元"
)

c2.metric(
    "联合方案支出",
    f"{joint_plan['cost_wan']:.2f} 万元"
)

c3.metric(
    "单群体方案最弱群体覆盖率",
    f"{single_worst:.1f}%"
)

c4.metric(
    "联合方案最弱群体覆盖率",
    f"{joint_worst:.1f}%"
)

# 四、展示两个算法选择的项目
st.markdown("#### 推荐改造项目差异")

st.write(
    "**单群体方案项目：**",
    "、".join(improved_ids) or "无"
)

st.write(
    "**多群体联合项目：**",
    "、".join(joint_plan["selected_ids"]) or "无"
)

# 五、检查是否仍有住宅完全无法到达服务设施
worst_home = min(
    x["min_home_pct"]
    for x in joint_group_metrics
)

if worst_home < 1e-9:

    st.warning(
        "注意：联合方案下仍有至少一个档案的"
        "某栋住宅无法到达任何模型目的地。"
        "最弱群体覆盖率提高，不等于每栋楼都有改善。"
    )

else:

    st.info(
        f"联合方案中，各档案最弱楼栋"
        f"可达率至少为 {worst_home:.1f}%。"
    )

st.caption(
    "本次对比使用相同候选项目、预算和路网假设。"
    "联合优化属于模拟研究，不保证各类人群"
    "都比单群体优化获得更高覆盖率。"
)


# ============================================
# 步骤10：最低生活服务保障预算
# ============================================

st.divider()

st.subheader("步骤10｜基本生活服务最低保障决策")

st.caption(
    "目标：在三种通行能力档案下，"
    "让每栋住宅至少能够到达一个生活服务目的地。"
)

# 1. 调用最低保障预算算法
try:
    with st.spinner("正在计算最低保障预算……"):
        guarantee = minimum_service_guarantee(
            selected_projects,
            nodes,
            edges,
            budget_wan=budget,
            verified_only=verified_only
        )

except Exception as exc:
    st.error(f"最低保障预算计算失败：{exc}")
    st.stop()

# 2. 判断当前候选项目能否满足保障目标
if not guarantee["possible"]:

    st.error(
        "当前候选改造项目无法满足基本生活服务保障。"
    )

    st.warning(guarantee["reason"])

else:

    # 3. 显示预算指标
    c1, c2, c3 = st.columns(3)

    c1.metric(
        "当前预算",
        f"{budget:.2f} 万元"
    )

    c2.metric(
        "最低保障预算",
        f"{guarantee['minimum_cost_wan']:.2f} 万元"
    )

    c3.metric(
        "尚需增加预算",
        f"{guarantee['extra_budget_wan']:.2f} 万元"
    )

    # 4. 判断预算是否足够
    if guarantee["within_budget"]:

        st.success(
            "当前预算能够满足模型设定的最低生活服务保障要求。"
        )

    else:

        st.warning(
            "当前预算不足以满足全部住宅的最低保障要求。"
        )

    # 5. 显示最低保障项目组合
    if guarantee["within_budget"]:


        st.markdown("#### 当前预算内可执行的最低保障项目")

        st.success(
            "当前预算可以执行以下最低保障组合。"
        )
    else:

        st.markdown("#### 最低保障目标项目（当前不可执行）")

        st.warning(
            f"当前预算为 {budget:.2f} 万元，"
            f"最低保障需要 {guarantee['minimum_cost_wan']:.2f} 万元，"
            f"仍缺少 {guarantee['extra_budget_wan']:.2f} 万元。"
            "以下项目仅为达到保障目标所需的计算组合，"
            "不是当前预算内可直接实施的方案。"
        )

    st.write(
        "项目编号：",
        "、".join(guarantee["selected_ids"])
        or "无需新增改造项目"
    )
        

    # 6. 查看各楼栋的保障效果
    st.markdown("#### 三类群体及各楼栋的保障结果")

    coverage_rows = []

    for p in PROFILES:

        before = evaluate_access(
            nodes, edges, p, (), verified_only
        )

        after = evaluate_access(
            nodes, edges, p,
            guarantee["selected_ids"],
            verified_only
        )

        for home, after_pct in after["per_home_pct"].items():

            before_pct = before["per_home_pct"].get(
                home, 0
            )

            coverage_rows.append({
                "通行能力档案": p,
                "住宅楼栋": home,
                "改造前可达率(%)": round(before_pct, 1),
                "最低保障目标方案后可达率(%)": round(after_pct, 1),
                "目标方案是否达标": (
                    "是" if after_pct > 0 else "否"
                )
            })

    coverage_df = pd.DataFrame(coverage_rows)

    st.dataframe(
        coverage_df,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "本模块所称最低保障，是每栋住宅在每个"
        "通行能力档案下至少有一个目的地模型可达。"
        "不意味着全部目的地都可达，也不构成"
        "实际道路无障碍安全认证。"
    )