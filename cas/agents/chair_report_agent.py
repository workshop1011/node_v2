"""
cas/agents/chair_report_agent.py
1/2단계 결과를 융합하고 최종 비토권(Veto) 심사 및 투자 심의 메모를 작성하는 의장(Manager) 모듈
"""

# ==========================================
# 1. 라이브러리 Import 부분
# ==========================================
import json
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.anthropic import Claude
from cas.agents.state import AgentState, AgentOutput, Recommendation

# ==========================================
# 2. Pydantic 스키마 및 에이전트 객체 선언
# ==========================================
class ChairReportOutput(BaseModel):
    final_committee_label: str = Field(
        description="최종 위원회 라벨 (적격 / 보류 / 부적격 중 하나로 제시)"
    )
    veto_triggered: bool = Field(
        description="리서치 결과 치명적 리스크로 인해 비토권(강제 강등)이 발동되었는지 여부 (True/False)"
    )
    conflict_resolution: str = Field(
        description="정량 해석과 외부 근거가 충돌할 경우, 어떤 근거에 가중치를 두어 판결했는지 논리 구성 (2~3문장)"
    )
    executive_summary: str = Field(
        description="최종 투자 심의 메모 (마크다운 포맷의 종합 보고서)"
    )

# 💡 [핵심 수정]: output_schema를 제거하고 프롬프트로 JSON 출력을 강력히 강제합니다.
chair_agent = Agent(
    name="ChairReport_Agent",
    model=Claude(id="claude-opus-4-7"),
    instructions=[
        "당신은 3인 신용평가 위원회의 '최종 의사결정권자(ChairReportAgent)'입니다.",
        "내부 재무 분석가(QuantCredit)의 정량 해석과 외부 리스크 분석가(EvidenceAudit)의 증거를 종합하여 최종 위원회 의견을 작성하세요.",
        "절대 규칙 [Veto Power]: 외부 리스크 분석가가 'has_critical_risk'를 띄웠다면, 재무 점수가 아무리 좋아도 최종 라벨을 무조건 '부적격'으로 강등(Veto)시킵니다.",
        "두 에이전트의 의견이 충돌할 경우, 어떤 의견에 가중치를 두어 최종 결정을 내렸는지 'conflict_resolution'에 명확히 기재하세요.",
        "반드시 아래의 정확한 JSON 형식으로만 응답을 출력하세요. 마크다운 기호(```json)나 다른 설명 텍스트를 절대 포함하지 말고 순수 JSON 문자열만 출력해야 합니다.",
        "{",
        '  "final_committee_label": "적격 / 보류 / 부적격 중 택 1",',
        '  "veto_triggered": true 또는 false (소문자로 작성, 비토권 발동 시 true),',
        '  "conflict_resolution": "의견 충돌 조율 논리 요약 (2~3문장)",',
        '  "executive_summary": "최종 투자 심의 메모 (마크다운 포맷)"',
        "}"
    ]
)

# ==========================================
# 3. 외부에서 호출할 래퍼(Wrapper) 함수
# ==========================================
def build_chair_agent_output(
    state: AgentState, 
    recommendation: Recommendation, 
    confidence: float,
    quant_findings: list[str],
    evidence_findings: list[str]
) -> AgentOutput:
    """
    committee_node_v2에서 호출하는 함수. 
    앞선 두 에이전트의 finding 결과를 입력받아 최종 판결을 내립니다.
    """
    xgb = dict(state.get("xgboost_result") or {})
    prediction_label = str(xgb.get("prediction_label", "unknown"))
    
    query = f"""
    [1단계 기계 학습 원본 판단]
    모델 라벨: {prediction_label}
    
    [내부 재무 분석가 (QuantCredit) 소견]
    {' / '.join(quant_findings)}
    
    [외부 리스크 분석가 (EvidenceAudit) 소견]
    {' / '.join(evidence_findings)}
    
    위 3가지 의견을 종합하여, 비토권 발동 여부를 심사하고 지시된 JSON 규격에 맞게 최종 투자 심의 보고서를 작성하세요.
    """
    
    try:
        response = chair_agent.run(query)
        
        # 💡 [핵심 수정]: Agno의 에러 텍스트 둔갑 방어 및 마크다운 스트립
        raw_content = str(response.content).strip()
        if raw_content.startswith("Error code:"):
            raise ValueError(f"API 에러 문자열이 반환되었습니다: {raw_content}")

        if raw_content.startswith("```json"):
            raw_content = raw_content[7:-3].strip()
        elif raw_content.startswith("```"):
            raw_content = raw_content[3:-3].strip()
            
        # JSON 문자열을 파이썬 딕셔너리로 변환 후 Pydantic 객체로 맵핑
        result_dict = json.loads(raw_content)
        result_data = ChairReportOutput(**result_dict)
        
        veto_status = "발동됨 (중대 리스크 발견)" if result_data.veto_triggered else "미발동"
        
        # summary에는 전체 보고서를 그대로 둡니다. (이게 마지막에 출력될 핵심 데이터입니다)
        summary = result_data.executive_summary
        
        # 💡 [여기 수정!] findings에서는 긴 보고서를 빼고 안내 문구로 바꿉니다.
        findings = [
            f"최종 위원회 라벨: {result_data.final_committee_label}",
            f"비토권(Veto) 발동 여부: {veto_status}",
            f"의견 충돌 조율 논리: {result_data.conflict_resolution}",
            "종합 심사 메모: (하단의 최종 위원회 심사 결과 참조)" # <--- 이렇게 짧게 수정!
        ]
        
    except json.JSONDecodeError as e:
        summary = "ChairReportAgent JSON 파싱 실패"
        findings = [f"JSON 디코딩 중 에러가 발생했습니다: {e}", f"원시 데이터: {raw_content[:200]}..."]
    except Exception as e:
        summary = f"ChairReportAgent 실행 중 에러 발생: {str(e)}"
        findings = ["최종 의견을 종합하지 못했습니다."]

    return AgentOutput(
        role="chair_report",
        summary=summary,
        findings=findings,
        confidence=max(0.6, confidence),
    )