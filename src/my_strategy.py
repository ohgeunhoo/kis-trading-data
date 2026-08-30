"""내 전략을 KIS 모의 주문 미리보기와 Docker 백테스트로 옮기는 스크립트.

실행:
  uv run python src/my_strategy.py
  uv run python src/my_strategy.py --backtest
  uv run python src/my_strategy.py --start-ui
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

# 레포 루트를 import 경로에 추가한다.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 내 전략 입력값을 한 곳에 모아 둔다.
ETF_CODES: dict[str, str] = {
    "ETF_01": "069500",  # KODEX 200
    "ETF_09": "133690",  # TIGER 미국나스닥100
    "ETF_18": "114260",  # KODEX 국고채3년
    "ETF_19": "153130",  # KODEX 단기채권
    "ETF_22": "132030",  # KODEX 골드선물(H)
}

ETF_NAMES: dict[str, str] = {
    "069500": "KODEX 200",
    "133690": "TIGER 미국나스닥100",
    "114260": "KODEX 국고채3년",
    "153130": "KODEX 단기채권",
    "132030": "KODEX 골드선물(H)",
}

SAMPLE_PRICES: dict[str, int] = {
    "069500": 38_000,
    "133690": 110_000,
    "114260": 105_000,
    "153130": 103_000,
    "132030": 14_000,
}

PREVIEW_CAPITAL = 10_000_000
BACKTEST_INITIAL_CASH = 100_000_000
BACKTEST_START = "2021-06-27"
BACKTEST_END = "2026-06-27"
BACKTEST_TARGET_WEIGHT = 0.18
BACKTESTER_DIR = ROOT.parent / "open-trading-api" / "backtester"
BACKTESTER_PYTHON = BACKTESTER_DIR / ".venv" / "bin" / "python"
REPORT_PATH = (
    BACKTESTER_DIR / "examples" / "output" / "reports" / "monthly_5_etf_report.html"
)
BACKTEST_ENV_FLAG = "MY_STRATEGY_BACKTEST_IN_BACKTESTER_VENV"

SECRET_ARG_NAMES = (
    "APP_KEY",
    "APP_SECRET",
    "ACCOUNT_PASSWORD",
    "KIS_MOCK_APP_KEY",
    "KIS_MOCK_APP_SECRET",
    "KIS_MOCK_ACCOUNT_PASSWORD",
    "paper_app",
    "paper_sec",
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"app(?:key|secret)", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9_\-]{32,}"),
)


def strategy(universe: dict[str, Any], ctx: dict[str, Any]) -> dict[str, float] | None:
    """내 백테스트 비중 규칙을 그대로 둔다."""
    target_weights = {
        "ETF_01": 0.18,
        "ETF_09": 0.18,
        "ETF_18": 0.18,
        "ETF_19": 0.18,
        "ETF_22": 0.18,
    }
    today_month = ctx["date"][:7]
    if ctx["state"].get("last_month") == today_month:
        return None
    ctx["state"]["last_month"] = today_month
    return target_weights


def abort_if_secret_in_args(argv: list[str]) -> None:
    """CLI 인자에 비밀값처럼 보이는 항목이 있으면 값을 되말하지 않는다."""
    joined = " ".join(argv)
    if any(name.lower() in joined.lower() for name in SECRET_ARG_NAMES):
        print("비밀값이 노출됐어요. KIS 포털에서 다시 발급하세요")
        raise SystemExit(1)
    if any(pattern.search(arg) for pattern in SECRET_VALUE_PATTERNS for arg in argv):
        print("비밀값이 노출됐어요. KIS 포털에서 다시 발급하세요")
        raise SystemExit(1)


def require_mock_mode() -> None:
    """실전 모드에서는 어떤 주문 후보도 만들지 않는다."""
    from src.kis_client import is_live

    if is_live():
        raise SystemExit("실전(live) 모드는 차단했습니다. KIS_MODE=mock에서만 실행하세요.")


def keys_present() -> bool:
    """모의 키가 있을 때만 KIS 서버 가격/잔고 조회를 시도한다."""
    return bool(os.getenv("KIS_MOCK_APP_KEY", "").strip()) and bool(
        os.getenv("KIS_MOCK_APP_SECRET", "").strip()
    )


def account_present() -> bool:
    """모의 계좌가 있을 때만 잔고 조회 결과를 신뢰한다."""
    return bool(os.getenv("KIS_MOCK_ACCOUNT_NUMBER", "").strip()) and bool(
        os.getenv("KIS_MOCK_ACCOUNT_PASSWORD", "").strip()
    )


def fetch_prices(token: str | None) -> tuple[dict[str, int], bool]:
    """현재가를 조회하고 실패하면 수업용 샘플 가격으로 미리보기를 이어간다."""
    from labs.lab02_price import fetch_price

    prices: dict[str, int] = {}
    if token is None:
        return dict(SAMPLE_PRICES), True

    try:
        for code in ETF_CODES.values():
            output = fetch_price(token, code)
            prices[code] = int(str(output["stck_prpr"]).replace(",", ""))
        return prices, False
    except Exception as exc:
        print(f"현재가 조회 생략: {type(exc).__name__} - 샘플 가격으로 미리보기합니다.")
        return dict(SAMPLE_PRICES), True


def weights_to_target_qty(
    weights: dict[str, float],
    capital: int,
    prices: dict[str, int],
) -> dict[str, int]:
    """비중을 KIS 종목코드별 목표 수량으로 바꾼다."""
    target_qty: dict[str, int] = {}
    for anon_ticker, weight in weights.items():
        code = ETF_CODES[anon_ticker]
        target_qty[code] = int(capital * weight / prices[code])
    return target_qty


def build_rebalance_orders(
    target_qty: dict[str, int],
    holdings: dict[str, int],
) -> list[dict[str, Any]]:
    """목표 수량과 보유 수량의 차이로 주문 후보를 만든다."""
    orders: list[dict[str, Any]] = []
    for code, target in target_qty.items():
        held = holdings.get(code, 0)
        diff = target - held
        side = "hold" if diff == 0 else ("buy" if diff > 0 else "sell")
        orders.append(
            {
                "code": code,
                "name": ETF_NAMES[code],
                "target_qty": target,
                "held_qty": held,
                "diff": diff,
                "side": side,
                "qty": abs(diff),
            }
        )
    return orders


def print_preview(
    weights: dict[str, float],
    prices: dict[str, int],
    orders: list[dict[str, Any]],
    *,
    offline: bool,
    holdings_known: bool,
) -> None:
    """주문 후보를 표로 보여 주고 서버에는 보내지 않는다."""
    from src.kis_client import get_mode

    print("=== KIS 모의 주문 후보 미리보기 (dry-run, 전송 안 함) ===")
    print(f"mode={get_mode()} | capital={PREVIEW_CAPITAL:,}원")
    if offline:
        print("가격/잔고 일부 조회를 생략하여 샘플 가격 또는 빈 보유수량으로 계산했습니다.")
    if not holdings_known:
        print("계좌 설정 또는 잔고 조회를 확인하지 못해 보유수량은 0으로 가정했습니다.")
    print()
    print(f"{'코드':<8}{'종목명':<18}{'비중':>6}{'현재가':>12}{'목표':>8}{'보유':>8}{'diff':>8}{'주문':>8}")
    for order in orders:
        anon = next(k for k, v in ETF_CODES.items() if v == order["code"])
        side_ko = {"buy": "매수", "sell": "매도", "hold": "유지"}[order["side"]]
        print(
            f"{order['code']:<8}"
            f"{order['name']:<18}"
            f"{weights[anon]:>6.2f}"
            f"{prices[order['code']]:>11,}원"
            f"{order['target_qty']:>8}"
            f"{order['held_qty']:>8}"
            f"{order['diff']:>+8}"
            f"{side_ko:>8}"
        )
    print()
    print("주문 API는 호출하지 않았습니다. 이 파일은 기본적으로 미리보기 전용입니다.")
    print_backtest_note()


def run_preview() -> None:
    """전략 비중을 KIS 모의 주문 후보 수량으로 변환한다."""
    from src.kis_client import get_current_holdings, get_token, load_env

    load_env()
    require_mock_mode()

    ctx = {"date": date.today().isoformat(), "state": {}}
    weights = strategy(universe={}, ctx=ctx)
    if weights is None:
        print("이번 달은 이미 리밸런싱한 상태라 주문 후보가 없습니다.")
        return

    token = None
    if keys_present():
        try:
            token = get_token()
        except Exception as exc:
            print(f"토큰 발급 생략: {type(exc).__name__} - 오프라인 미리보기로 진행합니다.")

    prices, price_offline = fetch_prices(token)
    holdings_known = token is not None and account_present()
    holdings = get_current_holdings(token) if holdings_known else {}
    target_qty = weights_to_target_qty(weights, PREVIEW_CAPITAL, prices)
    orders = build_rebalance_orders(target_qty, holdings)
    print_preview(
        weights,
        prices,
        orders,
        offline=price_offline or token is None or not holdings_known,
        holdings_known=holdings_known,
    )


def monthly_5_etf_algorithm_code() -> str:
    """Lean에서 실행할 월간 리밸런싱 알고리즘 코드를 만든다."""
    symbols = list(ETF_CODES.values())
    return f'''
from AlgorithmImports import *


class KRXEquity(PythonData):
    """한국 주식/ETF 커스텀 데이터"""

    def GetSource(self, config, date, isLive):
        symbol = config.Symbol.Value.lower()
        source = f"/Data/equity/krx/daily/{{symbol}}.csv"
        return SubscriptionDataSource(source, SubscriptionTransportMedium.LocalFile, FileFormat.Csv)

    def Reader(self, config, line, date, isLive):
        if not line.strip():
            return None

        data = KRXEquity()
        data.Symbol = config.Symbol
        try:
            cols = line.split(",")
            data.Time = datetime.strptime(cols[0], "%Y%m%d")
            data.Value = float(cols[4])
            data["Open"] = float(cols[1])
            data["High"] = float(cols[2])
            data["Low"] = float(cols[3])
            data["Close"] = float(cols[4])
            data["Volume"] = int(cols[5])
        except Exception:
            return None
        return data


class MonthlyFiveETFRebalance(QCAlgorithm):
    """매월 첫 데이터일에 5개 ETF를 18%씩 맞춘다."""

    def Initialize(self):
        self.SetStartDate(2021, 6, 27)
        self.SetEndDate(2026, 6, 27)
        self.SetCash({BACKTEST_INITIAL_CASH})
        self.target_weight = {BACKTEST_TARGET_WEIGHT}
        self.last_rebalance_month = None
        self.symbols = []

        for ticker in {symbols!r}:
            symbol = self.AddData(KRXEquity, ticker, Resolution.Daily).Symbol
            self.symbols.append(symbol)

    def OnData(self, data):
        if any(not data.ContainsKey(symbol) for symbol in self.symbols):
            return

        month_key = self.Time.strftime("%Y-%m")
        if self.last_rebalance_month == month_key:
            return

        self.last_rebalance_month = month_key
        for symbol in self.symbols:
            self.SetHoldings(symbol, self.target_weight)
            self.Debug(f"rebalance {{self.Time.date()}} {{symbol.Value}} -> {{self.target_weight:.2f}}")
'''


def run_backtest() -> None:
    """Docker Lean으로 최근 5년 백테스트를 실행한다."""
    from src.kis_client import load_env

    load_env()
    require_mock_mode()

    if not BACKTESTER_DIR.exists():
        raise SystemExit(f"백테스터 폴더를 찾지 못했습니다: {BACKTESTER_DIR}")
    if BACKTESTER_PYTHON.exists() and os.getenv(BACKTEST_ENV_FLAG) != "1":
        env = os.environ.copy()
        env[BACKTEST_ENV_FLAG] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(BACKTESTER_DIR), env.get("PYTHONPATH", "")]
        )
        subprocess.run(
            [str(BACKTESTER_PYTHON), str(Path(__file__).resolve()), "--backtest"],
            cwd=BACKTESTER_DIR,
            env=env,
            check=True,
        )
        return

    os.chdir(BACKTESTER_DIR)
    sys.path.insert(0, str(BACKTESTER_DIR))
    from kis_backtest import LeanClient
    from kis_backtest.providers.kis import KISAuth, KISDataProvider

    auth = KISAuth.from_env(mode="mock")
    client = LeanClient(data_provider=KISDataProvider(auth))
    symbols = list(ETF_CODES.values())

    print("=== Docker Lean 백테스트 시작 ===")
    print(f"symbols={', '.join(symbols)}")
    print(f"period={BACKTEST_START} ~ {BACKTEST_END}")
    print(f"initial_cash={BACKTEST_INITIAL_CASH:,}원")

    result = client.backtest_custom(
        algorithm_code=monthly_5_etf_algorithm_code(),
        symbols=symbols,
        start_date=BACKTEST_START,
        end_date=BACKTEST_END,
        initial_cash=BACKTEST_INITIAL_CASH,
        market_type="krx",
    )

    print("\n=== 백테스트 결과 ===")
    print(f"총 수익률: {result.total_return_pct:.2f}%")
    print(f"CAGR: {result.cagr:.2f}%")
    print(f"Sharpe: {result.sharpe_ratio:.2f}")
    print(f"MDD: {result.max_drawdown:.2f}%")
    print(f"총 거래 수: {result.total_trades}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_path = client.report(
        result=result,
        output_path=REPORT_PATH,
        title="5 ETF 월간 리밸런싱 백테스트",
        subtitle=f"{BACKTEST_START} ~ {BACKTEST_END} | 초기자금 {BACKTEST_INITIAL_CASH:,}원",
    )
    print(f"HTML 리포트: {report_path}")
    print_backtest_note()


def start_docker_ui() -> None:
    """open-trading-api 백테스터 UI를 실행한다."""
    from src.kis_client import load_env

    load_env()
    require_mock_mode()
    if not BACKTESTER_DIR.exists():
        raise SystemExit(f"백테스터 폴더를 찾지 못했습니다: {BACKTESTER_DIR}")
    print("Docker UI를 시작합니다: http://localhost:3001")
    subprocess.run(["./start.sh"], cwd=BACKTESTER_DIR, check=True)


def print_backtest_note() -> None:
    """백테스트와 모의 체결의 차이를 짧게 설명한다."""
    print(
        "대회 백테스트는 '다음 거래일 시가'에 체결됐다고 가정하고, "
        "KIS 모의는 실행한 그 순간 장중 시장가로 체결되므로 두 결과를 직접 빼서 비교하지 않는다."
    )


def parse_args() -> argparse.Namespace:
    """실행 모드를 고른다."""
    parser = argparse.ArgumentParser(description="내 전략 KIS 모의 주문 미리보기")
    parser.add_argument("--backtest", action="store_true", help="Docker Lean 백테스트 실행")
    parser.add_argument("--start-ui", action="store_true", help="Docker 백테스터 UI 실행")
    return parser.parse_args()


def main() -> None:
    """CLI 진입점이다."""
    abort_if_secret_in_args(sys.argv[1:])
    args = parse_args()
    if args.start_ui:
        start_docker_ui()
    elif args.backtest:
        run_backtest()
    else:
        run_preview()


if __name__ == "__main__":
    main()
