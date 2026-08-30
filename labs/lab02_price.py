"""lab02 — 현재가 조회.

현재가 조회도 모든 요청과 마찬가지로 접근 토큰(access_token)이 필요하다.
토큰 발급은 lab01에서 배웠으므로 여기서는 반복하지 않고 get_token()을 재사용한다.
이 lab에서는 발급받은 토큰으로 종목의 현재가를 조회한다.

실행:  uv run python labs/lab02_price.py
"""

import sys
from pathlib import Path

# 레포 루트를 import 경로에 추가 (src 패키지 사용을 위해)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from src.kis_client import get_base_url, get_credentials, get_mode, get_token, load_env


def fetch_price(token: str, ticker: str = "005930") -> dict:
    app_key, app_secret = get_credentials(get_mode())
    base_url = get_base_url(get_mode())

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST01010100",
        "content-type": "application/json",
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": ticker,
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    output = data.get("output")
    if not isinstance(output, dict):
        raise RuntimeError(f"현재가 응답 형식이 예상과 다릅니다: {data}")
    if "stck_prpr" not in output:
        raise RuntimeError(f"현재가 필드(stck_prpr)가 없습니다: {data}")
    return output


def main() -> None:
    load_env()
    mode = get_mode()
    print(f"📈 현재가 조회 시도 (mode={mode}, base={get_base_url(mode)})")
    ticker = "005930"
    try:
        token = get_token()
        o = fetch_price(token, ticker)
    except requests.HTTPError as exc:
        print(f"❌ HTTP 오류: {exc}")
        if exc.response is not None:
            # 비밀키는 출력하지 않음 — 응답 본문만 표시
            print(f"   응답: {exc.response.text}")
        raise SystemExit(1)

    print("✅ 현재가 조회 성공")
    print(f"   종목코드 {ticker}: {int(o['stck_prpr']):,}원")


if __name__ == "__main__":
    main()
