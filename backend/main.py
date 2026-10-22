
"""银龄智城独立后端：第一阶段API。"""

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 直接复用此前开发好的Python核心模块
from core.data import load_data
from core.risk import evaluate

from core.optimizer import optimize
from core.survey_network import (
    sample_network,
    choose_guaranteed_joint_budget,
    evaluate_access,
    PROFILES,
)


# 1. 创建API服务
app = FastAPI(
    title="银龄智城 API",
    version="0.1.0"
)


# 2. 允许本地Vue前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173" ,
         "https://silver-city-web.onrender.com",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)


# 3. 定义预算请求的数据结构
class BudgetRequest(BaseModel):
    budget_wan: float = Field(
        ge=0,
        le=1000,
        description="改造预算，单位：万元"
    )


# 4. 测试后端是否正常启动
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "银龄智城后端"
    }


# 5. 首页统计数据接口
@app.get("/api/dashboard")
def dashboard():

    df = evaluate(load_data())

    return {
        "problem_count": int(len(df)),
        "high_risk_count": int(
            (df["risk_level"] == "高").sum()
        ),
        "verified_count": int(df["verified"].sum()),
        "estimated_total_cost_wan": round(
            float(df["cost_wan"].sum()), 2
        ),
        "notice": "包含模拟数据；并非实际工程评估结论"
    }


# 6. 社区问题与风险地图数据接口
@app.get("/api/problems")
def problems():

    df = evaluate(load_data())

    fields = [
        "id", "name", "issue_type",
        "lat", "lon",
        "risk_score", "risk_level",
        "source_type", "verified", "suggestion"
    ]

    # 把Pandas数据转为标准JSON
    items = json.loads(
        df[fields].to_json(
            orient="records",
            force_ascii=False
        )
    )

    return {
        "total": len(items),
        "items": items
    }


# 7. 基础预算优化接口
@app.post("/api/plan")
def plan(request: BudgetRequest):

    df = evaluate(load_data())

    result = optimize(
        df,
        request.budget_wan
    )

    selected = []

    for p in result["selected"]:
        selected.append({
            "id": str(p["id"]),
            "name": str(p["name"]),
            "cost_wan": round(float(p["cost_wan"]), 2),
            "risk_score": round(float(p["risk_score"]), 2),
            "benefit_score": round(
                float(p["benefit_score"]), 2
            ),
            "suggestion": str(p["suggestion"])
        })

    return {
        "budget_wan": request.budget_wan,
        "spent_wan": result["cost_wan"],
        "benefit_score": result["benefit_score"],
        "selected": selected,
        "notice": (
            "当前接口为基础代理收益优化，"
            "尚不是多群体最低保障方案"
        )
    }


# ============================================
# 公平保障优化 API
# ============================================

@app.post("/api/guarantee-plan")
def guarantee_plan(request: BudgetRequest):
    """
    多群体最低保障约束 + 分层公平优化。

    当前使用内置模拟路网。
    与基础预算优化接口相互独立。
    """

    # 1. 读取候选改造项目
    projects = evaluate(load_data())

    if projects.empty:
        raise HTTPException(
            status_code=400,
            detail="当前没有候选改造项目"
        )

    if len(projects) > 12:
        raise HTTPException(
            status_code=400,
            detail="当前精确优化器最多支持12个候选项目"
        )

    # 2. 读取内置模拟路网
    nodes, edges = sample_network()

    # 3. 调用此前完成的公平保障优化算法
    try:
        result = choose_guaranteed_joint_budget(
            projects,
            nodes,
            edges,
            budget_wan=request.budget_wan,
            verified_only=False
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    # 4. 将项目编号转换为完整项目信息
    project_lookup = {
        str(row["id"]): row
        for row in projects.to_dict("records")
    }

    selected = []

    for project_id in result.get("selected_ids", []):

        project = project_lookup[str(project_id)]

        selected.append({
            "id": str(project["id"]),
            "name": str(project["name"]),
            "cost_wan": float(project["cost_wan"]),
            "risk_score": float(project["risk_score"]),
            "benefit_score": float(
                project["benefit_score"]
            ),
            "suggestion": str(project["suggestion"])
        })

    # 5. 返回供Vue前端使用的JSON
    return {
        "algorithm": "guaranteed_lexicographic",
        "data_mode": "simulation",
        "budget_wan": request.budget_wan,
        **result,
        "selected": selected,
        "notice": (
            "结果来自模拟路网和预设通行条件，"
            "尚未经过真实社区工程验证。"
        )
    }


# ============================================
# 生活出行链与空间推演 API
# ============================================

class TripChainRequest(BaseModel):
    selected_ids: list[str] = Field(default_factory=list)
    profile: str = "轮椅"
    verified_only: bool = False


@app.post("/api/travel-chains")
def travel_chains(request: TripChainRequest):

    # 1. 验证通行能力档案
    if request.profile not in PROFILES:
        raise HTTPException(
            status_code=400,
            detail="未知通行能力档案"
        )

    # 2. 读取当前社区模拟数据
    projects = evaluate(load_data())
    nodes, edges = sample_network()

    known_ids = set(
        projects["id"].astype(str)
    )

    selected_ids = list(dict.fromkeys(
        str(pid).strip()
        for pid in request.selected_ids
        if str(pid).strip()
    ))

    unknown = set(selected_ids) - known_ids

    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"未知改造项目编号：{sorted(unknown)}"
        )

    # 3. 计算改造前状态
    before = evaluate_access(
        nodes,
        edges,
        profile=request.profile,
        finished=(),
        verified_only=request.verified_only
    )

    # 4. 计算项目实施后的状态
    after = evaluate_access(
        nodes,
        edges,
        profile=request.profile,
        finished=selected_ids,
        verified_only=request.verified_only
    )

    # 5. 整理道路节点
    node_data = []

    for row in nodes.to_dict("records"):
        node_data.append({
            "id": str(row["node_id"]),
            "name": str(row["name"]),
            "kind": str(row["kind"]),
            "lat": float(row["lat"]),
            "lon": float(row["lon"])
        })

    # 6. 整理道路及障碍状态
    edge_data = []
    selected_set = set(selected_ids)

    for row in edges.to_dict("records"):

        restrictions = {
            x.strip()
            for x in str(row["blocked_for"]).split(";")
            if x.strip()
        }

        project_id = str(
            row["repair_project_id"]
        ).strip()

        verified = str(
            row["verified"]
        ).strip().lower() in {
            "true", "1", "yes", "是", "已核验"
        }

        # 未核验道路在严格模式下不参与通行
        excluded = request.verified_only and not verified

        blocked_before = (
            excluded or request.profile in restrictions
        )

        blocked_after = (
            excluded or (
                request.profile in restrictions
                and (
                    not project_id
                    or project_id not in selected_set
                )
            )
        )

        edge_data.append({
            "start": str(row["start"]),
            "end": str(row["end"]),
            "length_m": float(row["length_m"]),
            "project_id": project_id,
            "verified": verified,
            "blocked_before": blocked_before,
            "blocked_after": blocked_after,
            "selected_for_repair": (
                bool(project_id)
                and project_id in selected_set
            )
        })

    # 7. 逐条对比完整生活出行链
    before_lookup = {
        (r["origin_id"], r["destination_id"]): r
        for r in before["routes"]
    }

    route_data = []

    for new in after["routes"]:

        key = (
            new["origin_id"],
            new["destination_id"]
        )

        old = before_lookup[key]

        newly_connected = (
            not old["reachable"]
            and new["reachable"]
        )

        route_data.append({
            "origin_id": new["origin_id"],
            "origin": new["origin"],
            "destination_id": new["destination_id"],
            "destination": new["destination"],
            "before_reachable": bool(old["reachable"]),
            "after_reachable": bool(new["reachable"]),
            "newly_connected": newly_connected,
            "before_path": old["route"],
            "after_path": new["route"],
            "before_distance_m": old["distance_m"],
            "after_distance_m": new["distance_m"]
        })

    # 8. 返回给Vue的完整结果
    return {
        "data_mode": "simulation",
        "profile": request.profile,
        "selected_ids": selected_ids,
        "nodes": node_data,
        "edges": edge_data,
        "summary": {
            "before_reachable": before["reachable_pairs"],
            "after_reachable": after["reachable_pairs"],
            "total_pairs": after["total_pairs"],
            "newly_connected": sum(
                int(r["newly_connected"])
                for r in route_data
            ),
            "before_coverage_pct": round(
                before["coverage_pct"], 2
            ),
            "after_coverage_pct": round(
                after["coverage_pct"], 2
            )
        },
        "routes": route_data,
        "notice": (
            "本结果基于模拟路网及预设通行条件。"
            "道路连接线不能直接视为真实导航路线，"
            "模型可通行不代表实际安全认证。"
        )
    }
    
