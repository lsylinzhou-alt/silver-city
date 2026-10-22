
import streamlit as st
from core.data import load_data
from core.risk import evaluate

# 1. 网页基本配置
st.set_page_config(
    page_title="银龄智城 | 智能决策驾驶舱",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 统一网页配色和卡片样式
st.markdown("""
<style>
.stApp {
    background-color: #f5f7f6;
}
.block-container {
    max-width: 1500px;
    padding-top: 2rem;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #173f46, #10323a);
}
section[data-testid="stSidebar"] * {
    color: #e8f2ef;
}
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e1eae6;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 5px 20px rgba(20,60,60,0.04);
}
.hero {
    background: white;
    border: 1px solid #e2eae7;
    padding: 28px;
    border-radius: 16px;
    margin-bottom: 20px;
}
.hero-label {
    color: #23957a;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
}
.hero h1 {
    color: #183d45;
    font-size: 30px;
    margin: 10px 0;
}
.hero p {
    color: #70868a;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# 3. 首页标题
st.markdown("""
<div class="hero">
    <div class="hero-label">SILVER CITY · 智慧社区更新</div>
    <h1>让每一笔更新预算，真正打通一条生活之路。</h1>
    <p>社区适老化数字体检 · 空间风险诊断 · 微更新智能决策</p>
</div>
""", unsafe_allow_html=True)

st.info(
    "当前为竞赛原型。初始社区点位、人口、成本和评分"
    "包含模拟数据，尚不代表真实工程评估结果。"
)

# 4. 读取现有数据并计算指标
try:
    df = evaluate(load_data())
except Exception as exc:
    st.error(f"数据加载失败：{exc}")
    st.stop()

total = len(df)
high = int((df["risk_level"] == "高").sum())
verified = int(df["verified"].sum())
total_cost = float(df["cost_wan"].sum())

# 5. 四张统计卡片
c1, c2, c3, c4 = st.columns(4)

c1.metric("已登记空间问题", f"{total} 处")
c2.metric("模型高风险问题", f"{high} 处")
c3.metric("已人工核验", f"{verified} 处")
c4.metric("候选项目估计总成本", f"{total_cost:.1f} 万元")

st.write("")

# 6. 页面主体
left, right = st.columns([1.7, 1], gap="large")

with left:
    st.subheader("📍 社区空间风险优先清单")

    if df.empty:
        st.warning("暂无问题数据，请先录入。")
    else:
        display_df = df[
            ["name", "issue_type", "risk_score", "suggestion"]
        ].head(8).rename(columns={
            "name": "问题位置",
            "issue_type": "问题类别",
            "risk_score": "模型风险分",
            "suggestion": "建议措施"
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

with right:
    st.subheader("🧭 智能决策工作台")

    st.page_link(
        "pages/1_问题采集.py",
        label="① 社区问题采集",
        icon="📝"
    )

    st.page_link(
        "pages/2_数字体检.py",
        label="② 社区数字体检与风险地图",
        icon="🗺️"
    )

    st.page_link(
        "pages/3_微更新决策.py",
        label="③ 微更新预算优化",
        icon="📊"
    )

    st.caption(
        "下一阶段接入：多群体出行链、"
        "空间协同优化和改造前后推演。"
    )

st.divider()
st.caption("银龄智城 · 2026研究生智慧城市竞赛原型")