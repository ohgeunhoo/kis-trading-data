"""lab05 — 전략 1(5-ETF 포트폴리오)을 KIS 모의투자 자동화 함수로.

이 lab은 대회 sample strategy '전략 1'(5개 ETF 동일가중, 월간 리밸런스)을 그대로
KIS **모의투자** 주문 흐름으로 옮긴다. 단일 종목이던 §300/§600의 흐름을 여러 종목으로
확장하되, 핵심 사고 흐름은 두 단계로 나눈다.
  STAGE 1) 비중 → 목표수량표 : 종목별로 int(평가금액 × 비중 / 가격) 을 계산한다 (주문 없음).
  STAGE 2) 목표 vs 보유 → 주문후보 : diff = 목표수량 - 보유수량 으로 매수/매도/유지를 가른다.

전략 함수 strategy(universe, ctx)는 **이미 주어진 블랙박스**다 — 학생이 작성·수정하지 않는다.
입력(universe, ctx)·상태(state)·반환(비중 dict)의 안쪽을 파지 않고, 그 함수가 돌려주는
==비중표(weights)==를 어떻게 소비하는지(코드 매핑 → 수량 → diff)에만 집중한다.

⚠️ 결과 비교에 대하여: 장기간의 과거 백테스트 시뮬레이션 수익률과, 오늘 하루 짧은
   모의투자 계좌 평가금액은 ==측정 대상이 다르다==. 둘을 직접 빼서 비교하지 않는다
   (§600의 '체결가를 미리 아느냐/사후에야 아느냐' 정직 프레이밍을 전략 전체 수준으로 들어올린 것).

안전장치(§300/§600/lab04와 동일 규약):
  - 모의(mock) 전용. live 전환은 KIS_MODE=live 일 때만이며 데모는 막아 둔다.
  - mock_rebalance_submit()은 기본 미리보기 모드 — 주문 후보만 보여 주고 **전송하지 않는다**.
  - API 키가 없거나 조회가 실패해도 오프라인 샘플로 끝까지 동작한다.
  - .env 내용·비밀키는 출력하지 않는다.

실행:  uv run python labs/lab05_strategy_kis.py   (API 키 없이도 완주)
"""

import sys
from pathlib import Path

# 레포 루트를 import 경로에 추가 (src 패키지 + 다른 lab import를 위해)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

from labs.lab03_order import place_order
from src.kis_client import (
    get_current_holdings,
    get_mode,
    get_token,
    is_live,
    load_env,
)

# ─── (a) 익명 티커 → 실 KIS ETF 종목코드 매핑 ────────────────────────────────
# 대회 universe는 익명 티커(ETF_01 …)였지만, KIS에 주문하려면 실제 종목코드가 필요하다.
# 각 코드는 ≥2개 독립 출처로 교차검증(triangulate)했다.
ETF_CODES: dict[str, str] = {
    "ETF_01": "069500",  # KODEX 200        — 국내 주식 대형주 (KOSPI200)
    "ETF_09": "133690",  # TIGER 미국나스닥100 — 미국 성장주 (NASDAQ100)
    "ETF_18": "114260",  # KODEX 국고채3년    — 국내 중단기 채권 (3년 국채)
    "ETF_19": "153130",  # KODEX 단기채권     — 국내 단기 채권/현금성
    "ETF_22": "132030",  # KODEX 골드선물(H)  — 금 선물 (방어 역할 기대)
}

# ─── 오프라인/키없음 헬퍼 (lab04·companion 노트북과 동일 패턴) ───────────────


def _keys_present() -> bool:
    """모의투자 키가 환경변수에 설정되어 있으면 True."""
    return bool(os.getenv("KIS_MOCK_APP_KEY", "").strip())


# 키 없음·조회 실패 시 사용하는 오프라인 대체 현재가 (실제 종목코드 기준 샘플 값).
# 실데이터가 아니라 데모를 키 없이 끝까지 돌리기 위한 고정 교육용 값이다.
_SAMPLE_PRICES: dict[str, int] = {
    "069500": 38_000,  # KODEX 200
    "133690": 110_000,  # TIGER 미국나스닥100
    "114260": 105_000,  # KODEX 국고채3년
    "153130": 103_000,  # KODEX 단기채권
    "132030": 14_000,  # KODEX 골드선물(H)
}

# 데모용 운용 파라미터
ACCOUNT_VALUE_DEFAULT = 10_000_000  # 모의 계좌 평가금액(원) — 자본 베이스


# ─── (b) 전략 함수 = 이미 주어진 블랙박스 (학생 작성 대상 아님) ──────────────
# 대회 sample '전략 1'을 그대로 옮긴 것. universe/ctx/state/반환 dict의 안쪽은 다루지 않는다.
# 우리가 쓰는 것은 이 함수가 돌려주는 '비중표(weights)'뿐이다.
def strategy(universe, ctx):
    # 단순 baseline: 5개 ETF 동일가중, 월초마다 리밸런싱
    # ETF_01 KOSPI200 대형주 / ETF_09 Nasdaq100 성장주
    # ETF_18 3년 국채 / ETF_19 단기채권 / ETF_22 금 선물
    targets = {
        "ETF_01": 0.18,  # 국내 주식 대형주
        "ETF_09": 0.18,  # 미국 성장주
        "ETF_18": 0.18,  # 국내 중단기 채권
        "ETF_19": 0.18,  # 국내 단기 채권/현금성
        "ETF_22": 0.18,  # 금 선물 (방어 역할 기대)
    }
    # 오늘 만든 목표 비중은 다음 거래일 시가에 체결됩니다 (T+1 execution)

    # 월초만 리밸런싱: ctx["state"]에 지난번 month를 기록해 두고 비교
    today_month = ctx["date"][:7]  # 예: "2024-03"
    last_month = ctx["state"].get("last_month")
    if last_month == today_month:
        return None  # 같은 달이면 비중 유지 (새 주문 없음)
    ctx["state"]["last_month"] = today_month  # in-place로 갱신 (= 대입이 아님)
    return targets


# ─── (c) STAGE 1: 비중 → 목표수량표 (종목별, 주문 API 없음) ──────────────────
def weights_to_target_qty(
    weights: dict[str, float],
    account_value: float,
    prices: dict[str, int],
) -> dict[str, int]:
    """비중표(익명 티커→비중)를 종목코드별 목표수량으로 바꾼다 (주문 호출 없음).

    §300의 단일 종목 공식 qty = int(capital × weight / price) 를 여러 종목으로 확장한다:
      목표수량_i = int(평가금액 × 비중_i / 가격_i)
    weights의 키는 익명 티커(ETF_01 …)이므로, ETF_CODES로 실 종목코드로 매핑한다.
    """
    target_qty: dict[str, int] = {}
    for anon_ticker, w in weights.items():
        code = ETF_CODES[anon_ticker]  # 익명 티커 → 실 KIS 종목코드
        price = prices[code]
        qty = int(account_value * w / price)  # §300 공식의 종목별 일반화
        target_qty[code] = qty
    return target_qty


# ─── (d) STAGE 2: 목표 vs 보유 → 주문후보표 (diff가 주인공) ──────────────────
def build_rebalance_orders(
    target_qty: dict[str, int],
    holdings: dict[str, int],
) -> list[dict]:
    """목표수량과 현재 보유수량의 차이(diff)로 주문 후보 목록을 만든다.

    diff = 목표수량 - 보유수량 이 이 단계의 ==주인공==이다.
      diff > 0 → 부족한 만큼 매수(buy)
      diff < 0 → 초과분 매도(sell)
      diff == 0 → 이미 목표대로 보유 → 주문 없음
    보유에 없는 종목은 0주로 본다(holdings.get(code, 0)).
    각 후보는 학생이 읽기 쉬운 code, diff, side만 담는다.
    실제 KIS 주문 필드는 lab03.place_order 안에서만 만든다.
    """
    orders: list[dict] = []
    for code, target in target_qty.items():
        diff = target - holdings.get(code, 0)  # 목표 - 보유 (없으면 0주)
        if diff == 0:
            continue  # 이미 목표대로 → 주문 없음
        side = "buy" if diff > 0 else "sell"
        qty = abs(diff)
        orders.append(
            {
                "code": code,
                "target_qty": target,
                "held_qty": holdings.get(code, 0),
                "diff": diff,
                "side": side,
            }
        )
    return orders


# ─── (e) 모의 제출 (DRY_RUN 기본) ────────────────────────────────────────────
def mock_rebalance_submit(
    orders: list[dict],
    token: str | None = None,
    *,
    dry_run: bool = True,
) -> list[dict]:
    """리밸런스 주문 후보들을 미리보기(dry-run)하거나, 실제 모의 주문으로 전송한다.

    dry_run=True(기본)면 각 주문 본문만 출력하고 **전송하지 않는다**.
    dry_run=False 일 때만, 유효한 토큰 + mock 모드에서 place_order()로 실제 전송한다.
    (place_order가 live를 차단하고, 키 없으면 애초에 토큰이 없어 전송 경로로 가지 않는다.)
    """
    if dry_run or token is None or not _keys_present() or is_live():
        print("=== 리밸런스 주문 후보 미리보기 (dry-run, 전송 안 함) ===")
        if not orders:
            print("   (주문 후보 없음 — 목표와 보유가 같거나 이번 달은 관망)")
        for o in orders:
            print(
                f"   {o['code']}  {o['side']:>4}  {abs(o['diff'])}주  "
                f"(목표 {o['target_qty']} / 보유 {o['held_qty']} / diff {o['diff']:+d})"
            )
        if token is None or not _keys_present():
            print("   (오프라인/키 없음 — 실 서버 미접속, 보유는 0주로 가정)")
        return orders

    # dry_run=False — 실제 모의 주문 전송 (mock 전용; 교수 안내/opt-in 상황에서만)
    print("=== 리밸런스 주문 전송 (mock) ===")
    for o in orders:
        resp = place_order(token, o["code"], abs(o["diff"]), price=0, side=o["side"])
        o["response"] = resp
        print(
            f"   {o['code']} {o['side']} {abs(o['diff'])}주 → {resp.get('msg1', resp)}"
        )
    return orders


def main() -> None:
    """API 키 없이도 끝까지 도는 오프라인-세이프 전체 데모."""
    load_env()

    if is_live():
        raise SystemExit(
            "❌ lab05 데모는 모의투자(mock) 전용입니다. KIS_MODE=mock 으로 실행하세요."
        )

    mode = get_mode()
    print(f"🧪 lab05 전략1(5-ETF)→KIS 리밸런스 데모 (mode={mode})")
    print(
        f"   키 설정됨: {_keys_present()}  |  계좌 평가금액(데모): {ACCOUNT_VALUE_DEFAULT:,}원"
    )
    print()

    # 0) 전략 함수 호출 → 비중표 (블랙박스가 돌려주는 weights만 쓴다) -----------
    #    universe는 이 데모에서 쓰지 않으므로 빈 dict, ctx는 고정 날짜 + 빈 state.
    ctx = {"date": "2026-06-02", "state": {}}
    weights = strategy(universe={}, ctx=ctx)
    print("📦 전략 함수가 돌려준 목표 비중표 (weights)")
    if weights is None:
        print("   이번 달은 관망(리밸런스 없음) → 주문 없음")
        print("\n✅ 데모 완료 (오프라인-세이프).")
        return
    for anon, w in weights.items():
        print(f"   {anon} → {ETF_CODES[anon]}  비중 {w:.2f}")

    # 1) STAGE 1: 비중 → 목표수량표 (오프라인 샘플 가격 사용) ------------------
    target_qty = weights_to_target_qty(weights, ACCOUNT_VALUE_DEFAULT, _SAMPLE_PRICES)
    print("\n📊 STAGE 1 — 목표수량표 (주문 없음)")
    print(f"   {'종목코드':<8}{'비중':>6}{'가격':>12}{'목표수량':>10}")
    for anon, w in weights.items():
        code = ETF_CODES[anon]
        print(
            f"   {code:<8}{w:>6.2f}{_SAMPLE_PRICES[code]:>11,}원{target_qty[code]:>9}주"
        )

    # 2) STAGE 2: 목표 vs 보유 → 주문후보표 (오프라인이면 보유 {} = 0주) -------
    token = None
    if _keys_present():
        try:
            token = get_token()
        except Exception as exc:  # 토큰 실패해도 데모는 계속 (오프라인 폴백)
            print(f"   (토큰 발급 생략 — 오프라인 진행: {type(exc).__name__})")
            token = None
    holdings = get_current_holdings(token)  # 오프라인/키없음 → {}
    orders = build_rebalance_orders(target_qty, holdings)
    print("\n🔁 STAGE 2 — 주문후보표 (diff = 목표 - 보유)")
    print(f"   {'종목코드':<8}{'목표':>6}{'보유':>6}{'diff':>7}{'주문':>6}")
    for code in target_qty:
        target = target_qty[code]
        held = holdings.get(code, 0)
        diff = target - held
        side = "유지" if diff == 0 else ("매수" if diff > 0 else "매도")
        print(f"   {code:<8}{target:>6}{held:>6}{diff:>+7}{side:>6}")

    # 3) dry-run 모의 제출 (기본값 — 전송 없음) -------------------------------
    print()
    mock_rebalance_submit(orders, token, dry_run=True)

    print(
        "\n⚠️ 결과 비교: 장기 과거 백테스트 시뮬레이션 수익률과 오늘 하루 모의투자 계좌 "
        "평가금액은 측정 대상이 달라 직접 빼서 비교하지 않는다."
    )
    print("✅ 데모 완료 (오프라인-세이프). 실제 모의 제출은 dry_run=False + 키 필요.")


if __name__ == "__main__":
    main()
