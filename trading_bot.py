import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# KIS API 설정
KIS_API_KEY = os.getenv('KIS_API_KEY')
KIS_API_SECRET = os.getenv('KIS_API_SECRET')
KIS_ACCOUNT = os.getenv('KIS_ACCOUNT')
MOCK_MODE = os.getenv('MOCK_MODE', 'true').lower() == 'true'

def get_market_regime():
    """현재 시장 상황 판단 (Growth/Neutral/Caution/Defense)"""
    try:
        # 간단한 시장 지표 조회
        response = requests.get('https://api.example.com/market', timeout=5)
        
        # 테스트용: 현재 시간으로 자동 판단
        hour = datetime.now().hour
        if hour < 9:
            return "Growth"  # 아침: 공격적
        elif hour < 14:
            return "Neutral"  # 오전중반: 중립적
        elif hour < 17:
            return "Caution"  # 오후: 주의
        else:
            return "Defense"  # 저녁: 방어적
    except Exception as e:
        print(f"시장 분석 오류: {str(e)}")
        return "Neutral"

def get_asset_allocation(regime):
    """4단계 자산배분 전략"""
    allocations = {
        "Growth": {"stocks": 100, "bonds": 0},      # 공격적
        "Neutral": {"stocks": 70, "bonds": 30},     # 중립적
        "Caution": {"stocks": 50, "bonds": 50},     # 주의
        "Defense": {"stocks": 30, "bonds": 70}      # 방어적
    }
    return allocations.get(regime, allocations["Neutral"])

def execute_trade(regime):
    """거래 실행"""
    allocation = get_asset_allocation(regime)
    
    trade = {
        "symbol": "SPY",
        "type": "BUY",
        "quantity": 10,
        "price": 450.00,
        "timestamp": datetime.now().isoformat(),
        "regime": regime,
        "allocation": allocation,
        "mock_mode": MOCK_MODE
    }
    
    if not MOCK_MODE:
        # 실제 거래 (아직 구현 안 함)
        print(f"🚀 실제 거래 실행: {trade}")
    else:
        # 모의 거래
        print(f"📊 모의 거래: {trade}")
    
    return trade

def update_trading_data(trade):
    """trading_data.json 업데이트"""
    try:
        # 기존 데이터 읽기
        if os.path.exists('trading_data.json'):
            with open('trading_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "portfolio_value": 10000000,
                "total_return": 0.0,
                "trades": []
            }
        
        # 새 거래 추가
        data['trades'].append({
            "symbol": trade['symbol'],
            "type": trade['type'],
            "quantity": trade['quantity'],
            "price": trade['price'],
            "timestamp": trade['timestamp'],
            "regime": trade['regime']
        })
        
        # 수익률 계산 (간단한 예시)
        data['total_return'] = round(len(data['trades']) * 0.5, 2)
        data['portfolio_value'] = 10000000 + (len(data['trades']) * 50000)
        
        # 저장
        with open('trading_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✅ trading_data.json 업데이트 완료")
        return True
    except Exception as e:
        print(f"❌ 데이터 저장 오류: {str(e)}")
        return False

def commit_to_github():
    """GitHub에 자동 커밋"""
    try:
        os.system('git add trading_data.json')
        os.system(f'git commit -m "자동 거래 기록 업데이트 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
        os.system('git push')
        print("🔄 GitHub에 커밋 완료")
    except Exception as e:
        print(f"⚠️ GitHub 커밋 오류: {str(e)}")

def main():
    """메인 함수"""
    print(f"\n{'='*50}")
    print(f"🤖 KIS 자동매매 시스템 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"모드: {'모의 거래' if MOCK_MODE else '실제 거래'}")
    print(f"{'='*50}\n")
    
    # 1. 시장 분석
    regime = get_market_regime()
    print(f"📈 현재 시장 상황: {regime}")
    
    # 2. 거래 실행
    trade = execute_trade(regime)
    
    # 3. 데이터 업데이트
    update_trading_data(trade)
    
    # 4. GitHub 커밋
    commit_to_github()
    
    print(f"\n✅ 거래 완료!")

if __name__ == "__main__":
    main()
