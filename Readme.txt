- 전체폴더 
// key.env, requirements.txt, run_test.py 
> key.env: API 키 (Anthropic, Naver, Tavily, DART 등)를 안전하게 보관하는 환경 변수 파일 (깃허브 업로드 제외) 
> requirements.txt: 프로젝트 구동에 필요한 파이썬 패키지 및 의존성 버전 목록 (agno, pydantic, xgboost 등) 
> run_test.py: 가상/실제 데이터를 주입하여 전체 파이프라인(3인 위원회)을 가동하고, 에이전트별 상세 사고 과정과 최종 결과를 콘솔에 출력하는 실행용 스크립트 
>> cas/nodes/committee_node_v2를 import해 실행하는 코드와, 더미 코드("오스템임플란트", 비율 등이 적힘)가 같이 있습니다. 이후 agent의 각 인자들을 불러와 출력하도록 만들어져 있습니다. 

- cas/agents 
// __init__.py, quant_credit_agent.py, evidence_audit_agent.py, chair_report_agent.py, state.py 
> quant_credit_agent.py: [내부 재무 전담] XGBoost 정량 모델의 1차 판단과 SHAP 변수, Core 재무 지표를 교차 검증하여 기업의 '펀더멘털 방어력(부채/유동성/현금흐름)'을 진단하는 에이전트 모듈 
>> QuantCreditOutput: Pydantic 스키마 간략히 설정했습니다. 
>> CORE43_DICT: 부채, 유동자산, 영엄활동현금흐름, 유동비율의 4개 정보를 core 43에서 가져와 보도록 했습니다. 
>> quant_agent: 에이전트입니다. 프롬포트에는 CORE43_DICT으로 가져오고, 우려하셨던 점인 덮어씌우는 현상이 없도록 조정했습니다. 현재로서는 부채와 현금흐름 검증이 중심적입니다. 
>> build_quant_agent_output: 에이전트 함수입니다. 데이터를 받는 부분과, 쿼리, JSON 변환과 오류 방어 코드가 포함되어 있습니다.  

> evidence_audit_agent.py: [외부 리스크 전담] 3중 통합 크롤러(DART, Naver, Tavily)를 활용하여 횡령/배임/소송 등 재무제표 밖의 치명적 꼬리 위험(Tail Risk)과 거시경제 타격을 추론하는 에이전트 모듈 
>> EvidenceAuditOutput: 스키마 간략히 설정했습니다. 
>> evidence_agent: 마찬가지로 에이전트이고, 프롬포트에는 거시데이와 뉴스/공시 분석을 하도록 만들어져 있습니다. 
>> build_evidence_agent_output: 에이전트 함수입니다. Agno 에러 처리, JSON변환과 맵핑 등이 있습니다.  

> chair_report_agent.py: [최종 위원장] 앞선 두 에이전트의 의견을 취합하여 의견 충돌을 조율하고, 치명적 위험 감지 시 '비토권(Veto Power)'을 발동하여 최종 신용 등급을 확정 및 심사 메모를 작성하는 에이전트 모듈 
>> ChairReportOutput: 스키마 간략히 설정했습니다. 
>> chair_agent: 에이전트이고, 프롬포트에는 각각에서 받아온 해석을 종합하도록 하였으며, 일종의 절대규칙 (has_critical_risk)도 함께 넣었습니다. 출력은 JSON입니다.
>> build_chair_agent_output: 에이전트 함수입니다. 각각의 소견 데이터를 불러오고, JSON 리포트로 출력하게 만들어져 있습니다.

> state.py: LangGraph 및 Agno 파이프라인에서 에이전트 간 주고받는 데이터의 타입(Pydantic 스키마)과 상태(AgentState)를 3인 체제에 맞게 약간 가공했습니다.

- cas/nodes 
// __init__.py, committee_node_v2.py, base_prediction_node.py, data_node.py 
> committee_node_v2.py: [중앙 통제실] 3개의 에이전트 모듈을 순차적으로 호출하여 데이터를 릴레이하고, 백그라운드 에러 까지 잡으며 최종 심사 내역(agent_summary)을 통합 반환하는 종합 노드 
>> 3단계 에이전트 함수 호출과, 딕셔너리 불러오기, 이후 순차적으로 가동시키는 구성입니다. build_chair_agent_output의 구성이 완료되면 반환합니다.

> base_prediction_node.py: XGBoost 모델을 학습/추론하고, 확률 보정(Calibration)을 거쳐 예측 확률(y_proba) 및 SHAP 중요도를 도출하는 1단계 정량 예측 노드 
> data_node.py: CSV 기반의 기업 재무 데이터 스냅샷과 산업 백분위(Peer Percentile) 비교 데이터를 파이프라인에 주입하는 데이터 공급 노드
>> 위 두 파일은 기존에 공유된 파일과 동일합니다.

- 기타 주의할 점  
// 어떤 이유인지는 알 수 없지만 os.~로 API키를 구동하면 하나도 안 먹습니다. 키를 직접 따오는 것이 오류가 덜하니 만약 생긴다면 참고해보세요.
// AI코딩이고 간이수준인 만큼 고도화 진행중입니다.