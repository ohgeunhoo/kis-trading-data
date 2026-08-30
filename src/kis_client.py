"""KIS REST 공통 클라이언트 — 모든 lab이 공유하는 최소 유틸.

- KIS_MODE(mock/live)에 따라 base URL · APP KEY/SECRET · 계좌를 선택한다.
- get_token()은 lab02 이후가 재사용한다. lab01은 학습을 위해 토큰 발급을 직접 구현한다.
"""

import json
import os
import time

import requests
from dotenv import load_dotenv

# 실전(live) / 모의(mock) REST Base URL (KIS 공식)
LIVE_BASE = "https://openapi.koreainvestment.com:9443"
MOCK_BASE = "https://openapivts.koreainvestment.com:29443"


def load_env(path: str = ".env") -> None:
    """.env를 os.environ에 로드한다 (기존 환경변수는 덮어쓰지 않음)."""
    load_dotenv(path)


def get_mode() -> str:
    """실행 모드 반환. 기본값은 mock(모의투자)."""
    return os.getenv("KIS_MODE", "mock").strip().lower()


def is_live(mode: str | None = None) -> bool:
    return (mode or get_mode()) == "live"


def get_base_url(mode: str | None = None) -> str:
    return LIVE_BASE if is_live(mode) else MOCK_BASE


def get_credentials(mode: str | None = None) -> tuple[str, str]:
    """(app_key, app_secret) 반환. mode(mock/live)에 맞는 키를 고른다."""
    prefix = "KIS_LIVE" if is_live(mode) else "KIS_MOCK"
    return (
        os.getenv(f"{prefix}_APP_KEY", "").strip(),
        os.getenv(f"{prefix}_APP_SECRET", "").strip(),
    )


def get_account(mode: str | None = None) -> tuple[str, str]:
    """(계좌번호, 계좌비밀번호) 반환. lab03(주문)·잔고 조회에서 사용."""
    prefix = "KIS_LIVE" if is_live(mode) else "KIS_MOCK"
    return (
        os.getenv(f"{prefix}_ACCOUNT_NUMBER", "").strip(),
        os.getenv(f"{prefix}_ACCOUNT_PASSWORD", "").strip(),
    )


def _cache_paths() -> tuple[str, str]:
    """토큰 캐시 (디렉터리, 파일) 경로. 사용자 홈 아래 전용 폴더를 쓴다."""
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "kis_lab")
    return cache_dir, os.path.join(cache_dir, "token_cache.json")


def get_token(mode: str | None = None) -> str:
    """접근 토큰(access_token)을 발급받아 반환한다.

    프로세스 간 재사용을 위해 사용자 전용 캐시(~/.cache/kis_lab/)에 토큰을 JSON으로 저장한다.
    KIS API는 1분당 1회 발급 제한(EGW00133)이 있으므로, 유효한 토큰이 있으면 재사용한다.
    토큰은 자격증명이므로 소유자 전용(디렉터리 0o700·파일 0o600)으로 쓴다.
    캐시가 꼬이면 ~/.cache/kis_lab/token_cache.json을 삭제하면 다음 실행 때 재발급된다.
    """
    _mode = get_mode() if mode is None else mode
    base_url = get_base_url(_mode)
    app_key, app_secret = get_credentials(_mode)
    if not app_key or not app_secret:
        raise RuntimeError(f"APP KEY/SECRET 미설정 (mode={_mode}). .env를 확인하세요.")

    cache_dir, cache_path = _cache_paths()
    now = time.time()

    # 파일 캐시에서 유효한 토큰이 있으면 재사용
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        entry = cache.get(_mode, {})
        if entry.get("expiry", 0) - 5 > now:
            return entry["token"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        cache = {}

    # 새 토큰 발급
    url = f"{base_url}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data:
        raise RuntimeError(f"토큰 발급 실패: {data}")

    access_token = data["access_token"]
    expires_in = float(data.get("expires_in", 86400))
    expiry_ts = now + max(60.0, expires_in)

    cache[_mode] = {"token": access_token, "expiry": expiry_ts}
    # 토큰은 자격증명 — 소유자 전용 디렉터리/파일로 저장 (심볼릭링크 추종 금지)
    try:
        os.makedirs(cache_dir, mode=0o700, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(cache_path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass  # 캐시 쓰기 실패는 무시 — 다음 실행 때 재발급

    return access_token


def fetch_daily_ohlc(
    token: str, ticker: str = "005930", count: int = 100
) -> list[dict]:
    """국내주식 일봉(일자별 OHLCV)을 조회해 최신순 리스트로 반환한다.

    lab04 백테스트가 쓰는 '진짜 일봉 데이터를 받아오는 법'을 보여주는 함수다.
    (lab04 데모는 오프라인 CSV로 동작하지만, 실데이터는 이 함수로 받는다.)

    엔드포인트: /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
    tr_id     : FHKST03010100 (국내주식 기간별 시세 - 일/주/월/년)
    lab02(fetch_price)와 동일한 GET 패턴(Bearer 토큰 + appkey/appsecret/tr_id 헤더)을 따른다.

    파라미터:
      fid_cond_mrkt_div_code='J'  (주식)
      fid_input_iscd=ticker       (종목코드, 예: 005930)
      fid_input_date_1 / _2       (조회 시작/종료일 YYYYMMDD; 종료일은 오늘)
      fid_period_div_code='D'     (일봉)
      fid_org_adj_prc='0'         (수정주가 0=원주가, 1=수정주가)

    반환: KIS 응답의 output2(일자별 레코드) 리스트. 각 항목 키 예시 —
      stck_bsop_date(영업일자), stck_oprc(시가), stck_hgpr(고가),
      stck_lwpr(저가), stck_clpr(종가), acml_vol(누적 거래량).

    주의: 한 번 호출에 약 100영업일까지 반환된다. count는 시작일 추정에만 쓰며
    더 긴 구간은 날짜를 옮겨 가며 여러 번 호출해야 한다(페이지네이션).
    """
    import datetime as _dt

    app_key, app_secret = get_credentials(get_mode())
    base_url = get_base_url(get_mode())

    today = _dt.date.today()
    # 영업일이 아닌 달력일 기준으로 넉넉히 거슬러 올라가 시작일을 잡는다.
    start = today - _dt.timedelta(days=int(count) * 2 + 10)

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST03010100",
        "content-type": "application/json",
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": ticker,
        "fid_input_date_1": start.strftime("%Y%m%d"),
        "fid_input_date_2": today.strftime("%Y%m%d"),
        "fid_period_div_code": "D",
        "fid_org_adj_prc": "0",
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["output2"]


def get_current_holdings(token: str | None, mode: str | None = None) -> dict[str, int]:
    """모의 계좌의 현재 보유 수량을 {종목코드: 보유수량} 딕셔너리로 반환한다.

    lab05 리밸런스에서 '목표수량 vs 보유수량'의 보유 쪽을 채우는 함수다.
    잔고 조회(inquire-balance, tr_id=VTTC8434R)를 직접 호출해 output1(보유 종목
    리스트)을 {pdno(종목코드): int(hldg_qty(보유수량))} 형태로 정리한다.

    오프라인-세이프: 토큰이 없거나(token is None) 키가 미설정이거나 HTTP/네트워크
    오류가 나면 **빈 딕셔너리 {}** 를 반환한다. 그러면 호출 측은 보유 0으로 보고
    diff = 목표수량 - 0 = 목표수량 전량을 매수 후보로 계산하게 된다(데모가 끊기지 않음).

    주의: 이 함수는 읽기 전용(read-only) 조회만 한다 — 주문을 보내지 않는다.
    """
    _mode = get_mode() if mode is None else mode
    app_key, app_secret = get_credentials(_mode)
    if token is None or not app_key or not app_secret:
        return {}

    base_url = get_base_url(_mode)
    cano = get_account(_mode)[0]
    acnt_prdt_cd = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")
    url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "VTTC8434R",  # 모의 주식 잔고 조회
        "content-type": "application/json",
    }
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
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        output1 = response.json().get("output1", [])
    except Exception:
        # 네트워크·HTTP·파싱 오류 — 데모가 끊기지 않게 빈 보유로 폴백
        return {}

    holdings: dict[str, int] = {}
    for row in output1:
        code = str(row.get("pdno", "")).strip()
        if not code:
            continue
        try:
            qty = int(float(str(row.get("hldg_qty", "0")).replace(",", "")))
        except (ValueError, TypeError):
            qty = 0
        holdings[code] = qty
    return holdings
