import uuid
from pathlib import Path
import streamlit as st
from core.data import ISSUE_TYPES, UPLOADS_DIR, add_problem, load_data

st.title("① 社区适老化问题采集")
st.caption("先人工标注，再做风险评价；照片上传属于证据采集，不代表已实现AI识别。")

with st.form("new_problem_form", clear_on_submit=True):
    name = st.text_input("位置名称 *", placeholder="例如：5号楼东入口")
    issue_type = st.selectbox("问题类别", ISSUE_TYPES)
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("纬度", value=31.2300, format="%.6f")
    with col2:
        lon = st.number_input("经度", value=121.4710, format="%.6f")

    severity = st.slider("问题严重程度（1轻 - 5重）", 1, 5, 3)
    people = st.number_input("估计受影响人数", min_value=0, max_value=100000, value=50)
    frequency = st.slider("路径使用频率（1低 - 5高）", 1, 5, 3)
    improvement = st.slider("预计改造改善程度（1低 - 5高）", 1, 5, 3)
    cost_wan = st.number_input("预计改造成本（万元）", min_value=0.01, value=1.00, step=0.10)
    source_type = st.selectbox("数据来源", ["模拟", "实地调查"])
    verified = st.checkbox("调查数据已人工核验（仅实地调查数据有效）")
    notes = st.text_area("问题备注 / 数据来源说明")
    photo = st.file_uploader("上传证据照片（可选，jpg/jpeg/png）", type=["jpg", "jpeg", "png"])
    submitted = st.form_submit_button("保存这条问题", type="primary")

if submitted:
    if not name.strip():
        st.error("请先填写位置名称。")
    elif not (-90 <= lat <= 90 and -180 <= lon <= 180):
        st.error("经纬度超出合法范围。")
    elif photo is not None and photo.size > 8 * 1024 * 1024:
        st.error("照片超过8MB，请先压缩后上传。")
    else:
        path = ""
        if photo is not None:
            suffix = Path(photo.name).suffix.lower()
            suffix = suffix if suffix in {".jpg", ".jpeg", ".png"} else ".jpg"
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            file_path = UPLOADS_DIR / f"{uuid.uuid4().hex}{suffix}"
            file_path.write_bytes(photo.getvalue())
            path = f"uploads/{file_path.name}"
        record = {
            "name": name.strip(), "issue_type": issue_type,
            "lat": lat, "lon": lon, "severity": severity,
            "people": people, "frequency": frequency,
            "improvement": improvement, "cost_wan": cost_wan,
            "source_type": source_type,
            "verified": verified if source_type == "实地调查" else False,
            "photo_path": path, "notes": notes.strip(),
        }
        try:
            created_id = add_problem(record)
            st.success(f"保存成功，记录编号：{created_id}")
        except Exception as exc:
            st.error(f"保存失败：{exc}")

st.subheader("问题数据表")
try:
    df = load_data()
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "导出全部问题CSV", df.to_csv(index=False).encode("utf-8-sig"),
        file_name="银龄智城_问题记录.csv", mime="text/csv"
    )
except Exception as exc:
    st.error(f"读取失败：{exc}")
