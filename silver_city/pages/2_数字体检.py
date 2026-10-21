import html
from pathlib import Path
import folium
import streamlit as st
from streamlit_folium import st_folium
from core.data import ROOT, load_data
from core.risk import evaluate

st.title("② 社区适老化数字体检")
st.caption("显示人工录入点位的模型评分；地图颜色不是安全认证等级。")

try:
    df = evaluate(load_data())
except Exception as exc:
    st.error(f"读取或评价失败：{exc}")
    st.stop()

if df.empty:
    st.warning("数据为空，请到‘问题采集’页面新增记录。")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("问题总数", len(df))
c2.metric("模型高风险点", int((df["risk_level"] == "高").sum()))
c3.metric("风险均分（演示）", round(df["risk_score"].mean(), 1))

st.subheader("问题位置与风险地图")
st.info("初始地图位置为模拟坐标，非真实社区调查。底图需要联网，若网络不可用请查看下方数据表。")
center = [float(df["lat"].mean()), float(df["lon"].mean())]
m = folium.Map(location=center, zoom_start=16, control_scale=True)
colors = {"高": "red", "中": "orange", "低": "green"}
for _, row in df.iterrows():
    popup_text = (
        f"<b>{html.escape(str(row['name']))}</b><br>"
        f"问题：{html.escape(str(row['issue_type']))}<br>"
        f"风险分：{row['risk_score']:.1f}<br>"
        f"措施：{html.escape(str(row['suggestion']))}"
    )
    folium.CircleMarker(
        location=[float(row["lat"]), float(row["lon"])],
        radius=8, color=colors[row["risk_level"]], fill=True,
        fill_color=colors[row["risk_level"]], fill_opacity=0.85,
        tooltip=str(row["name"]), popup=folium.Popup(popup_text, max_width=300),
    ).add_to(m)
st_folium(m, height=430, use_container_width=True, returned_objects=[])

st.subheader("模型风险与建议清单")
st.dataframe(
    df[["id", "name", "issue_type", "risk_score", "risk_level",
        "benefit_score", "suggestion", "source_type", "verified"]],
    use_container_width=True, hide_index=True
)

available = df["id"].astype(str).tolist()
selected_id = st.selectbox("查看某条记录的照片证据", available)
chosen = df[df["id"].astype(str) == selected_id].iloc[0]
photo_path = str(chosen["photo_path"])
if photo_path.startswith("session/"):
    image_bytes = st.session_state.get("photo_store", {}).get(photo_path)
    if image_bytes is not None:
        st.image(image_bytes, caption=f"{chosen['name']} - 本次会话照片", width=350)
    else:
        st.caption("该照片只在提交时的浏览器会话中保留，当前不可用。")
elif photo_path:
    file_path = ROOT / photo_path
    if file_path.is_file():
        st.image(str(file_path), caption=f"{chosen['name']} - 证据照片", width=350)
    else:
        st.warning("照片路径存在，但文件未找到。")
else:
    st.caption("当前记录没有附加照片。")

st.warning("风险评分属于未校准原型指标；正式现场决策需专业人员核验，涉及安全和规范的项目应优先遵守法定要求。")
