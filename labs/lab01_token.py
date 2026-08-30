"""lab01 — 접근 토큰 (참고용 데모).

토큰 발급 '실습'은 노트북 FD-14-900(trading-practice) 첫 셀로 이관되었다.
이 파일은 "토큰을 어떻게 손에 쥐는가"를 보여 주는 참고용 데모다.

핵심: 실제 코드에서는 항상 get_token()을 쓴다.
- get_token()은 발급된 토큰을 mode별·만료시각으로 캐시에 저장해 재사용한다.
- 그래서 셀을 여러 번 돌리거나 노트북과 같이 실행해도 재발급하지 않는다
  (KIS 1분당 1회 발급 제한 EGW00133을 자동으로 피한다).
- 발급의 내부 원리(원시 요청의 생김새)는 FD-14-300 노트와 노트북 첫 셀에서 다룬다.

실행:  uv run python labs/lab01_token.py
"""

import sys
from pathlib import Path

# 레포 루트를 import 경로에 추가 (src 패키지 사용을 위해)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.kis_client import get_base_url, get_mode, get_token, load_env


def main() -> None:
    load_env()
    mode = get_mode()
    print(f"🔑 토큰 확보 (mode={mode}, base={get_base_url(mode)})")

    # 항상 get_token() — 캐시에 유효한 토큰이 있으면 재사용, 없으면 1회만 발급
    try:
        token = get_token()
    except RuntimeError as exc:
        print(f"⚠️  {exc}")
        print("   .env에 모의 APP_KEY/SECRET을 채운 뒤 다시 실행하세요.")
        raise SystemExit(0)

    masked = f"{token[:6]}...{token[-4:]}" if len(token) > 12 else "***"
    print("✅ 토큰 준비 완료 (캐시 재사용 또는 신규 발급)")
    print(f"   access_token: {masked} (length={len(token)})")


if __name__ == "__main__":
    main()
