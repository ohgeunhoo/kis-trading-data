from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import trading_bot
import time

def schedule_trading():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=trading_bot.main,
        trigger="cron",
        hour=15,
        minute=45,
        timezone='Asia/Seoul',
        id='daily_trading'
    )
    scheduler.start()
    print(f"\n{'='*50}")
    print(f"🕐 자동 거래 스케줄러 시작!")
    print(f"⏰ 매일 15:45 KST에 자동 실행")
    print(f"시작 시간: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n스케줄러 중지됨")
        scheduler.shutdown()

if __name__ == "__main__":
    schedule_trading()