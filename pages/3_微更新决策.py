import pandas as pd
import streamlit as st
from core.data import load_data
from core.risk import evaluate
from core.optimizer import optimize, greedy
from core.experiment import comparison

st.title("③ 微更新预算组合决策")
st.caption("目标：在预算上限内最大化‘估计收益代理分’，不代表真实工程收益已验证。")

demo_mode = st.checkbox("演示模式：允许使用模拟数据", value=True)
budget = st.slider("可用改造预算（万元）", 0.0, 20.0, 5.0, 0.5)
severity_weight = st.slider("估计收益分中的严重度权重", 0.25, 0.45, 0.35, 0.05)

try:
    data = load_data()
    if demo_mode:
        st.info("正在使用包含模拟记录的数据，仅供算法演示和仿真对比。")
    else:
        data = data[(data["source_type"] == "实地调查") & (data["verified"])]
        st.info("仅使用来源为‘实地调查’且已人工核验的记录。")
    df = evaluate(data, severity_weight=severity_weight)
except Exception as exc:
    st.error(f"数据处理失败：{exc}")
    st.stop()

if df.empty:
    st.warning("当前筛选条件下没有候选项目，请先完成记录或开启演示模式。")
    st.stop()

try:
    result = optimize(df, budget)
    comp = comparison(df, budget)
except Exception as exc:
    st.error(f"预算优化失败：{exc}")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("预算上限", f"{budget:.1f}万元")
m2.metric("推荐支出", f"{result['cost_wan']:.2f}万元")
m3.metric("组合估计收益分", f"{result['benefit_score']:.1f}")

st.subheader("C 组合优化推荐项目")
if result["selected"]:
    selected = pd.DataFrame(result["selected"])
    st.dataframe(
        selected[["id", "name", "issue_type", "cost_wan",
                  "risk_level", "benefit_score", "suggestion"]],
        use_container_width=True, hide_index=True
    )
    st.download_button(
        "下载推荐方案CSV", selected.to_csv(index=False).encode("utf-8-sig"),
        file_name="银龄智城_优化方案.csv", mime="text/csv"
    )
else:
    st.info("当前预算不足以选择任一项目，请提高预算。")

st.subheader("三种预算决策方案对比（同预算、同数据）")
st.dataframe(comp, use_container_width=True, hide_index=True)
st.bar_chart(comp.set_index("方案")["估计收益分"])
st.caption(
    "注意：C方法正是以‘估计收益分’为优化目标，"
    "因此该指标的较高值只能验证求解逻辑，不足以证明实际治理绩效。"
)

st.subheader("权重敏感性检查")
rows = []
for sw in [0.25, 0.35, 0.45]:
    adjusted = evaluate(data, severity_weight=sw)
    answer = optimize(adjusted, budget)
    rows.append({
        "严重度权重": sw,
        "推荐编号": ", ".join(str(p["id"]) for p in answer["selected"]),
        "项目数": answer["count"],
        "预算使用(万元)": answer["cost_wan"],
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.warning("此页面未模拟真实施工效果、重复受益人口及项目间依赖；模拟结果不得表述为真实改造绩效。")

# ======================================
# 新增：预算优化决策解释模块
# ======================================

st.divider()
st.subheader("🔍 智能改造决策解释")
st.caption(
    "解释当前优化方案的项目选择依据，并与传统严重度优先方法比较。"
)

# 获取两种方法的结果
severity_plan = greedy(df, budget, "severity")

optimized_ids = {
    str(p["id"]) for p in result["selected"]
}

severity_ids = {
    str(p["id"]) for p in severity_plan["selected"]
}

# 方案比较
a, b, c = st.columns(3)

a.metric(
    "组合优化收益分",
    f"{result['benefit_score']:.1f}"
)

b.metric(
    "严重度优先收益分",
    f"{severity_plan['benefit_score']:.1f}"
)

c.metric(
    "收益分差值",
    f"{result['benefit_score'] - severity_plan['benefit_score']:.1f}"
)

st.caption(
    "以上均为模型代理分。优化方法以该分数最大化为目标，"
    "因此不能仅凭分数差值证明真实改造效果更好。"
)

# 显示两种方案的选择差异
name_lookup = {
    str(row["id"]): str(row["name"])
    for _, row in df.iterrows()
}

new_ids = sorted(optimized_ids - severity_ids)
old_ids = sorted(severity_ids - optimized_ids)

with st.expander("查看两种方案选择了哪些不同项目", expanded=True):

    if new_ids:
        st.success(
            "组合优化额外选择：" +
            "、".join(name_lookup.get(i, i) for i in new_ids)
        )
    else:
        st.write("组合优化没有额外选择的项目。")

    if old_ids:
        st.warning(
            "严重度优先独有项目：" +
            "、".join(name_lookup.get(i, i) for i in old_ids)
        )
    else:
        st.write("严重度优先没有独有项目。")

# 逐项展示推荐依据
st.markdown("#### 推荐项目详细解释")

if result["selected"]:

    project_options = {
        str(p["id"]): p for p in result["selected"]
    }

    selected_id = st.selectbox(
        "选择一个推荐项目",
        list(project_options.keys()),
        format_func=lambda x: (
            f"{project_options[x]['name']}（{x}）"
        )
    )

    project = project_options[selected_id]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "模型风险分",
        f"{float(project['risk_score']):.1f}"
    )

    col2.metric(
        "估计收益分",
        f"{float(project['benefit_score']):.1f}"
    )

    col3.metric(
        "估计成本",
        f"{float(project['cost_wan']):.2f}万元"
    )

    st.write(
        f"**问题类别：** {project['issue_type']}"
    )

    st.write(
        f"**问题严重度：** {project['severity']} / 5"
    )

    st.write(
        f"**估计受影响人数：** {project['people']} 人"
    )

    st.write(
        f"**路径使用频率等级：** {project['frequency']} / 5"
    )

    st.info(
        f"**建议措施：** {project['suggestion']}"
    )

    st.success(
        "推荐逻辑：系统在当前预算约束内搜索项目组合，"
        "使组合估计收益分最大化。该项目属于最优组合之一，"
        "并不意味着它单独的收益成本比一定最高。"
    )

else:
    st.info("当前预算内没有选中项目，无法生成单项解释。")

# 不被选中的项目
st.markdown("#### 本轮暂未选择的候选项目")

not_selected = df[
    ~df["id"].astype(str).isin(optimized_ids)
]

if not not_selected.empty:

    st.dataframe(
        not_selected[
            ["name", "issue_type", "cost_wan", "benefit_score"]
        ].rename(columns={
            "name": "问题位置",
            "issue_type": "问题类别",
            "cost_wan": "成本（万元）",
            "benefit_score": "估计收益分"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "未选中不代表项目不重要，只表示它没有进入"
        "当前预算和目标函数下的最优组合。"
    )
else:
    st.success("当前全部候选项目均已纳入推荐组合。")