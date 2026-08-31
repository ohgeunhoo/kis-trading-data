from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import trading_bot
import time
import os
import subprocess
from pathlib import Path

def push_to_github():
    """거래 후 데이터를 GitHub에 자동으로 업로드"""
    try:
        # 환경변수에서 GitHub 정보 읽기
        github_token = os.getenv('GITHUB_TOKEN')
        github_user = os.getenv('GITHUB_USER')
        github_repo = os.getenv('GITHUB_REPO')
        
        if not all([github_token, github_user, github_repo]):
            print("⚠️ GitHub 환경변수가 설정되지 않았습니다.")
            return False
        
        # 리포지토리 경로
        repo_path = Path('/app')
        data_path = repo_path / 'data'
        
        if not data_path.exists():
            print("⚠️ data 폴더를 찾을 수 없습니다.")
            return False
        
        # Git 설정
        os.chdir(repo_path)
        subprocess.run(['git', 'config', 'user.email', f'{github_user}@bot.local'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Trading Bot'], check=True)
        
        # data/ 폴더의 변경사항만 스테이징
        subprocess.run(['git', 'add', 'data/'], check=True)
        
        # 커밋할 내용이 있는지 확인
        result = subprocess.run(['git', 'diff', '--cached', '--exit-code'], 
                              capture_output=True)
        
        if result.returncode == 0:
            print("✅ 변경사항이 없습니다.")
            return True
        
        # 커밋 메시지 생성
        timestamp = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
        commit_msg = f"Update trading data - {timestamp}"
        
        # 커밋
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # GitHub에 푸시 (HTTPS 토큰 사용)
        remote_url = f'https://{github_user}:{github_token}@github.com/{github_user}/{github_repo}.git'
        subprocess.run(['git', 'push', remote_url, 'main'], check=True)
        
        print(f"✅ GitHub에 업로드 완료: {commit_msg}")
        return True
        
    except Exception as e:
        print(f"❌ GitHub 업로드 실패: {str(e)}")
        return False


def schedule_trading():
    scheduler = BackgroundScheduler()
    
    def trading_job():
        """거래 실행 후 데이터 업로드"""
        print(f"\n{'='*50}")
        print("🤖 자동 거래 시작!")
        print(f"시간: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}\n")
        
        try:
            # 거래 실행
            trading_bot.main()
            print("\n✅ 거래 완료!")
            
            # 데이터를 GitHub에 업로드
            time.sleep(2)  # 데이터 저장 대기
            print("\n📤 GitHub에