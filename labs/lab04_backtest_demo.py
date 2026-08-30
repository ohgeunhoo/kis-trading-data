"""lab04 — 백테스트 신호 → 모의 주문 데모 (하나의 전략, 두 곳에서 실행).

이 lab은 **하나의 전략 함수**(signal())를 두 군데에서 똑같이 쓴다.
  1) 백테스트(backtest): 과거 일봉 CSV 위에서 신호를 재현해 수익률을 계산한다.
  2) 모의 주문(mock_submit): 같은 신호로 실제 KIS **모의투자** 주문 본문을 만든다.

이 파일은 Week14 동반 노트북에서 import해서 쓰는 완성본 데모 스크립트다.
lab01~03처럼 TODO를 채우는 파일이 아니며, 그대로 실행해서 흐름을 확인한다.
lab01~03이 스캐폴딩/API 연결 확인이라면, lab04는 sample strategy 아이디어를
백테스트하고 모의 주문 본문으로 연결하는 수업 본편이다.

⚠️ 핵심 — 백테스트는 체결가를 '미리' 알고, 실거래는 '사후에야' 안다.
  - 백테스트는 신호 다음 날 **시가(open)에 깨끗하게 체결됐다고 가정**한다.
    → 즉 체결가를 계산 시점에 **미리 안다**(가정이니까).
  - 모의 주문은 현재가를 본 뒤 **시장가(ORD_DVSN=01)** 로 나가며, 실제 체결가는
    호가·슬리피지·타이밍에 따라 **주문이 체결된 뒤에야** 알 수 있다.
  - gap_report()는 이 '앎의 시점' 차이를 설명한다(두 숫자를 빼지 않는다).

안전장치:
  - 모의(mock) 전용. live 전환은 KIS_MODE=live 일 때만이며 데모는 막아 둔다.
  - mock_submit()은 기본 dry_run=True — 주문 본문만 만들고 **전송하지 않는다**.
  - API 키가 없거나 조회가 실패해도 오프라인 샘플로 끝까지 동작한다.
  - .env 내용·비밀키는 출력하지 않는다.

실행:  uv run python labs/lab04_backtest_demo.py   (API 키 없이도 완주)
"""

import json
import sys
from pathlib import Path

# 레포 루트를 import 경로에 추가 (src 패키지 + 다른 lab import를 위해)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from labs.lab02_price import fetch_price
from labs.lab03_order import place_order
from src.kis_client import get_mode, get_token, is_live, load_env

# CSV 기본 경로 (이 파일 기준 labs/data/005930_daily.csv)
DEFAULT_CSV = Path(__file__).resolve().parent / "data" / "005930_daily.csv"
DATA_DIR = DEFAULT_CSV.parent  # 종목 CSV 폴더 (labs/data/) — symbol 인자로 종목 교체

# ─── 오프라인/키없음 헬퍼 (companion 노트북과 동일 패턴) ──────────────────────
import os


def _keys_present() -> bool:
    """모의투자 키가 환경변수에 설정되어 있으면 True."""
    return bool(os.getenv("KIS_MOCK_APP_KEY", "").strip())


# 키 없음·조회 실패 시 사용하는 오프라인 대체 현재가 (companion _SAMPLE_OUTPUT 패턴)
_SAMPLE_OUTPUT = {
    "stck_prpr": "76000",  # 현재가
    "stck_oprc": "75800",  # 시가
    "bstp_kor_isnm": "전기·전자",
    "rprs_mrkt_kor_name": "KOSPI200",
}

# 데모용 운용 파라미터 (강의 §300 노트와 동일 규약)
CAPITAL_DEFAULT = 1_000_000  # 운용 자금 (원)
WEIGHT_DEFAULT = 0.3  # 한 종목 배분 비중
SMA_WINDOW = 5  # 단순이동평균 기간


def signal(closes: pd.Series) -> bool:
    """SMA 교차 신호. 오늘 종가가 5일 단순이동평균보다 높으면 매수(True).

    가격 시계열(T 시점까지)만의 순수 함수 — 미래 데이터를 보지 않는다.
    강의 §300 노트의 로직과 동일: today_close > SMA(5).
    """
    if len(closes) < SMA_WINDOW:
        return False
    sma5 = float(pd.Series(closes.rolling(SMA_WINDOW).mean()).iloc[-1])
    today = float(closes.iloc[-1])
    return bool(today > sma5)


def backtest(
    csv_path: str | Path = DEFAULT_CSV,
    capital: float = CAPITAL_DEFAULT,
    weight: float = WEIGHT_DEFAULT,
    *,
    symbol: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """일봉 CSV 위에서 signal()을 재현해 성과를 계산한다.

    핵심 가정(ASSUMPTION):
      신호가 매수로 '전환'된 날, 그 **다음 날 시가(open)에 체결됐다고 가정**한다.
      이것은 어디까지나 가정이다 — 실제로는 호가·슬리피지·체결 지연이 끼어든다.
      그래서 백테스트 수익률은 현실의 상한선에 가깝다(과장 가능).

    파라미터(학생이 바꿔 실험하는 곳):
      symbol — 'labs/data/{symbol}_daily.csv'를 자동 선택 (예: "000660"). csv_path보다 우선.
      capital — 운용 자금(원). start/end — 'YYYY-MM-DD' 기간 슬라이스(포함). None이면 전체.

    반환: trades(체결 로그), n_trades, final_equity, return_pct, first_assumed_fill,
      equity(일별 자산곡선 pd.Series — §700 CAGR/Sharpe/MDD 계산용).
    """
    if symbol is not None:
        csv_path = DATA_DIR / f"{symbol}_daily.csv"
    df = pd.read_csv(csv_path)
    if start is not None:
        df = df.loc[df["date"] >= start]
    if end is not None:
        df = df.loc[df["date"] <= end]
    df = df.reset_index(drop=True)
    closes_all = pd.Series(df["close"], dtype=float)
    opens_all = pd.Series(df["open"], dtype=float)

    cash = float(capital)
    position = 0  # 보유 수량(주)
    prev_sig = False
    trades: list[dict] = []
    first_assumed_fill: float | None = None
    equity_curve: list[float] = []  # 일별 평가금액(자산곡선) — §700 지표용

    # 신호로 진입(매수)·청산(매도)을 반복한다 — 신호 ON→매수, OFF→매도.
    # 둘 다 '신호가 뜬 날의 다음 날 시가'에 체결됐다고 가정한다(아래 ASSUMPTION).
    # 마지막 날은 '다음 날 시가'가 없어 체결을 가정할 수 없다 → range(len-1).
    for t in range(len(df) - 1):
        closes_up_to_t = closes_all.iloc[: t + 1]
        sig = signal(closes_up_to_t)
        next_open = float(opens_all.iloc[t + 1])  # ← 다음 날 시가 = '가정된' 체결가
        next_date = df["date"].iloc[t + 1]

        if sig and not prev_sig and position == 0:
            # 신호가 매수로 '전환' → 다음 날 시가에 매수 체결을 가정
            alloc = cash * weight
            qty = int(alloc // next_open)
            if qty > 0:
                cash -= qty * next_open
                position += qty
                if first_assumed_fill is None:
                    first_assumed_fill = next_open
                trades.append(
                    {
                        "date": next_date,
                        "side": "buy",
                        "assumed_fill_price": next_open,
                        "qty": qty,
                    }
                )
        elif (not sig) and prev_sig and position > 0:
            # 신호가 관망으로 '전환' → 다음 날 시가에 보유분 매도 체결을 가정
            cash += position * next_open
            trades.append(
                {
                    "date": next_date,
                    "side": "sell",
                    "assumed_fill_price": next_open,
                    "qty": position,
                }
            )
            position = 0
        prev_sig = sig
        # 그날 종가로 평가한 일별 자산(현금 + 보유분 평가액) 기록
        equity_curve.append(cash + position * float(closes_all.iloc[t]))

    # 마지막 날: 거래 없이 종가로 평가만 기록 (자산곡선 마지막 점 = final_equity)
    last_close = float(closes_all.iloc[-1])
    equity_curve.append(cash + position * last_close)
    final_equity = cash + position * last_close
    return_pct = (final_equity / capital - 1.0) * 100.0

    return {
        "n_days": len(df),
        "n_trades": len(trades),
        "trades": trades,
        "final_position": position,
        "final_cash": float(cash),
        "final_equity": float(final_equity),
        "return_pct": float(return_pct),
        "first_assumed_fill": first_assumed_fill,
        "equity": pd.Series(equity_curve),  # 일별 자산곡선 (CAGR/Sharpe/MDD용)
    }


def _current_quote(token: str | None, ticker: str) -> tuple[dict, bool]:
    """현재가 조회. 키 없음·실패 시 오프라인 샘플로 폴백.

    반환: (output dict, is_offline). is_offline=True 면 샘플 데이터 사용.
    """
    if token is None or not _keys_present():
        return dict(_SAMPLE_OUTPUT), True
    try:
        return fetch_price(token, ticker), False
    except Exception:
        # 네트워크·HTTP 오류 등 — 데모는 끊기지 않게 샘플로 폴백
        return dict(_SAMPLE_OUTPUT), True


def mock_submit(
    token: str | None,
    ticker: str = "005930",
    qty: int | None = None,
    *,
    capital: float = CAPITAL_DEFAULT,
    weight: float = WEIGHT_DEFAULT,
    dry_run: bool = True,
) -> dict:
    """현재가를 조회해 수량을 산정하고, 모의 주문 본문을 만든다.

    dry_run=True(기본)면 주문 본문만 만들어 반환/출력하고 **전송하지 않는다**.
    dry_run=False 일 때만 place_order()로 실제 모의 주문을 전송한다(mock 전용).
    키가 없거나 조회 실패면 오프라인 샘플 현재가로 본문을 구성한다.
    """
    output, offline = _current_quote(token, ticker)
    price = int(output["stck_prpr"])  # 현재가 (주문 수량 산정 기준)

    if qty is None:
        alloc = capital * weight
        qty = int(alloc // price)

    # 시장가 주문 본문 (lab03.place_order와 동일 스키마, ORD_DVSN='01'=시장가)
    body_preview = {
        "PDNO": ticker,
        "ORD_DVSN": "01",  # 시장가 — 주문가는 0, 체결가는 시장이 정함
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",
    }

    result: dict = {
        "ticker": ticker,
        "order_price_basis": price,  # 주문 산정 기준이 된 '현재가'
        "qty": qty,
        "offline_sample": offline,
        "dry_run": dry_run,
        "body_preview": body_preview,
        "submitted": False,
        "response": None,
    }

    if dry_run:
        print("=== 주문 본문 미리보기 (dry-run, 전송 안 함) ===")
        print(json.dumps(body_preview, ensure_ascii=False, indent=2))
        if offline:
            print("   (오프라인 샘플 현재가 사용 — 실 서버 미접속)")
        return result

    # dry_run=False — 실제 모의 주문 전송 (mock 전용; place_order가 live를 차단)
    if token is None:
        raise RuntimeError("실제 전송(dry_run=False)에는 유효한 token이 필요합니다.")
    resp = place_order(token, ticker, qty, price=0, side="buy")
    result["submitted"] = True
    result["response"] = resp
    return result


def gap_report(backtest_result: dict) -> None:
    """백테스트와 실거래의 '체결가를 아는 시점' 차이를 설명한다.

    핵심은 두 숫자의 뺄셈이 아니다 — 백테스트는 체결가를 **가정으로 미리** 알고,
    실거래는 시장가라 **사후에야** 안다는 점이다. (두 값을 직접 빼서 비교하지 말 것.)
    """
    assumed = backtest_result.get("first_assumed_fill")
    assumed_s = f"{int(assumed):,}원" if assumed is not None else "신호 없음"

    print()
    print("=== 백테스트 vs 실거래 — '체결가를 아는 시점'이 다르다 ===")
    print(
        f"  • 백테스트: 신호 다음날 시가에 '깨끗이' 체결됐다고 가정 → 체결가({assumed_s})를 "
        "미리 안다."
    )
    print(
        "  • 모의 주문: 시장가(ORD_DVSN=01)로 나가므로 실제 체결가는 호가·슬리피지·타이밍에 "
        "따라 주문 뒤에야 안다."
    )
    print(
        "  ⚠️ 이 데모의 CSV는 교육용 고정 데이터라 실제 005930 시세(지금 모의 현재가)와 다르다 "
        "— 두 숫자를 직접 빼서 비교하지 말 것."
    )
    print("  → 핵심은 '백테스트=체결가를 가정으로 미리 안다, 실거래=사후에야 안다'.")


def main() -> None:
    """API 키 없이도 끝까지 도는 오프라인-세이프 전체 데모."""
    load_env()

    if is_live():
        raise SystemExit(
            "❌ lab04 데모는 모의투자(mock) 전용입니다. KIS_MODE=mock 으로 실행하세요."
        )

    mode = get_mode()
    print(f"🧪 lab04 백테스트→모의주문 데모 (mode={mode})")
    print(f"   CSV: {DEFAULT_CSV.name}  |  키 설정됨: {_keys_present()}")
    print()

    # 1) 백테스트 ----------------------------------------------------------
    bt = backtest(DEFAULT_CSV)
    print("📊 백테스트 요약")
    print(f"   거래일수      : {bt['n_days']}일")
    print(f"   체결(가정) 수 : {bt['n_trades']}회")
    print(f"   최종 평가금액 : {int(bt['final_equity']):,}원")
    print(f"   수익률        : {bt['return_pct']:+.2f}%")
    if bt["trades"]:
        first = bt["trades"][0]
        print(
            f"   첫 체결(가정) : {first['date']} @ {int(first['assumed_fill_price']):,}원 "
            f"× {first['qty']}주"
        )

    # 2) 오늘의 신호 (CSV 꼬리로 판정) -------------------------------------
    closes = pd.Series(pd.read_csv(DEFAULT_CSV)["close"], dtype=float)
    today_sig = signal(closes)
    sma5 = float(pd.Series(closes.rolling(SMA_WINDOW).mean()).iloc[-1])
    print()
    print("📈 오늘의 신호 (CSV 마지막 날 기준)")
    print(f"   5일 SMA  : {int(sma5):,}원")
    print(f"   오늘 종가: {int(closes.iloc[-1]):,}원")
    print(f"   신호     : {'매수' if today_sig else '관망'}")

    # 3) dry-run 모의 주문 본문 — 매수 신호가 있는 날에만 주문이 나간다 ----
    print()
    if not today_sig:
        # 관망이면 주문 자체가 없다 (qty=0 주문 본문은 의미가 없으므로 만들지 않는다)
        print(
            "오늘은 매수 신호 없음(관망) → 주문 없음. 신호가 있는 날에만 주문이 나간다."
        )
    else:
        token = None
        if _keys_present():
            try:
                token = get_token()
            except Exception as exc:  # 토큰 실패해도 데모는 계속 (오프라인 폴백)
                print(f"   (토큰 발급 생략 — 오프라인 진행: {type(exc).__name__})")
                token = None
        mock_submit(token, ticker="005930", dry_run=True)

    # 4) 백테스트 vs 실거래 — '체결가를 아는 시점' 설명 --------------------
    gap_report(bt)

    print()
    print("✅ 데모 완료 (오프라인-세이프). 실제 모의 주문은 dry_run=False + 키 필요.")


if __name__ == "__main__":
    main()
