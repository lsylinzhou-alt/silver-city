import pandas as pd
import streamlit as st
from core.data import load_data
from core.risk import evaluate
from core.optimizer import optimize
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
