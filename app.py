import streamlit as st
from core.data import load_data

st.set_page_config(page_title="银龄智城", page_icon="🏙️", layout="wide")
st.title("银龄智城 | 适老化数字体检与微更新决策")
st.write("请选择左侧页面：① 问题采集 → ② 数字体检 → ③ 微更新决策。")

try:
    data = load_data()
    left, right = st.columns(2)
    left.metric("当前问题记录", len(data))
    right.metric("其中模拟案例", int((data["source_type"] == "模拟").sum()))
except Exception as exc:
    st.error(f"数据读取失败：{exc}")

st.info(
    "这是竞赛教学原型。初始记录全部为模拟案例；"
    "评价权重和工程成本仅用于功能演示，非实际社区诊断或施工决策。"
)
st.markdown("**演示建议：** 先在‘问题采集’增加一条，再去‘数字体检’看地图，最后调整‘微更新决策’的预算。")
