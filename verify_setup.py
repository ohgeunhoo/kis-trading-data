"""KIS 개발 환경 검증 스크립트.

실행:  uv run verify_setup.py
"""

import os
import sys
from pathlib import Path


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


if Path(".env").exists():
    load_env()

checks = {
    "Python 3.12+": sys.version_info >= (3, 12),
    ".env 존재": Path(".env").exists(),
    "MOCK_APP_KEY 설정": bool(os.getenv("KIS_MOCK_APP_KEY", "").strip()),
    "MOCK_ACCOUNT 설정": bool(os.getenv("KIS_MOCK_ACCOUNT_NUMBER", "").strip()),
    "labs/ 디렉토리": Path("labs").is_dir(),
    "lab04_backtest_demo.py": Path("labs/lab04_backtest_demo.py").is_file(),
    "005930_daily.csv": Path("labs/data/005930_daily.csv").is_file(),
}
for pkg in ["requests", "dotenv", "pandas", "rich"]:
    try:
        __import__(pkg)
        checks[f"{pkg} 설치"] = True
    except ImportError:
        checks[f"{pkg} 설치"] = False

print("\n=== KIS 개발 환경 검증 ===\n")
for name, ok in checks.items():
    print(f"{'✅' if ok else '❌'} {name}")
passed = sum(checks.values())
print(f"\n{passed}/{len(checks)} 통과")

# .mcp.json은 lab04(백테스트) 단계에서 설정 — 지금은 불필요
print("\nℹ️  .mcp.json은 lab04(백테스트) 단계에서 설정합니다 (lab01~03은 불필요).")

if passed == len(checks):
    print("🎉 완료! lab01부터 시작하세요.")
else:
    print("⚠️  ❌ 항목을 해결 후 재실행하세요.")
    sys.exit(1)
