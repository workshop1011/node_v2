"""
cas/nodes/committee_node_v2.py
3인(The Triad) 다중 에이전트 파이프라인 중앙 제어 노드
"""
from __future__ import annotations  # 💡 반드시 파일의 최상단에 위치해야 합니다!

from datetime import UTC, datetime
from typing import Any, cast

from cas.agents.state import (
    AgentOutput,
    AgentState,
    AuditEntry,
    CommitteeReview,
    Recommendation,
)

# 💡 분리된 3개의 진짜 에이전트 모듈을 Import 합니다
from cas.agents.quant_credit_agent import build_quant_agent_output
from cas.agents.evidence_audit_agent import build_evidence_agent_output
from cas.agents.chair_report_agent import build_chair_agent_output


def run(state: AgentState) -> dict[str, Any]:
    """Run the 3-agent (Triad) Stage 2 scaffold over Stage 1 outputs."""
    xgb = dict(state.get("xgboost_result") or {})
    rule = dict(state.get("rule_result") or {})

    recommendation = cast(
        Recommendation,
        rule.get("recommendation") or state.get("final_recommendation") or "review",
    )
    confidence = round(
        float(rule.get("confidence", state.get("final_confidence", 0.0)) or 0.0),
        4,
    )

    # ==========================================
    # 💡 3인 체제 (The Triad) 순차적 실행 및 데이터 릴레이
    # ==========================================
    
    # 1. 내부 재무 전담 에이전트 가동 (XGBoost 결과와 팩트 전달)
    quant_output = build_quant_agent_output(state, xgb)
    
    # 2. 외부 리스크 전담 에이전트 가동 (DART/뉴스 검색)
    evidence_output = build_evidence_agent_output(state)
    
    # 3. 위원장 에이전트 가동 (앞선 두 에이전트의 findings를 쥐여주고 최종 판결)
    chair_output = build_chair_agent_output(
        state, 
        recommendation, 
        confidence, 
        quant_output.findings, 
        evidence_output.findings
    )
    
    # 최종 리스트로 깔끔하게 묶기
    agents = [quant_output, evidence_output, chair_output]

    # ==========================================
    # 💡 시스템 기록 (Audit 및 Review) 생성
    # ==========================================
    reviews = [
        CommitteeReview(
            perspective=agent.role,
            recommendation=recommendation,
            confidence=agent.confidence,
            rationale=agent.summary,
        )
        for agent in agents
    ]

    agent_summary = {
        "final_recommendation": recommendation,
        "final_confidence": confidence,
        "synthesis": agents[-1].summary, # 위원장(Chair)의 요약을 최종 synthesis로 지정
        "agents": {
            agent.role: {
                "summary": agent.summary,
                "findings": agent.findings,
                "confidence": agent.confidence,
            }
            for agent in agents
        },
    }

    audit = AuditEntry(
        node="agno_agents_triad",
        timestamp=_now(),
        summary=f"Three-agent Stage 2 scaffold completed: {', '.join(agent.role for agent in agents)}",
        metrics={"n_agents": float(len(agents)), "final_confidence": confidence},
    )
    
    # 모든 처리가 끝난 후 단 한 번만 반환(Return)합니다.
    return {
        "agent_outputs": agents,
        "committee_reviews": reviews,
        "agent_summary": agent_summary,
        "final_recommendation": recommendation,
        "final_confidence": confidence,
        "audit": [audit],
    }

def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")