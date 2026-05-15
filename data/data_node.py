import os
import pandas as pd
from typing import Any, Dict
from cas.agents.state import AgentState

# 현재 파일 위치 기준으로 Csv_43 폴더 경로 설정 (절대 경로)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(BASE_DIR, "Csv_43")

def data_node(state: AgentState) -> Dict[str, Any]:
    """CSV 데이터를 로드하여 타겟 기업의 재무 지표와 산업 비교 데이터를 추출합니다."""
    
    try:
        # 1. 마스터 재무 데이터 및 Peer 데이터 로드
        master_df = pd.read_csv(os.path.join(CSV_PATH, "feature_43_master.csv"))
        peer_df = pd.read_csv(os.path.join(CSV_PATH, "peer_percentiles.csv"))
        
        target_name = state.get("company_name")
        target_id = state.get("company_id")

        # 💡 [핵심 로직] ID가 없고 이름만 입력된 경우 -> corp_name 컬럼에서 검색!
        if target_name and not target_id:
            match = master_df[master_df['corp_name'] == target_name]
            if not match.empty:
                # 검색 성공 시, 해당 기업의 종목코드를 가져옴 (CSV의 코드 컬럼이 'code'라고 가정)
                target_id = match.iloc[-1]['code']
            else:
                return {"selection_errors": [f"마스터 데이터에서 '{target_name}' 기업을 찾을 수 없습니다."]}

        # ID도 없고 이름도 없으면 에러 반환
        if not target_id:
            return {"selection_errors": ["분석할 기업의 ID(종목코드) 또는 이름이 입력되지 않았습니다."]}

        # 2. 타겟 기업의 최신 데이터 1줄(Row) 추출
        target_row = master_df[master_df['code'] == target_id].iloc[-1]
        source_feature_row = target_row.to_dict()

        # 3. 산업 비교 데이터 (Peer Percentiles) 결합
        industry = source_feature_row.get("industry_category") # 산업군 컬럼명 확인 필요
        peer_comparison = []
        if industry:
            peer_comparison = peer_df[peer_df['industry'] == industry].to_dict(orient="records")

        # 상태값(State)에 쓸 최종 이름 확보
        final_company_name = source_feature_row.get('corp_name', target_name or "Unknown")

        print(f"✅ 데이터 매칭 완료: {final_company_name} (코드: {target_id})")

        return {
            "company_id": str(target_id),
            "company_name": final_company_name,
            "source_feature_row": source_feature_row,
            "peer_comparison_rows": peer_comparison,
            "insufficient_data": False
        }

    except FileNotFoundError as e:
        return {"selection_errors": [f"CSV 파일을 찾을 수 없습니다. 경로를 확인하세요: {str(e)}"]}
    except Exception as e:
        return {"selection_errors": [f"데이터 추출 중 에러 발생: {str(e)}"]}