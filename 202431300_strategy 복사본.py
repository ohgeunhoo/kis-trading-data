def strategy(universe, ctx):
    """
    S&P500 60일 이동평균과 최근 20거래일 수익률을 활용한
    4국면 동적 자산배분 전략입니다.
    """

    INVERSE_TICKER = "ETF_29"
    sp500_ticker = "ETF_10"
    nasdaq_ticker = "ETF_09"
    gold_ticker = "ETF_22"

    # 데이터가 부족할 때 사용할 기본 포트폴리오
    fallback_target = {
        nasdaq_ticker: 0.50,
        sp500_ticker: 0.20,
        gold_ticker: 0.20,
    }

    # 시장 국면 판단에 필요한 ETF_10 데이터 확인
    sp500_df = universe.get(sp500_ticker)
    if sp500_df is None or "close" not in sp500_df.columns or len(sp500_df) < 61:
        return {ticker: weight for ticker, weight in fallback_target.items() if ticker in universe}

    # 원본 데이터를 직접 수정하지 않고 날짜순으로 정렬
    sp500_work = sp500_df.sort_values("date")
    sp500_close = sp500_work["close"]

    # 이전 리밸런싱 정보 불러오기
    state = ctx["state"]
    days_since_rebalance = state.get("days_since_rebalance", 999)
    last_mode = state.get("last_mode", "growth")
    current_portfolio = state.get("current_portfolio", None)

    # 60일 이동평균 대비 현재 가격 위치 확인
    sp500_ma60 = sp500_close.tail(60).mean()
    sp500_current = sp500_close.iloc[-1]
    ratio = sp500_current / sp500_ma60

    # 중립장 세분화를 위한 최근 20거래일 수익률
    sp500_ret20 = sp500_close.iloc[-1] / sp500_close.iloc[-21] - 1

    # 시장 국면 분류
    if ratio > 1.005:
        mode = "growth"
    elif ratio < 0.995:
        mode = "defense"
    else:
        if sp500_ret20 >= 0:
            mode = "neutral_recovery"
        else:
            mode = "neutral_caution"

    # 기본 21거래일마다 리밸런싱, 국면 변화 시 최소 5거래일 이후 조정
    is_rebalance_day = (days_since_rebalance >= 21) or (last_mode != mode and days_since_rebalance >= 5)

    # 리밸런싱 시점이 아니면 기존 포트폴리오 유지
    if not is_rebalance_day and current_portfolio is not None:
        state["days_since_rebalance"] = days_since_rebalance + 1
        return None

    # ETF_02와 ETF_04 중 최근 20거래일 수익률이 높은 국내 성장 ETF 선택
    semi = universe.get("ETF_02")
    battery = universe.get("ETF_04")
    chosen_domestic = "ETF_02"

    if semi is not None and battery is not None:
        if "close" in semi.columns and "close" in battery.columns:
            if len(semi) >= 21 and len(battery) >= 21:
                semi_work = semi.sort_values("date")
                battery_work = battery.sort_values("date")

                semi_ret = semi_work["close"].iloc[-1] / semi_work["close"].iloc[-21] - 1
                battery_ret = battery_work["close"].iloc[-1] / battery_work["close"].iloc[-21] - 1

                if battery_ret > semi_ret:
                    chosen_domestic = "ETF_04"

    # 국면별 목표 비중 설정
    target = {}

    if mode == "growth":
        # 성장장: 성장자산 중심
        target[nasdaq_ticker] = 0.50
        target["ETF_07"] = 0.20
        target[chosen_domestic] = 0.20

    elif mode == "neutral_recovery":
        # 중립-회복장: 주식 비중 일부 유지
        target[nasdaq_ticker] = 0.35
        target["ETF_07"] = 0.10
        target[chosen_domestic] = 0.10
        target[sp500_ticker] = 0.20
        target[gold_ticker] = 0.15

    elif mode == "neutral_caution":
        # 중립-주의장: 금 비중 확대
        target[nasdaq_ticker] = 0.25
        target["ETF_07"] = 0.10
        target[chosen_domestic] = 0.10
        target[sp500_ticker] = 0.15
        target[gold_ticker] = 0.30

    else:
        # 방어장: 금과 인버스 ETF 활용
        target[nasdaq_ticker] = 0.10
        target["ETF_07"] = 0.10
        target[chosen_domestic] = 0.10
        target[sp500_ticker] = 0.10
        target[gold_ticker] = 0.40
        target[INVERSE_TICKER] = 0.10

    # 실제 universe에 존재하는 ETF만 반환
    target = {ticker: weight for ticker, weight in target.items() if ticker in universe}

    # 현재 리밸런싱 정보 저장
    state["days_since_rebalance"] = 0
    state["last_mode"] = mode
    state["current_portfolio"] = target

    return target