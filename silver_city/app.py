"""Silver City: municipal age-friendly renewal decision-support demonstration."""
import streamlit as st
from core.data import load_data
from core.risk import evaluate
from core.survey_network import sample_network, evaluate_access

st.set_page_config(page_title="银龄智城", page_icon="🏙️", layout="wide")
st.title("银龄智城 | 社区适老化数字体检与微更新决策")
st.caption("空间风险识别 · 完整生活出行链 · 有限预算下的公平与效益协同优化")

st.markdown(
    "**不是普通养老APP，也不只是风险点统计。** "
    "本系统尝试回答三个城市治理问题：哪里需要改、哪些关键生活路径真正受影响、"
    "在相同预算下怎样选择更合理的微更新项目。"
)

try:
    data = evaluate(load_data())
    nodes, edges = sample_network()
    accessibility = evaluate_access(nodes, edges, "轮椅")
    c1, c2, c3 = st.columns(3)
    c1.metric("项目问题记录", len(data))
    c2.metric("模型高风险点", int((data["risk_level"] == "高").sum()))
    c3.metric("虚拟场景改造前可达链", f"{accessibility['reachable_pairs']}/{accessibility['total_pairs']}")
except Exception as exc:
    st.error(f"演示数据载入失败：{exc}")

st.subheader("研究路线：从单点评分到生活链路优化")
left, middle, right = st.columns(3)
with left:
    st.markdown("**01 采集与诊断**")
    st.write("记录入口台阶、坡道、座椅、照明等问题，并保留数据来源与人工核验状态。")
with middle:
    st.markdown("**02 路网与差异化通行**")
    st.write("按一般步行、助行器、轮椅的预设限制，评估住宅至卫生站、菜市场、公交站的完整路径。")
with right:
    st.markdown("**03 预算与方案解释**")
    st.write("在同等预算下对比传统收益优化与路网协同优化，并解释关键项目对哪些路径有贡献。")

st.subheader("左侧5个功能页面")
st.write("① 问题采集 → ② 数字体检 → ③ 微更新决策 → ④ 出行链与空间推演 → ⑤ 片区路网与人群差异。")
st.success("建议评委演示顺序：先看③预算差异，再看④出行链，最后在⑤选择轮椅档案并展示项目边际贡献。")
st.warning(
    "**数据边界：** 初始问题、空间网络、居民人数代理值、改造成本和权重均为演示设定；"
    "没有由系统自动判断照片中的工程风险，任何推演均不能代替实地调查和安全评估。"
)
