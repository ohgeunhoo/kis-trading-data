# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="KIS 자동매매 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GitHub에서 데이터 로드 함수
@st.cache_data(ttl=60)
def load_data_from_github():
    """GitHub에서 거래 데이터를 로드합니다"""
    github_user = "oghrock823"
    github_repo = "kis-trading-data"
    branch = "main"
    
    base_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{branch}"
    
    data = {
        "trading_state": None,
        "positions": None,
        "balance": None,
        "trade_history": None
    }
    
    try:
        # trading_data.json 로드
        trading_url = f"{base_url}/trading_data.json"
        response = requests.get(trading_url, timeout=5)
        if response.status_code == 200:
            data["trading_state"] = response.json()
    except Exception as e:
        st.warning(f"trading_data.json 로드 실패: {e}")
    
    try:
        # positions.json 로드
        positions_url = f"{base_url}/data/positions.json"
        response = requests.get(positions_url, timeout=5)
        if response.status_code == 200:
            data["positions"] = response.json()
    except Exception as e:
        st.warning(f"positions.json 로드 실패: {e}")
    
    try:
        # balance.json 로드
        balance_url = f"{base_url}/data/balance.json"
        response = requests.get(balance_url, timeout=5)
        if response.status_code == 200:
            data["balance"] = response.json()
    except Exception as e:
        st.warning(f"balance.json 로드 실패: {e}")
    
    try:
        # trade_history.json 로드
        history_url = f"{base_url}/data/trade_history.json"
        response = requests.get(history_url, timeout=5)
        if response.status_code == 200:
            data["trade_history"] = response.json()
    except Exception as e:
        st.warning(f"trade_history.json 로드 실패: {e}")
    
    return data

def get_kst_time():
    """UTC+9 시간대(한국시간)로 현재 시간을 반환합니다"""
    utc_now = datetime.utcnow()
    kst = utc_now + timedelta(hours=9)
    return kst

# 제목
st.title("📊 KIS 자동매매 대시보드")
st.markdown("---")

# 데이터 로드
with st.spinner("GitHub에서 데이터를 로드 중입니다..."):
    data = load_data_from_github()

# 데이터 확인
if not any([data["trading_state"], data["positions"], data["balance"], data["trade_history"]]):
    st.info("📝 거래 데이터를 기다리는 중입니다. (매일 15:45에 자동 거래 실행)")
    st.info("💡 팁: 60초마다 자동으로 새로고침됩니다")
else:
    # 거래 상태 표시
    if data["trading_state"]:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if "total_asset_value" in data["trading_state"]:
                st.metric(
                    "💰 총 자산",
                    f"₩{data['trading_state'].get('total_asset_value', 0):,.0f}"
                )
        
        with col2:
            if "cash" in data["trading_state"]:
                st.metric(
                    "💵 현금",
                    f"₩{data['trading_state'].get('cash', 0):,.0f}"
                )
        
        with col3:
            if "holdings_value" in data["trading_state"]:
                st.metric(
                    "📈 보유주식가치",
                    f"₩{data['trading_state'].get('holdings_value', 0):,.0f}"
                )
        
        with col4:
            if "cash_ratio" in data["trading_state"]:
                st.metric(
                    "📊 현금비율",
                    f"{data['trading_state'].get('cash_ratio', 0):.1%}"
                )
    
    st.markdown("---")
    
    # 시장 체제
    if data["trading_state"] and "market_regime" in data["trading_state"]:
        st.subheader("🎯 현재 시장 체제")
        regime = data["trading_state"]["market_regime"]
        regime_colors = {
            "growth": "🟢 성장",
            "neutral": "🟡 중립",
            "caution": "🟠 주의",
            "defense": "🔴 방어"
        }
        st.write(f"**{regime_colors.get(regime, regime)}**")
    
    st.markdown("---")
    
    # 현재 보유 주식
    if data["positions"]:
        st.subheader("📌 현재 보유 주식")
        
        positions_list = []
        for ticker, info in data["positions"].items():
            positions_list.append({
                "종목코드": ticker,
                "수량": info.get("quantity", 0),
                "평균가": f"₩{info.get('avg_price', 0):,.0f}",
                "현재가": f"₩{info.get('current_price', 0):,.0f}",
                "평가손익": f"₩{info.get('gain_loss', 0):,.0f}"
            })
        
        if positions_list:
            df_positions = pd.DataFrame(positions_list)
            st.dataframe(df_positions, use_container_width=True, hide_index=True)
        else:
            st.info("현재 보유한 주식이 없습니다")
    
    st.markdown("---")
    
    # 거래 이력
    if data["trade_history"] and isinstance(data["trade_history"], list):
        st.subheader("📋 최근 거래 이력 (최근 20개)")
        
        trades = data["trade_history"][-20:] if len(data["trade_history"]) > 20 else data["trade_history"]
        
        if trades:
            trade_list = []
            for trade in reversed(trades):
                trade_list.append({
                    "일시": trade.get("timestamp", ""),
                    "종목": trade.get("ticker", ""),
                    "유형": "매수" if trade.get("order_type") == "buy" else "매도",
                    "수량": trade.get("quantity", 0),
                    "가격": f"₩{trade.get('price', 0):,.0f}",
                    "상태": trade.get("status", "")
                })
            
            df_trades = pd.DataFrame(trade_list)
            st.dataframe(df_trades, use_container_width=True, hide_index=True)
        else:
            st.info("거래 이력이 없습니다")
    
    st.markdown("---")
    
    # 마지막 업데이트
    current_time = get_kst_time().strftime('%Y-%m-%d %H:%M:%S')
    st.caption(f"🔄 마지막 업데이트: {current_time} | 60초마다 자동 새로고침")

