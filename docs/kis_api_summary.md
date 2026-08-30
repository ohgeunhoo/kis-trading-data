# KIS REST API 요약 (labs 01–03)

> 초보자는 먼저 노트북과 helper 함수(`get_token`, `fetch_account_summary`, `place_order`)를 사용합니다. 이 문서는 KIS 원문 필드명(`ACNT_PRDT_CD`, `ORD_DVSN` 등)이 궁금할 때 확인하는 API 사전입니다.

한국투자증권(KIS) Open Trading API 핵심 정보 요약. **강의는 모의투자(mock)만 사용한다.**
표기된 사실 중 ✅ 는 이번 세션에서 모의 서버 대상 라이브 검증을 완료한 항목, ⚠️ 검증 대기 는 아직 모의 서버로 실행 검증하지 않은 항목이다.

---

## Base URL

| 구분 | REST Base URL |
|------|--------------|
| 실전 (live) | `https://openapi.koreainvestment.com:9443` |
| 모의 (mock) | `https://openapivts.koreainvestment.com:29443` |

`KIS_MODE` 값에 따라 분기한다. 강의 시연은 반드시 모의(`KIS_MODE=mock`)를 사용한다.

```python
import os
MODE = os.getenv("KIS_MODE", "mock")
BASE_URL = (
    "https://openapi.koreainvestment.com:9443"
    if MODE == "live"
    else "https://openapivts.koreainvestment.com:29443"
)
```

---

## 토큰 발급 (✅ 검증, lab01)

`POST /oauth2/tokenP` 로 접근 토큰을 발급받는다.

- Body: `{"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}`
- 응답: `access_token`

```python
def get_token():
    res = requests.post(f"{BASE_URL}/oauth2/tokenP", json={
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    })
    res.raise_for_status()
    return res.json()["access_token"]
```

> ⚠️ **운영 주의 — 토큰 재발급 쿨다운**: 토큰 재발급에는 쿨다운이 있다. 발급 후 약 1분 내에 재요청하면 `403`(예: `EGW00133` 류)으로 거부될 수 있다. 따라서 **한 번 발급한 토큰을 재사용**해야 한다 (매 요청마다 새로 발급하지 말 것).

---

## 공통 헤더

토큰 발급 이후 모든 요청 헤더에 아래를 포함한다.

```python
def headers(token, tr_id):
    return {
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
        "content-type": "application/json"
    }
```

| 헤더 | 값 |
|------|----|
| `authorization` | `Bearer {access_token}` |
| `appkey` | APP_KEY |
| `appsecret` | APP_SECRET |
| `tr_id` | 기능별 거래 ID (아래 표 참조) |
| `content-type` | `application/json` |

---

## 엔드포인트 요약 표

| 기능 | Method | Path | tr_id 모의 | tr_id 실전 | 상태 |
|------|--------|------|-----------|-----------|------|
| 현재가 조회 | GET | `/uapi/domestic-stock/v1/quotations/inquire-price` | `FHKST01010100` | `FHKST01010100` | ✅ 검증 |
| 일별 시세 조회 | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` | `FHKST03010100` | `FHKST03010100` | ✅ 검증 (lab04) |
| 잔고 조회 | GET | `/uapi/domestic-stock/v1/trading/inquire-balance` | `VTTC8434R` | `TTTC8434R` | ✅ 검증 |
| 매수 주문 | POST | `/uapi/domestic-stock/v1/trading/order-cash` | `VTTC0802U` | `TTTC0802U` | ⚠️ 부분 검증 |
| 매도 주문 | POST | `/uapi/domestic-stock/v1/trading/order-cash` | `VTTC0801U` | `TTTC0801U` | ⚠️ 부분 검증 |

> 현재가 조회의 tr_id는 모의·실전이 동일(`FHKST01010100`)하다.

---

## 현재가 조회 (✅ 검증, lab02)

`GET /uapi/domestic-stock/v1/quotations/inquire-price`, tr_id `FHKST01010100`

- Params: `{"fid_cond_mrkt_div_code": "J", "fid_input_iscd": "종목코드"}`
- 응답: `output`

확인된 필드:

- ✅ `output["stck_prpr"]` = 현재가 (정수형 문자열, 예: 삼성전자 `005930` → `"317000"`)

> ⚠️ **중요 정정 — 종목명 필드 없음**: `inquire-price`의 `output`에는 **종목명(회사명) 필드가 없다.** `hts_kor_isnm` 키는 **존재하지 않으며** 접근 시 `KeyError`가 발생한다. 이름이 비슷한 필드는 다음 두 개뿐이며 회사명이 아니다.
> - `bstp_kor_isnm` = 업종명 (예: `"전기·전자"`)
> - `rprs_mrkt_kor_name` = 대표시장 (예: `"KOSPI200"`)
>
> 따라서 출력은 **종목코드 + 가격**으로 한다.

> ℹ️ 005930(보통주) 기준 검증. ETF/ETN 등은 일부 필드가 비거나 의미가 다를 수 있으니 stck_prpr 존재 여부를 확인하라.

```python
def get_price(token, ticker="005930"):  # 005930 = 삼성전자
    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers(token, "FHKST01010100"),
        params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": ticker}
    )
    res.raise_for_status()
    data = res.json()["output"]
    print(f"{ticker}: {int(data['stck_prpr']):,}원")  # 종목명 필드 없음 → 종목코드로 출력
```

---

## 잔고 조회 (✅ 검증, lab03)

`GET /uapi/domestic-stock/v1/trading/inquire-balance`, tr_id 모의 `VTTC8434R` / 실전 `TTTC8434R`

Params:

| 파라미터 | 값 | 설명 |
|----------|----|----|
| `CANO` | 8자리 계좌번호 | |
| `ACNT_PRDT_CD` | `"01"` | 계좌상품코드 (기본값) |
| `AFHR_FLPR_YN` | `"N"` | |
| `OFL_YN` | `""` | |
| `INQR_DVSN` | `"02"` | |
| `UNPR_DVSN` | `"01"` | |
| `FUND_STTL_ICLD_YN` | `"N"` | |
| `FNCG_AMT_AUTO_RDPT_YN` | `"N"` | |
| `PRCS_DVSN` | `"01"` | |
| `CTX_AREA_FK100` | `""` | |
| `CTX_AREA_NK100` | `""` | |

응답: `output1` = 보유종목 리스트. 확인된 필드:

- ✅ `prdt_name` = 종목명
- ✅ `hldg_qty` = 보유수량
- ✅ `pdno` = 종목코드

> ℹ️ 본 lab은 1페이지(output1)만 검증했다. 보유종목이 많으면 응답 헤더 tr_cont 와 CTX_AREA_FK100/NK100 로 다음 페이지를 반복 조회해야 한다. 계좌 요약·예수금은 output2에 있으며 본 lab에서는 파싱하지 않는다.

---

## 주문 (매수/매도) (⚠️ 부분 검증, lab03)

`POST /uapi/domestic-stock/v1/trading/order-cash`

- tr_id: 모의 매수 `VTTC0802U` / 모의 매도 `VTTC0801U` (실전 매수 `TTTC0802U` / 실전 매도 `TTTC0801U`)
- Body:

| 필드 | 값 | 설명 |
|------|----|----|
| `CANO` | 8자리 계좌번호 | |
| `ACNT_PRDT_CD` | `"01"` | 계좌상품코드 |
| `PDNO` | `"종목코드"` | |
| `ORD_DVSN` | `"01"` | 시장가 |
| `ORD_QTY` | `"수량"` | |
| `ORD_UNPR` | `"0"` | 시장가 주문 시 0 |

> ⚠️ 부분 검증 (2026-05-29): place_order(005930, 1주, 시장가)를 모의 서버로 1회 제출한 결과 rt_cd=1 / msg "모의투자 장종료" — 즉 인증·tr_id·엔드포인트는 정상 도달했고 hashkey/EXCG_ID 관련 오류는 없었다. 다만 장종료로 실제 체결(rt_cd=0)은 미확인이며, 장마감 게이트가 본문 검증보다 먼저 동작할 수 있어 hashkey 불필요는 확정 아님 → 장중(평일 09:00–15:30 KST) 재테스트로 최종 확정. 또한 hashkey 필요 여부, EXCG_ID_DVSN_CD(거래소 구분) 등 필수 필드 완전성, ORD_DVSN 의미도 장중 제출로 확정되기 전까지 미확정이다.

> 🕒 장마감/휴장 중 시장가 주문 결과(거부/대기/오류)는 검증되지 않았다. 주문 테스트는 장중 모의환경에서만, rt_cd·msg_cd·msg1을 그대로 기록한다.

> 💳 매수 시 예수금 부족·빈 계좌면 주문이 거부될 수 있다(코드 버그 아님). 잔고 output1이 비어도 정상이다.

> 🛑 **안전 규칙**
> - 주문은 `KIS_MODE=mock` 에서만 실행한다.
> - lab03은 일반 실행 시 **잔고 조회만** 수행하며, 주문은 자동 실행하지 않는다.
