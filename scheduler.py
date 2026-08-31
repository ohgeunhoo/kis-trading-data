# -*- coding: utf-8 -*-
import os
import subprocess
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import trading_bot
import time

def push_to_github():
    """GitHub에 거래 데이터를 업로드합니다"""
    try:
        github_token = os.getenv('GITHUB_TOKEN')
        github_user = os.getenv('GITHUB_USER')
        github_repo = os.getenv('GITHUB_REPO')

        if not all([github_token, github_user, github_repo]):
            print("❌ GitHub 환경 변수가 설정되지 않았습니다")
            return False

        # Railway 작업 디렉토리로 이동
        os.chdir('/app')

        # git 사용자 설정
        subprocess.run(['git', 'config', 'user.email', f'{github_user}@trading-bot.local'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Trading Bot'], check=True)

        # 데이터 폴더 변경사항 스테이징
        print("\n📤 GitHub에 데이터 업로드 중...")
        subprocess.run(['git', 'add', 'data/'], check=True)

        # 커밋할 변경사항 확인
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
        if result.returncode == 0:
            print("✅ 업로드할 새로운 데이터가 없습니다")
            return True

        # 타임스탬프와 함께 커밋 메시지 생성
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_message = f"Update trading data - {timestamp}"

        subprocess.run(['git', 'commit', '-m', commit_message], check=True)

        # GitHub으로 푸시 (token 인증 사용)
        remote_url = f"https://{github_user}:{github_token}@github.com/{github_user}/{github_repo}.git"
        subprocess.run(['git', 'push', remote_url, 'main'], check=True)

        print(f"✅ GitHub에 데이터를 성공적으로 업로드했습니다 - {timestamp}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ GitHub 업로드 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def trading_job():
    """거래 작업을 실행하고 GitHub에 데이터를 업로드합니다"""
    try:
        print("\n" + "="*50)
        print(f"거래 작업 시작: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)

        # 거래 봇 실행
        trading_bot.main()

        # 데이터 파일이 작성될 때까지 대기
        time.sleep(2)

        # GitHub에 데이터 푸시
        push_to_github()

        print("\n" + "="*50)
        print(f"거래 작업 완료: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)

    except Exception as e:
        print(f"\n❌ 거래 작업 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

# 스케줄러 설정
scheduler = BackgroundScheduler()
kst = pytz.timezone('Asia/Seoul')

# 15:45 KST에 거래 실행
scheduler.add_job(
    trading_job,
    'cron',
    hour=15,
    minute=45,
    timezone=kst,
    id='daily_trading_job'
)

# 스케줄러 시작
if __name__ == "__main__":
    scheduler.start()
    print("✅ 스케줄러가 시작되었습니다. (매일 15:45 KST에 거래 실행)")

    try:
        # 스케줄러가 계속 실행되도록 유지
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("\n스케줄러가 중지되었습니다")
