
import html
import folium
import streamlit as st

from streamlit_folium import st_folium
from core.data import ROOT, load_data
from core.risk import evaluate

# 页面样式
st.markdown("""
<style>
.stApp {
    background-color: #f5f7f6;
}
.block-container {
    max-width: 1550px;
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
    padding: 18px;
}
</style>
""", unsafe_allow_html=True)

st.title("社区适老化数字体检")
st.caption("空间风险识别 · 点位诊断 · 数据核验 · 改造建议")

# 读取现有数据
try:
    df = evaluate(load_data())
except Exception as exc:
    st.error(f"数据读取失败：{exc}")
    st.stop()

if df.empty:
    st.warning("当前没有问题数据，请先进入问题采集页面。")
    st.stop()

# 一、风险统计
c1, c2, c3, c4 = st.columns(4)

c1.metric("已登记问题", len(df))
c2.metric("高风险问题", int((df["risk_level"] == "高").sum()))
c3.metric("平均风险分", f"{df['risk_score'].mean():.1f}")
c4.metric("已人工核验", int(df["verified"].sum()))

st.divider()

# 二、交互筛选
st.subheader("社区空间风险分布")

f1, f2, f3 = st.columns(3)

with f1:
    selected_levels = st.multiselect(
        "筛选风险等级",
        ["高", "中", "低"],
        default=["高", "中", "低"]
    )

with f2:
    selected_source = st.selectbox(
        "数据来源",
        ["全部", "模拟", "实地调查"]
    )

with f3:
    only_verified = st.checkbox(
        "仅显示已人工核验的问题",
        value=False
    )

shown = df[df["risk_level"].isin(selected_levels)].copy()

if selected_source != "全部":
    shown = shown[shown["source_type"] == selected_source]

if only_verified:
    shown = shown[shown["verified"]]

st.caption(f"当前筛选显示 {len(shown)} / {len(df)} 个问题点位")

if shown.empty:
    st.warning("当前筛选条件下没有符合要求的问题。")
    st.stop()

# 三、地图与点位详情
map_col, detail_col = st.columns([1.8, 1], gap="large")

with map_col:
    st.markdown("#### 风险空间分布地图")

    center = [
        float(shown["lat"].mean()),
        float(shown["lon"].mean())
    ]

    m = folium.Map(
        location=center,
        zoom_start=16,
        control_scale=True
    )

    colors = {
        "高": "red",
        "中": "orange",
        "低": "green"
    }

    for _, row in shown.iterrows():
        status = "已核验" if row["verified"] else "未核验"

        popup_text = (
            f"<b>{html.escape(str(row['name']))}</b><br>"
            f"问题：{html.escape(str(row['issue_type']))}<br>"
            f"风险分：{row['risk_score']:.1f}<br>"
            f"数据来源：{html.escape(str(row['source_type']))}<br>"
            f"状态：{status}<br>"
            f"建议：{html.escape(str(row['suggestion']))}"
        )

        folium.CircleMarker(
            location=[
                float(row["lat"]),
                float(row["lon"])
            ],
            radius=10,
            color=colors[row["risk_level"]],
            fill=True,
            fill_color=colors[row["risk_level"]],
            fill_opacity=0.85,
            tooltip=str(row["name"]),
            popup=folium.Popup(
                popup_text,
                max_width=300
            )
        ).add_to(m)

    st_folium(
        m,
        height=520,
        use_container_width=True,
        returned_objects=[]
    )

    st.caption("🔴 高风险　🟠 中风险　🟢 低风险")
    st.caption("初始点位使用模拟坐标，不代表真实社区位置。")

with detail_col:
    st.markdown("#### 问题诊断与证据")

    label_map = {
        str(row["id"]): f"{row['name']} · {row['issue_type']}"
        for _, row in shown.iterrows()
    }

    selected_id = st.selectbox(
        "选择查看的问题点位",
        list(label_map.keys()),
        format_func=lambda x: label_map[x]
    )

    chosen = shown[
        shown["id"].astype(str) == selected_id
    ].iloc[0]

    st.metric(
        "模型风险分",
        f"{float(chosen['risk_score']):.1f} / 100"
    )

    st.write(f"**问题类别：** {chosen['issue_type']}")
    st.write(f"**风险等级：** {chosen['risk_level']}")
    st.write(f"**数据来源：** {chosen['source_type']}")

    status = "已人工核验" if chosen["verified"] else "尚未核验"
    st.write(f"**核验状态：** {status}")

    st.markdown("**建议改造措施**")
    st.info(str(chosen["suggestion"]))

    photo_path = str(chosen["photo_path"]).strip()

    if photo_path:
        image_file = ROOT / photo_path

        if image_file.is_file():
            st.image(
                str(image_file),
                caption="点位照片证据",
                use_container_width=True
            )
        else:
            st.caption("当前照片文件尚未找到。")
    else:
        st.caption("当前点位尚未上传照片证据。")

# 四、筛选后的问题清单
st.divider()
st.subheader("风险问题与改造建议清单")

st.dataframe(
    shown[
        [
            "id",
            "name",
            "issue_type",
            "risk_score",
            "risk_level",
            "suggestion",
            "source_type",
            "verified"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.warning(
    "当前风险分为未经实证校准的模型指标。"
    "涉及实际道路安全和无障碍规范的判断，"
    "应由专业人员结合现场测量进行核验。"
)