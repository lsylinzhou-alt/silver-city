"""CSV repository. The automatically generated records are clearly marked as DEMO."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "problems.csv"
UPLOADS_DIR = ROOT / "uploads"

COLUMNS = [
    "id", "name", "issue_type", "lat", "lon", "severity", "people",
    "frequency", "improvement", "cost_wan", "source_type", "verified",
    "photo_path", "notes",
]

ISSUE_TYPES = [
    "台阶/坡道缺失", "休息座椅不足", "照明不足", "路面破损",
    "扶手缺失", "坡度/横坡不友好", "过街不便",
]

# These are synthetic cases at synthetic point positions, not real survey findings.
_DEMOS = [
    ("1号楼门口", "台阶/坡道缺失", 5, 86, 5, 5, 2.0),
    ("西侧步道", "休息座椅不足", 4, 143, 5, 4, 0.8),
    ("北门小路", "照明不足", 4, 180, 4, 4, 4.5),
    ("中庭步行道", "路面破损", 4, 65, 5, 4, 1.2),
    ("便利店转角", "路面破损", 3, 110, 4, 3, 1.6),
    ("2号楼入口", "扶手缺失", 4, 70, 5, 5, 1.4),
    ("社区卫生站入口", "台阶/坡道缺失", 5, 200, 5, 5, 3.2),
    ("小花园", "休息座椅不足", 2, 60, 3, 3, 0.6),
    ("南门步道", "坡度/横坡不友好", 5, 90, 4, 5, 3.8),
    ("东侧人行道", "照明不足", 3, 120, 4, 3, 2.6),
    ("东门过街点", "过街不便", 4, 170, 5, 4, 4.2),
    ("3号楼缓坡", "坡度/横坡不友好", 3, 95, 3, 4, 2.1),
]


def seed_rows():
    rows = []
    for i, (name, issue, severity, people, freq, impr, cost) in enumerate(_DEMOS, 1):
        rows.append({
            "id": f"P{i:03d}", "name": name, "issue_type": issue,
            "lat": round(31.2300 + (i % 4) * 0.0007, 6),
            "lon": round(121.4710 + (i // 4) * 0.0007, 6),
            "severity": severity, "people": people, "frequency": freq,
            "improvement": impr, "cost_wan": cost,
            "source_type": "模拟", "verified": False,
            "photo_path": "", "notes": "演示模拟数据，非真实调查",
        })
    return rows


def _session_records():
    """Session-only records keep public demo visitors isolated from each other."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            return st.session_state.get("submitted_records", [])
    except (ImportError, RuntimeError):
        pass
    return []


def load_data():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        pd.DataFrame(seed_rows(), columns=COLUMNS).to_csv(
            DATA_FILE, index=False, encoding="utf-8-sig"
        )
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig", keep_default_na=False)
    extras = _session_records()
    if extras:
        df = pd.concat([df, pd.DataFrame(extras, columns=COLUMNS)], ignore_index=True)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError("CSV缺少列：" + ", ".join(sorted(missing)))
    for col in ["lat", "lon", "severity", "people", "frequency",
                "improvement", "cost_wan"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    df["verified"] = (
        df["verified"].astype(str).str.strip().str.lower()
        .isin({"true", "1", "yes"})
    )
    return df[COLUMNS]


def add_problem(record):
    """Only save into the current browser session, not a shared cloud CSV."""
    import streamlit as st
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx() is None:
        raise RuntimeError("请在Streamlit网页中添加数据")
    df = load_data()
    existing = set(df["id"].astype(str))
    number = 1
    while f"P{number:03d}" in existing:
        number += 1
    record = dict(record)
    record["id"] = f"P{number:03d}"
    record["verified"] = bool(
        record.get("verified", False)
        and record.get("source_type") == "实地调查"
    )
    st.session_state.setdefault("submitted_records", []).append(record)
    return record["id"]
