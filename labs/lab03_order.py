"""lab03 — 주문 / 잔고.

주문에도 현재가 조회와 마찬가지로 접근 토큰(access_token)이 필요하다.
이 lab은 두 가지를 다룬다.
  - 잔고 조회: 읽기 전용(read-only)이라 안전하다.
  - 주문(매수/매도): ⚠️ 주의 — 실제 모의계좌에 주문이 발생한다.

일반 실행(`uv run python labs/lab03_order.py`)은 잔고 조회만 수행한다.
주문은 자동으로 일어나지 않으며, place_order(...)를 직접 호출해야 실행된다.

실행:  uv run python labs/lab03_order.py
"""

import sys
from pathlib import Path

# 레포 루트를 import 경로에 추가 (src 패키지 사용을 위해)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

import requests

from src.kis_client import (
    get_account,
    get_base_url,
    get_credentials,
    get_mode,
    get_token,
    is_live,
    load_env,
)


def _headers(token: str, tr_id: str) -> dict:
    app_key, app_secret = get_credentials(get_mode())
    return {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "content-type": "application/json",
    }


def fetch_balance(token: str) -> list:
    return _fetch_balance_response(token)["output1"]


def fetch_account_summary(token: str) -> dict:
    summary = _summary_row(_fetch_balance_response(token).get("output2", {}))
    return {
        "cash": _format_money(_money_value(summary, "dnca_tot_amt", "prvs_rcdl_excc_amt")),
        "stock_value": _format_money(_money_value(summary, "scts_evlu_amt", "evlu_amt_smtl_amt")),
        "total_value": _format_money(_money_value(summary, "tot_evlu_amt", "nass_amt")),
    }


def _fetch_balance_response(token: str) -> dict:
    base_url = get_base_url(get_mode())
    cano = get_account(get_mode())[0]
    acnt_prdt_cd = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")

    url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
    # KIS 원문 필드는 helper 내부에서만 사용한다.
    # 노트북에서는 fetch_balance(), fetch_account_summary()만 호출한다.
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    response = requests.get(
        url, headers=_headers(token, "VTTC8434R"), params=params, timeout=10
    )
    response.raise_for_status()
    return response.json()


def _summary_row(raw_summary: object) -> dict:
    if isinstance(raw_summary, list):
        return raw_summary[0] if raw_summary else {}
    if isinstance(raw_summary, dict):
        return raw_summary
    return {}


def _money_value(summary: dict, *keys: str) -> int | None:
    for key in keys:
        value = summary.get(key)
        if value in (None, ""):
            continue
        try:
            return int(float(str(value).replace(",", "")))
        except ValueError:
            continue
    return None


def _format_money(value: int | None) -> str:
    return "응답 없음" if value is None else f"{value:,}원"


# ⚠️ 실전 주문 — KIS_MODE=live 상태에서 실제 매매 발생
def place_order(
    token: str, ticker: str, qty: int, price: int = 0, side: str = "buy"
) -> dict:
    if is_live():
        raise RuntimeError(
            "lab03 주문은 모의투자(mock) 전용입니다. KIS_MODE=mock 으로 실행하세요."
        )
    base_url = get_base_url(get_mode())
    cano = get_account(get_mode())[0]
    acnt_prdt_cd = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")
    if side not in ("buy", "sell"):
        raise ValueError(f"side는 'buy' 또는 'sell'만 허용됩니다 (입력: {side!r})")
    tr_id = "VTTC0802U" if side == "buy" else "VTTC0801U"
    url = f"{base_url}/uapi/domestic-stock/v1/trading/order-cash"
    # KIS 원문 주문 필드는 helper 내부에서만 사용한다.
    # 노트북에서는 ticker, qty 같은 쉬운 이름만 다룬다.
    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": ticker,
        "ORD_DVSN": "01" if price == 0 else "00",
        "ORD_QTY": str(qty),
        "ORD_UNPR": str(price),
    }
    response = requests.post(url, headers=_headers(token, tr_id), json=body, timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    load_env()
    if is_live():
        raise SystemExit(
            "❌ lab03은 모의투자(mock) 전용입니다. KIS_MODE=mock 으로 실행하세요."
        )

    mode = get_mode()
    print(f"💰 잔고 조회 시도 (mode={mode}, base={get_base_url(mode)})")
    try:
        token = get_token()
        balance_response = _fetch_balance_response(token)
        holdings = balance_response["output1"]
        summary = _summary_row(balance_response.get("output2", {}))
    except requests.HTTPError as exc:
        print(f"❌ HTTP 오류: {exc}")
        if exc.response is not None:
            # 비밀키는 출력하지 않음 — 응답 본문만 표시
            print(f"   응답: {exc.response.text}")
        raise SystemExit(1)

    print("✅ 잔고 조회 성공")
    cash = _money_value(summary, "dnca_tot_amt", "prvs_rcdl_excc_amt")
    stock_value = _money_value(summary, "scts_evlu_amt", "evlu_amt_smtl_amt")
    total_value = _money_value(summary, "tot_evlu_amt", "nass_amt")
    print(f"   현금/예수금   : {_format_money(cash)}")
    print(f"   주식 평가금액 : {_format_money(stock_value)}")
    print(f"   총 평가금액   : {_format_money(total_value)}")
    if holdings:
        print(f"   보유 종목 {len(holdings)}개")
        # 필드명(prdt_name/pdno/hldg_qty)은 orchestrator가 실제 API로 검증한다.
        for h in holdings:
            name = h.get("prdt_name", "") or h.get("pdno", "")
            qty = h.get("hldg_qty", "")
            print(f"   {name}: {qty}주")
    else:
        print("   보유 종목 없음 (현금 계좌)")

    # 주문 실습: place_order(token, "005930", 1) 을 직접 호출 (교수 안내 후)


if __name__ == "__main__":
    main()
