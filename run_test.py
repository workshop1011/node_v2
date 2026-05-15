
from cas.nodes.committee_node_v2 import run

"""
run_test.py
Antigravity 환경에서 3인 위원회 파이프라인을 구동하는 최종 테스트 스크립트
"""

import os
from dotenv import load_dotenv

# .env 파일에서 API 키를 불러와 시스템 환경변수에 등록합니다.
load_dotenv("key.env")

# 우리가 만든 중앙 통제실 함수를 불러옵니다.
from cas.nodes.committee_node_v2 import run

def main():
    print("=" * 70)
    print("🌟 Antigravity 환경: 신용평가 3인 위원회 파이프라인 가동 준비")
    print("=" * 70)

    # 1단계(XGBoost 및 Data Node)를 통과했다고 가정한 Mock State 데이터
    if __name__ == "__main__":
    # 사용자는 이름만 던져줍니다!
        mock_state = {
        "company_name": "오스템임플란트" # 여기에 CSV에 있는 다른 'corp_name'을 넣어도 됩니다.
    }
    



    print("\n▶ 파이프라인을 호출합니다...\n")
    
    try:
        # 중앙 제어 노드 실행
        final_result = run(mock_state)
        
        print("\n" + "=" * 70)
        print("🕵️‍♂️ [에이전트별 상세 심사 내역 공개]")
        print("=" * 70)
        
        # 💡 숨겨져 있던 3명 에이전트의 개별 심사 기록을 모두 순회하며 출력합니다.
        for role, details in final_result["agent_summary"]["agents"].items():
            print(f"\n🔹 에이전트 역할: {role}")
            print(f"  📝 요약: {details['summary']}")
            print("  📋 상세 분석 내역:")
            for finding in details['findings']:
                print(f"    - {finding}")

        print("\n" + "=" * 70)
        print("🏆 [최종 위원회 심사 결과 반환 완료]")
        print("=" * 70)
        
        # 최종 의장(Manager) 에이전트의 Synthesis(심사 메모) 출력
        print("\n[의장 에이전트 최종 심사 메모]")
        print(final_result["agent_summary"]["synthesis"])
        
    except Exception as e:
        print(f"\n🚨 실행 중 치명적 에러 발생: {str(e)}")

if __name__ == "__main__":
    main()