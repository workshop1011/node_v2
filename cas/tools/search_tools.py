import os
import requests
import datetime

# 실제 운영 시 환경 변수나 설정 파일에서 불러옵니다.
OPENDART_API_KEY = os.environ.get("OPENDART_API_KEY", "YOUR_DART_KEY")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "YOUR_NAVER_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "YOUR_NAVER_SECRET")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "YOUR_TAVILY_KEY")

def search_integrated_risk(company_name: str, stock_code: str) -> str:
    """OpenDART(공시), Naver(뉴스), Tavily(웹)를 통합하여 기업의 꼬리 위험을 검색합니다."""
    combined_results = []
    six_months_ago = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y%m%d')
    today = datetime.datetime.now().strftime('%Y%m%d')

    # 1. OpenDART 공식 공시 목록 검색
    try:
        dart_url = "[https://opendart.fss.or.kr/api/list.json](https://opendart.fss.or.kr/api/list.json)"
        dart_params = {
            "crtfc_key": OPENDART_API_KEY, 
            "corp_code": stock_code, 
            "bgn_de": six_months_ago, 
            "end_de": today, 
            "page_count": "30"
        }
        dart_res = requests.get(dart_url, params=dart_params)
        if dart_res.status_code == 200 and dart_res.json().get('status') == '000':
            noteworthy_filings = []
            risk_keywords = ['소송', '횡령', '배임', '유상증자', '감사', '부도', '회생', '벌금', '과징금']
            for item in dart_res.json().get('list', []):
                if any(kw in item.get('report_nm', '') for kw in risk_keywords):
                    noteworthy_filings.append(f"- [{item['pblntf_dt']}] {item['report_nm']}")
            if noteworthy_filings:
                combined_results.append("=== [OpenDART 공식 리스크 공시] ===")
                combined_results.extend(noteworthy_filings)
    except Exception as e:
        combined_results.append(f"OpenDART 오류: {str(e)}")

    # 2. 네이버 뉴스 검색
    try:
        naver_url = "[https://openapi.naver.com/v1/search/news.json](https://openapi.naver.com/v1/search/news.json)"
        naver_headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        naver_res = requests.get(naver_url, headers=naver_headers, params={"query": f"{company_name} 리스크 소송 횡령 배임", "display": 3, "sort": "date"})
        if naver_res.status_code == 200 and naver_res.json().get('items'):
            combined_results.append("\n=== [Naver News 최신 이슈] ===")
            for item in naver_res.json().get('items'):
                title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                combined_results.append(f"- {title}")
    except Exception as e:
        pass # 에러 발생 시 부드럽게 패스

    # 3. Tavily 웹 검색
    try:
        tavily_url = "[https://api.tavily.com/search](https://api.tavily.com/search)"
        tavily_payload = {"api_key": TAVILY_API_KEY, "query": f"{company_name} legal litigation risk", "max_results": 2}
        t_res = requests.post(tavily_url, json=tavily_payload)
        if t_res.status_code == 200 and t_res.json().get('results'):
            combined_results.append("\n=== [Tavily Web Insights] ===")
            for item in t_res.json().get('results'):
                combined_results.append(f"- {item.get('title')}: {item.get('content')[:100]}...")
    except Exception as e:
        pass

    return "\n".join(combined_results) if combined_results else "검색된 치명적 리스크가 없습니다."