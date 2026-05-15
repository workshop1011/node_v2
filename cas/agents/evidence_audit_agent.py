"""
cas/agents/evidence_audit_agent.py
외부 뉴스, DART 공시, 거시 경제 환경을 분석하여 오프밸런스 리스크를 탐지하는 통합 에이전트 모듈
"""

# ==========================================
# 1. 라이브러리 Import 부분
# ==========================================
import json
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.anthropic import Claude
from cas.agents.state import AgentState, AgentOutput

# (이전에 작성한 3중 통합 검색 도구를 tools 경로에서 불러온다고 가정합니다)
# from cas.tools.search_tools import search_integrated_risk

# ==========================================
# 2. Pydantic 스키마 및 에이전트 객체 선언
# ==========================================
class EvidenceAuditOutput(BaseModel):
    macro_environmental_impact: str = Field(
        description="거시경제 및 시장 환경이 기업에 미칠 타격 분석 (2~3문장)"
    )
    critical_off_balance_risk: str = Field(
        description="DART 공시/뉴스 기반 치명적 비재무 리스크 요약 (발견 시 상세히, 없으면 '특이사항 없음')"
    )
    has_critical_risk: bool = Field(
        description="횡령, 배임, 소송, 상장폐지 등 치명적 리스크 발견 여부 (True/False)"
    )
    external_risk_level: str = Field(
        description="외부 환경 관점에서의 위험도 (안전 / 주의 / 위험 중 택 1)"
    )

# 💡 [핵심 수정]: output_schema를 제거하고 프롬프트로 JSON 출력을 강력히 강제합니다.
evidence_agent = Agent(
    name="EvidenceAudit_Agent",
    model=Claude(id="claude-opus-4-7"), 
    # tools=[search_integrated_risk], # 실제 환경 시 주석 해제하여 툴 장착
    instructions=[
        "당신은 3인 신용평가 위원회의 '외부 환경 및 리스크 전담 애널리스트(EvidenceAuditAgent)'입니다.",
        "제공된 거시 데이터(스프레드 등)와 도구를 활용해 수집한 뉴스/공시를 분석하여 재무제표에 드러나지 않은 꼬리 위험(Tail Risk)을 추론하세요.",
        "단순한 주가 전망이나 증권사 리포트 같은 노이즈는 철저히 배제하고, DART 공시 원문 등 '팩트' 위주로 탐색하세요.",
        "만약 횡령, 배임, 대규모 소송, 자본잠식 위기 등 기업의 생존을 위협하는 치명적 악재가 발견되면 'has_critical_risk'를 반드시 true로 설정하여 위원장에게 비토권 발동을 경고하세요.",
        "반드시 아래의 정확한 JSON 형식으로만 응답을 출력하세요. 마크다운 기호(```json)나 다른 설명 텍스트를 절대 포함하지 말고 순수 JSON 문자열만 출력해야 합니다.",
        "{",
        '  "macro_environmental_impact": "거시경제 및 시장 환경 타격 분석 내용 (2~3문장)",',
        '  "critical_off_balance_risk": "DART/뉴스 기반 치명적 비재무 리스크 요약 (발견된 경우 상세히, 없으면 특이사항 없음 기재)",',
        '  "has_critical_risk": true 또는 false (소문자로 작성, 치명적 리스크 발견 시 true),',
        '  "external_risk_level": "안전 / 주의 / 위험 중 택 1"',
        "}"
    ]
)

# ==========================================
# 3. 외부에서 호출할 래퍼(Wrapper) 함수
# ==========================================
def build_evidence_agent_output(state: AgentState) -> AgentOutput:
    """
    committee_node_v2에서 호출하는 함수.
    """
    company_name = str(state.get("company_name") or "unknown")
    stock_code = str(state.get("company_id") or "unknown")
    
    # 거시 변수 추출
    source_row = dict(state.get("source_feature_row") or {})
    spec_spread = source_row.get("spec_spread", "N/A")
    
    query = f"""
    기업명: {company_name} (종목코드: {stock_code})
    거시 지표 참고 (투기등급 회사채 스프레드): {spec_spread}
    
    위 기업에 대한 외부 뉴스, DART 공시, 거시 경제 영향을 종합하여 지시된 JSON 규격에 맞게 보고서를 작성하세요.
    """
    
    try:
        response = evidence_agent.run(query)
        
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
        result_data = EvidenceAuditOutput(**result_dict)
        
        macro_status = f"투기경계 스프레드({spec_spread})를 반영한 거시 타격 분석 완료."
        risk_alert = "치명적 리스크 감지됨!" if result_data.has_critical_risk else "치명적 리스크 없음."
        
        summary = (
            "EvidenceAuditAgent는 거시환경, 산업 특성, 뉴스 및 공시를 결합하여 "
            "정량 모델(재무제표)에 덜 드러난 꼬리 위험(Tail Risk)을 분석했습니다."
        )
        
        findings = [
            f"거시 및 시장 환경: {result_data.macro_environmental_impact}",
            f"오프밸런스 리스크: {result_data.critical_off_balance_risk}",
            f"비토권 경고 여부: {risk_alert} (외부 위험도: {result_data.external_risk_level})"
        ]
        
    except json.JSONDecodeError as e:
        summary = "EvidenceAuditAgent JSON 파싱 실패"
        findings = [f"JSON 디코딩 중 에러가 발생했습니다: {e}", f"원시 데이터: {raw_content[:200]}..."]
    except Exception as e:
        summary = f"EvidenceAuditAgent 실행 중 에러 발생: {str(e)}"
        findings = ["외부 리스크 분석을 수행하지 못했습니다."]

    return AgentOutput(
        role="evidence_audit",
        summary=summary,
        findings=findings,
        confidence=0.75,
    )