import streamlit as st
import json
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="KIS Trading Dashboard", layout="wide")
st.title("📊 KIS 자동매매 대시보드")

# JSON 파일에서 거래 데이터 읽기
try:
    with open('trading_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("포트폴리오 가치", f"₩{data.get('portfolio_value', 0):,.0f}")
    with col2:
        st.metric("총 수익률", f"{data.get('total_return', 0):.2f}%")
    
    st.subheader("📈 최근 거래 기록")
    if data.get('trades'):
        trades_df = pd.DataFrame(data['trades'][-10:])
        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("거래 기록이 없습니다.")
        
except FileNotFoundError:
    st.warning("trading_data.json 파일을 찾을 수 없습니다.")
except Exception as e:
    st.error(f"오류: {str(e)}")

st.write("🔄 자동 새로고침: 60초마다")
time.sleep(60)
st.rerun()
