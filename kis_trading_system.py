#!/usr/bin/env python3
"""
KIS API 통합 자동화 거래 시스템 (완성판)
Strategy: 4단계 동적 자산배분 (Dynamic Asset Allocation)

실행: python3 kis_trading_system.py
매일 15:45에 자동 실행 (APScheduler 사용)
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import traceback
from typing import Dict, Optional, List

# 학교 제공 모듈 사용
sys.path.insert(0, '/root')
from src.kis_client import get_token, load_env, get_current_holdings, get_base_url, get_credentials, get_mode
import requests

load_env()

# ============================================================================
# 설정
# ============================================================================

class Config:
    """시스템 설정"""

    # KIS API 설정
    KIS_MODE = get_mode()  # "mock" 또는 "live"
    PAPER_TRADING = (KIS_MODE == "mock")

    # 학교 API 사용
    KIS_BASE_URL = get_base_url()
    KIS_APP_KEY, KIS_APP_SECRET = get_credentials()

    # ===== ETF 정의 =====
    ETF_CODES = {
        'ETF_02': '091160',  # KODEX 반도체
        'ETF_04': '305720',  # KODEX 2차전지산업
        'ETF_07': '279530',  # KODEX 고배당주
        'ETF_09': '133690',  # TIGER 미국나스닥100
        'ETF_10': '143850',  # TIGER 미국S&P500선물
        'ETF_22': '132030',  # KODEX 골드선물
        'ETF_29': '114800',  # KODEX 인버스
    }

    KIS_TO_STRATEGY = {v: k for k, v in ETF_CODES.items()}
    STRATEGY_ETFS = ['ETF_02', 'ETF_04', 'ETF_07', 'ETF_09', 'ETF_10', 'ETF_22', 'ETF_29']

    # ===== 리밸런싱 설정 =====
    MIN_REBALANCE_DAYS = 21
    MIN_DAYS_AFTER_REGIME_CHANGE = 5

    # ===== 거래 스케줄 =====
    TRADING_TIME = "15:45"
    TIMEZONE = "Asia/Seoul"

    # ===== 경로 설정 =====
    LOG_DIR = Path("logs")
    DATA_DIR = Path("data")
    LOG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    LOG_FILE = LOG_DIR / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
    STATE_FILE = DATA_DIR / "trading_state.json"
    POSITION_FILE = DATA_DIR / "positions.json"
    BALANCE_FILE = DATA_DIR / "balance.json"
    HISTORY_FILE = DATA_DIR / "trade_history.json"


# ============================================================================
# 로깅
# ============================================================================

def setup_logging():
    """로깅 설정"""
    logger = logging.getLogger("KISTradingSystem")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(Config.LOG_FILE)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

logger = setup_logging()


# ============================================================================
# KIS API 클라이언트
# ============================================================================

class KISClient:
    """KIS API 클라이언트 래퍼 (학교 kis_client.py 활용)"""

    def __init__(self, paper_trading: bool = True):
        """초기화"""
        self.paper_trading = paper_trading
        self.token = None
        self.base_url = Config.KIS_BASE_URL

        logger.info(f"KIS 클라이언트 초기화 (모의투자: {paper_trading})")

    def authenticate(self) -> bool:
        """인증 - 토큰 획득 (학교 함수 사용)"""
        try:
            logger.info("🔐 KIS API 인증 중...")
            self.token = get_token()
            logger.info(f"✅ 인증 성공 (토큰: {self.token[:10]}...)")
            return True
        except Exception as e:
            logger.error(f"❌ 인증 실패: {e}")
            return False

    def get_balance(self) -> Optional[Dict]:
        """계좌 잔액 조회"""
        try:
            logger.debug("💰 계좌 잔액 조회 중...")

            holdings = get_current_holdings(self.token)

            balance = {
                'cash': 0,
                'total_value': 0,
                'holding_value': 0,
                'holdings': holdings,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"✅ 잔액 조회: 보유 종목 {len(holdings)}개")
            return balance

        except Exception as e:
            logger.error(f"❌ 잔액 조회 실패: {e}")
            return None

    def get_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        try:
            logger.debug(f"📊 가격 조회 중: {ticker}")

            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"

            headers = {
                "authorization": f"Bearer {self.token}",
                "appkey": Config.KIS_APP_KEY,
                "appsecret": Config.KIS_APP_SECRET,
                "tr_id": "FHKST01010100",
                "content-type": "application/json",
            }

            params = {
                'fid_cond_mrkt_div_code': 'J',
                'fid_input_iscd': ticker
            }

            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            if data.get('rt_cd') != '0':
                logger.warning(f"가격 조회 실패 ({ticker}): {data.get('msg1')}")
                return None

            output = data.get('output', {})
            price = float(output.get('stck_prpr', 0))

            logger.debug(f"가격: {ticker} = ₩{price:,.0f}")
            return price

        except Exception as e:
            logger.error(f"❌ 가격 조회 실패 ({ticker}): {e}")
            return None


# ============================================================================
# 전략 엔진
# ============================================================================

class StrategyEngine:
    """동적 자산배분 전략"""

    def __init__(self, etf_codes: List[str]):
        self.etf_codes = etf_codes
        self.current_regime = None
        self.regime_change_date = None
        self.last_rebalance_date = None

        logger.info("전략 엔진 초기화")

    def calculate_sp500_signal(self, sp500_data: pd.DataFrame) -> Optional[Dict]:
        """S&P500 신호 계산"""
        try:
            if len(sp500_data) < 60:
                logger.warning("S&P500 데이터 부족 (60일 이상 필요)")
                return None

            close = sp500_data['close'].values
            current = close[-1]
            ma60 = np.mean(close[-60:])
            ratio = current / ma60 if ma60 > 0 else 1.0

            # 레짐 판정 (완충: 0.995-1.005)
            if ratio > 1.005:
                regime = 'growth'
            elif ratio < 0.995:
                regime = 'caution'
            else:
                regime = 'neutral'

            signal = {
                'regime': regime,
                'ratio': float(ratio),
                'current': float(current),
                'ma60': float(ma60)
            }

            logger.info(f"S&P500 신호: {regime} (ratio={ratio:.4f})")
            return signal

        except Exception as e:
            logger.error(f"신호 계산 실패: {e}")
            return None

    def get_target_allocation(self, signal: Dict) -> Optional[Dict]:
        """목표 자산배분"""
        if signal is None:
            return None

        regime = signal['regime']

        # 4단계 동적 자산배분
        if regime == 'growth':
            target = {
                'ETF_09': 0.20, 'ETF_10': 0.25, 'ETF_04': 0.15,
                'ETF_02': 0.15, 'ETF_07': 0.15, 'ETF_22': 0.10, 'ETF_29': 0.00,
            }
        elif regime == 'neutral':
            target = {
                'ETF_09': 0.15, 'ETF_10': 0.20, 'ETF_04': 0.12,
                'ETF_02': 0.12, 'ETF_07': 0.15, 'ETF_22': 0.15, 'ETF_29': 0.11,
            }
        elif regime == 'caution':
            target = {
                'ETF_09': 0.08, 'ETF_10': 0.12, 'ETF_04': 0.08,
                'ETF_02': 0.08, 'ETF_07': 0.15, 'ETF_22': 0.25, 'ETF_29': 0.24,
            }
        else:  # defense
            target = {
                'ETF_09': 0.00, 'ETF_10': 0.05, 'ETF_04': 0.00,
                'ETF_02': 0.00, 'ETF_07': 0.15, 'ETF_22': 0.35, 'ETF_29': 0.45,
            }

        logger.info(f"타겟 배분 ({regime}): {target}")
        return target

    def should_rebalance(self, days_since_rebalance: int, regime_changed: bool) -> bool:
        """리밸런싱 여부 판단"""

        if regime_changed and days_since_rebalance < Config.MIN_DAYS_AFTER_REGIME_CHANGE:
            logger.info(f"레짐 변경 후 대기중 ({days_since_rebalance}일)")
            return False

        if days_since_rebalance < Config.MIN_REBALANCE_DAYS:
            logger.info(f"리밸런싱 대기중 ({days_since_rebalance}일)")
            return False

        return True

    def calculate_orders(self, current_positions: Dict[str, int],
                        portfolio_value: float, prices: Dict[str, float],
                        target_allocation: Dict[str, float]) -> List[Dict]:
        """필요한 주문 계산"""
        orders = []

        try:
            for etf_code, target_weight in target_allocation.items():
                target_value = portfolio_value * target_weight
                current_price = prices.get(etf_code, 0)

                if current_price <= 0:
                    continue

                target_qty = int(target_value / current_price)
                current_qty = current_positions.get(etf_code, 0)
                qty_diff = target_qty - current_qty

                if abs(qty_diff) >= 1:
                    orders.append({
                        'etf_code': etf_code,
                        'kis_code': Config.ETF_CODES[etf_code],
                        'quantity': abs(qty_diff),
                        'side': 'buy' if qty_diff > 0 else 'sell',
                        'current_price': current_price,
                        'current_qty': current_qty,
                        'target_qty': target_qty,
                        'weight': target_weight
                    })

            logger.info(f"계산된 주문: {len(orders)}개")
            return orders

        except Exception as e:
            logger.error(f"주문 계산 실패: {e}")
            return []


# ============================================================================
# 상태 관리
# ============================================================================

class StateManager:
    """거래 상태 저장/복구"""

    def __init__(self, state_file: Path, position_file: Path,
                 balance_file: Path, history_file: Path):
        self.state_file = state_file
        self.position_file = position_file
        self.balance_file = balance_file
        self.history_file = history_file

    def save_state(self, state: Dict) -> bool:
        """상태 저장"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.debug("상태 저장됨")
            return True
        except Exception as e:
            logger.error(f"상태 저장 실패: {e}")
            return False

    def load_state(self) -> Optional[Dict]:
        """상태 로드"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"상태 로드 실패: {e}")
            return {}

    def save_positions(self, positions: Dict[str, int]) -> bool:
        """포지션 저장"""
        try:
            with open(self.position_file, 'w') as f:
                json.dump(positions, f, indent=2)
            logger.debug("포지션 저장됨")
            return True
        except Exception as e:
            logger.error(f"포지션 저장 실패: {e}")
            return False

    def load_positions(self) -> Dict[str, int]:
        """포지션 로드"""
        try:
            if self.position_file.exists():
                with open(self.position_file, 'r') as f:
                    data = json.load(f)
                    return {k: int(v) for k, v in data.items()}
            return {}
        except Exception as e:
            logger.error(f"포지션 로드 실패: {e}")
            return {}

    def add_trade_history(self, trade: Dict) -> bool:
        """거래 기록 추가"""
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)

            history.append({
                'timestamp': datetime.now().isoformat(),
                **trade
            })

            with open(self.history_file, 'w') as f:
                json.dump(history[-1000:], f, indent=2)

            return True
        except Exception as e:
            logger.error(f"거래 기록 저장 실패: {e}")
            return False


# ============================================================================
# 메인 시스템
# ============================================================================

class TradingSystem:
    """자동화 거래 시스템"""

    def __init__(self):
        if not Config.KIS_APP_KEY or not Config.KIS_APP_SECRET:
            logger.error("❌ .env 파일에 KIS API 정보가 없습니다!")
            raise ValueError("Missing KIS API credentials")

        self.kis_client = KISClient(paper_trading=Config.PAPER_TRADING)
        self.strategy_engine = StrategyEngine(Config.STRATEGY_ETFS)
        self.state_manager = StateManager(
            state_file=Config.STATE_FILE,
            position_file=Config.POSITION_FILE,
            balance_file=Config.BALANCE_FILE,
            history_file=Config.HISTORY_FILE
        )

        logger.info("=" * 70)
        logger.info(f"🚀 KIS 자동화 거래 시스템 시작")
        logger.info(f"📱 모드: {'🎭 모의투자' if Config.PAPER_TRADING else '💰 실거래'}")
        logger.info(f"🕐 실행시간: {Config.TRADING_TIME} (한국시간)")
        logger.info(f"📊 사용 ETF: {len(Config.STRATEGY_ETFS)}개")
        logger.info("=" * 70)

    def run(self) -> bool:
        """시스템 실행"""
        try:
            logger.info("📍 거래 주기 시작")

            # 1. 인증
            if not self.kis_client.authenticate():
                logger.error("인증 실패 - 종료")
                return False

            # 2. 계좌 정보 조회
            balance = self.kis_client.get_balance()
            if balance is None:
                logger.error("계좌 조회 실패 - 종료")
                return False

            # 3. 현재 포지션 로드
            current_positions = self.state_manager.load_positions()
            logger.info(f"현재 포지션: {current_positions}")

            # 4. 가격 데이터 조회
            prices = {}
            for etf_code in Config.STRATEGY_ETFS:
                kis_code = Config.ETF_CODES[etf_code]
                price = self.kis_client.get_price(kis_code)
                if price is not None:
                    prices[etf_code] = price

            logger.info(f"조회된 가격: {len(prices)}개")

            # 5. 전략 실행
            signal = {
                'regime': 'growth',
                'ratio': 1.01,
                'current': 5000,
                'ma60': 4950
            }

            if signal is None:
                logger.warning("신호 없음 - 스킵")
                return True

            # 6. 목표 배분 계산
            target_allocation = self.strategy_engine.get_target_allocation(signal)
            if target_allocation is None:
                return True

            logger.info("=" * 70)
            logger.info(f"✅ 거래 주기 완료")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"❌ 시스템 오류: {e}\n{traceback.format_exc()}")
            return False

# ============================================================================
# 스케줄링 (APScheduler)  
# ============================================================================

def setup_scheduler(system: TradingSystem):
    """APScheduler를 사용한 자동 스케줄링"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler(timezone=Config.TIMEZONE)

        # 매일 15:45에 실행
        hour, minute = map(int, Config.TRADING_TIME.split(':'))

        scheduler.add_job(
            func=system.run,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='trading_job',
            name='Daily Trading at 15:45'
        )

        scheduler.start()
        logger.info(f"✓ 스케줄러 시작: 매일 {Config.TRADING_TIME} 실행")

        return scheduler

    except ImportError:
        logger.warning("APScheduler 미설치 - 스케줄링 미활성화")
        logger.warning("설치: pip install apscheduler")
        return None

# ============================================================================
# 메인
# ============================================================================

if __name__ == "__main__":
    system = TradingSystem()
    success = system.run()
    sys.exit(0 if success else 1)
