# -*- coding: utf-8 -*-
import os
import json
import base64
import requests
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import trading_bot
import time

def get_kst_time():
    """UTC+9 시간대(한국시간)로 현재 시간을 반환합니다"""
    utc_now = datetime.utcnow()
    return utc_now + timedelta(hours=9)

def push_to_github():
    """GitHub에 거래 데이터를 업로드합니다 (GitHub API 사용)"""
    try:
        github_token = os.getenv('GITHUB_TOKEN')
        github_user = os.getenv('GITHUB_USER')
        github_repo = os.getenv('GITHUB_REPO')

        if not all([github_token, github_user, github_repo]):
            print("❌ GitHub 환경 변수가 설정되지 않았습니다")
            print(f"   GITHUB_TOKEN: {bool(github_token)}")
            print(f"   GITHUB_USER: {bool(github_user)}")
            print(f"   GITHUB_REPO: {bool(github_repo)}")
            return False

        repo_path = '/app'
        data_dir = os.path.join(repo_path, 'data')

        print("\n📤 GitHub에 데이터 업로드 중...")

        # data 디렉토리가 없으면 생성
        if not os.path.exists(data_dir):
            print("⚠️  data 디렉토리가 없습니다. 생성 중...")
            try:
                os.makedirs(data_dir, exist_ok=True)
                print("✅ data 디렉토리 생성 완료")
            except Exception as e:
                print(f"❌ data 디렉토리 생성 실패: {e}")
                return False

        # GitHub API 기본 설정
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        api_base = f'https://api.github.com/repos/{github_user}/{github_repo}/contents'

        timestamp = get_kst_time().strftime('%Y-%m-%d %H:%M:%S')
        commit_message = f"Update trading data - {timestamp}"

        print(f"📋 처리할 디렉토리: {data_dir}")
        print(f"📋 커밋 메시지: {commit_message}")

        # data 디렉토리의 모든 파일 처리
        files_list = os.listdir(data_dir)
        print(f"📋 발견된 파일 수: {len(files_list)}")

        if not files_list:
            print("⚠️  처리할 파일이 없습니다")
            return True

        files_updated = 0
        for filename in files_list:
            file_path = os.path.join(data_dir, filename)

            # 파일이 아니면 스킵
            if not os.path.isfile(file_path):
                print(f"⏭️  {filename}: 폴더이므로 스킵")
                continue

            print(f"\n📁 처리 중: {filename}")

            try:
                # 파일 내용 읽기
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                print(f"   ✅ 파일 읽기 완료 ({len(file_content)} bytes)")

                # Base64 인코딩
                file_content_b64 = base64.b64encode(file_content.encode()).decode()

                # GitHub API 엔드포인트
                file_api_url = f'{api_base}/data/{filename}'
                print(f"   📍 API URL: {file_api_url}")

                # 파일이 이미 존재하는지 확인
                print(f"   🔍 파일 존재 여부 확인 중...")
                check_response = requests.get(file_api_url, headers=headers, timeout=10)
                print(f"   ℹ️  Check 응답 코드: {check_response.status_code}")

                if check_response.status_code == 200:
                    # 파일이 존재하는 경우 - 업데이트
                    print(f"   📝 파일 존재함 - 업데이트 시도")
                    current_sha = check_response.json()['sha']
                    print(f"   ℹ️  현재 SHA: {current_sha[:10]}...")

                    # 내용이 변경되지 않았으면 스킵
                    remote_content = check_response.json().get('content', '')
                    if remote_content == file_content_b64:
                        print(f"   ⏭️  {filename}: 변경사항 없음")
                        continue

                    update_data = {
                        'message': commit_message,
                        'content': file_content_b64,
                        'sha': current_sha
                    }
                    print(f"   🔄 PUT 요청 전송 중...")
                    response = requests.put(file_api_url, json=update_data, headers=headers, timeout=10)
                    print(f"   ℹ️  응답 코드: {response.status_code}")

                else:
                    # 파일이 존재하지 않는 경우 - 생성
                    print(f"   ✨ 파일 없음 - 새로 생성")
                    create_data = {
                        'message': commit_message,
                        'content': file_content_b64
                    }
                    print(f"   🔄 PUT 요청 전송 중...")
                    response = requests.put(file_api_url, json=create_data, headers=headers, timeout=10)
                    print(f"   ℹ️  응답 코드: {response.status_code}")

                # 응답 확인
                if response.status_code in [200, 201]:
                    print(f"✅ {filename}: GitHub에 업로드됨")
                    files_updated += 1
                else:
                    print(f"❌ {filename}: 업로드 실패 - {response.status_code}")
                    print(f"   응답: {response.text[:200]}")

            except requests.exceptions.Timeout:
                print(f"❌ {filename}: 요청 타임아웃")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"❌ {filename}: 연결 실패 - {e}")
                continue
            except Exception as e:
                print(f"❌ {filename} 처리 중 오류: {type(e).__name__}: {e}")
                continue

        # 결과 출력
        print("\n" + "="*50)
        if files_updated > 0:
            print(f"✅ GitHub에 {files_updated}개 파일을 성공적으로 업로드했습니다")
            print(f"   시간: {timestamp}")
            return True
        else:
            print(f"⚠️  업로드할 변경된 데이터가 없습니다")
            print(f"   시간: {timestamp}")
            return True

    except Exception as e:
        print(f"\n❌ GitHub 업로드 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def trading_job():
    """거래 작업을 실행하고 GitHub에 데이터를 업로드합니다"""
    try:
        kst_time = get_kst_time()
        print("\n" + "="*50)
        print(f"거래 작업 시작: {kst_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)

        # 거래 봇 실행
        trading_bot.main()

        # 데이터 파일이 작성될 때까지 대기
        time.sleep(2)

        # GitHub에 데이터 푸시
        push_to_github()

        kst_time_end = get_kst_time()
        print("\n" + "="*50)
        print(f"거래 작업 완료: {kst_time_end.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)

    except Exception as e:
        print(f"\n❌ 거래 작업 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

# 스케줄러 설정
scheduler = BackgroundScheduler()

# 15:45 KST에 거래 실행 (timezone 없이, UTC 시간 변환)
# 15:45 KST = 06:45 UTC
scheduler.add_job(
    trading_job,
    'cron',
    hour=6,
    minute=45,
    id='daily_trading_job'
)

# 스케줄러 시작
if __name__ == "__main__":
    print("📊 KIS 거래 봇 스케줄러 시작...")
    scheduler.start()
    try:
        # 스케줄러를 계속 실행 상태로 유지
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n스케줄러 종료 중...")
        scheduler.shutdown()
        print("스케줄러 종료 완료")