"""Transparent prototype indicators; weights have NOT been empirically calibrated."""
import pandas as pd

SUGGESTIONS = {
    "台阶/坡道缺失": "核查高差和场地条件，论证增设坡道",
    "休息座椅不足": "结合步行路线评估增设休息座椅",
    "照明不足": "先做照度实测，再论证增设或调整照明",
    "路面破损": "现场复核破损范围后提出修复方案",
    "扶手缺失": "评估出入口增设适用扶手的条件",
    "坡度/横坡不友好": "现场测量坡度并论证微更新方式",
    "过街不便": "调查过街流线及信号配时，提出改善建议",
}


def evaluate(df: pd.DataFrame, severity_weight: float = 0.35):
    """Add risk_score and benefit_score, both proxy indicators on a 0..100 scale."""
    if not 0.20 <= severity_weight <= 0.50:
        raise ValueError("严重度权重必须介于0.20与0.50之间")
    data = df.copy()
    if data.empty:
        for c in ["risk_score", "benefit_score"]:
            data[c] = pd.Series(dtype="float")
        for c in ["risk_level", "suggestion"]:
            data[c] = pd.Series(dtype="str")
        return data

    s = data["severity"].clip(0, 5) / 5.0
    p = data["people"].clip(0, 200) / 200.0
    f = data["frequency"].clip(0, 5) / 5.0
    imp = data["improvement"].clip(0, 5) / 5.0

    data["risk_score"] = (100 * (0.60*s + 0.25*f + 0.15*p)).round(2)
    data["benefit_score"] = (
        100 * (severity_weight*s + (0.65-severity_weight)*p
               + 0.20*f + 0.15*imp)
    ).round(2)
    data["risk_level"] = data["risk_score"].map(
        lambda x: "高" if x >= 80 else ("中" if x >= 55 else "低")
    )
    data["suggestion"] = data["issue_type"].map(SUGGESTIONS).fillna(
        "需人工核查后制定改造措施"
    )
    return data.sort_values("risk_score", ascending=False)
