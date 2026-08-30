# kis-lab — AI 코딩 에이전트 셋업 & 실습 가이드

> 이 파일은 **AI 코딩 에이전트(GitHub Copilot · Claude Code · Codex · Gemini CLI 등)** 가 자동으로 읽는 워크스페이스 지시사항입니다.
> 동일한 내용이 `AGENTS.md` · `CLAUDE.md` · `.github/copilot-instructions.md` 세 곳에 들어 있어, 어떤 에이전트를 쓰든 "setup" 한마디로 동일하게 스캐폴딩됩니다.
> 학생이 "setup" 또는 "설치해줘"라고 하면 아래 Phase를 **직접 실행**합니다 — 안내만 하지 말고 터미널 명령을 직접 실행하세요.

---

## ⚠️ 사람이 직접 해야 하는 것 (1번, 선택 1번)

| 순서 | 할 일 | 소요 시간 |
|------|-------|-----------|
| Phase 3 완료 후 | `.env` 파일에 APP Key 입력 | 약 2분 |
| Phase 5(선택) 완료 후 | Docker Desktop 실행 → 약관 동의 버튼 클릭 | Lean 고급 트랙 최초 1회 |

**코어 lab02~lab04는 Docker 없이 완료됩니다.**

---

## 트리거 목록

| 학생 입력 | 동작 |
|-----------|------|
| `setup` / `설치해줘` | Phase 0~4 실행 후 Phase 6 코어 검증 (Docker 제외) |
| `lab02` / `현재가` | lab02_price.py TODO 채워주고 실행 |
| `lab03` / `주문` | lab03_order.py — 기본은 잔고조회만 실행. 주문 코드는 작성하되 모의(mock)·교수 안내 후에만 제출(⚠️ 검증 대기) |
| `lab04` / `백테스팅` | `labs/lab04_backtest_demo.py` 실행 — 수업 본편: sample strategy 아이디어 → 백테스트 → 모의주문 본문 연결 (Docker 불필요, 오프라인-세이프). Lean/Docker 환경은 Phase 8(선택). |
| `검증` / `확인해줘` | verify_setup.py 실행하여 환경 점검 |
| `오류 해결해줘` | 에러 메시지 분석 후 자동 수정 시도 |
| `MCP 연결해줘` | Phase 7 실행 — KIS 코드 도우미 MCP 연결 (키 불필요) |
| `백테스트 환경 만들어줘` | Phase 8 실행 — Docker/Lean 백테스터 준비 |

---

## Phase 0: OS 감지 (자동 실행)

아래 명령을 **직접 실행**하여 OS를 판별한다:

```bash
python3 -c "import platform; print(platform.system(), platform.machine())" 2>/dev/null \
  || python -c "import platform; print(platform.system(), platform.machine())"
```

- `Windows` 출력 → 이후 모든 명령을 **PowerShell** 기준으로 실행
- `Darwin` 출력 → 이후 모든 명령을 **bash (Mac)** 기준으로 실행
- `Linux` 출력 → 이후 모든 명령을 **bash (Linux)** 기준으로 실행

판별한 OS를 학생에게 알리고 Phase 1로 즉시 진행.

---

## Phase 1: uv 설치 (자동 실행)

먼저 설치 여부 확인:

```bash
uv --version
```

이미 있으면 → Phase 2로 즉시 이동.

없으면 OS에 맞게 **직접 실행**:

**Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
uv --version
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv --version
```

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version
```

`uv --version`이 출력되면 → Phase 2로 즉시 이동.
실패 시 → 오류 메시지를 보여주고 "터미널을 재시작한 뒤 다시 `setup`을 입력하세요" 안내.

---

## Phase 2: Python 3.12 + 패키지 설치 (자동 실행)

아래를 **순서대로 직접 실행**:

```bash
uv python install 3.12
```

`pyproject.toml`이 없으면 생성:
```bash
uv init --python 3.12 --no-readme .
```

패키지 설치:
```bash
uv add requests python-dotenv websocket-client pandas rich jupyterlab ipykernel
```

확인:
```bash
uv run python --version
```

`Python 3.12.x`가 출력되면 → Phase 3으로 즉시 이동.

---

## Phase 3: .env 파일 생성 (자동 실행 후 ✋ 한 번 개입)

**Mac/Linux:**
```bash
[ ! -f .env ] && cp .env.sample .env && echo ".env 생성 완료"
```

**Windows:**
```powershell
if (-not (Test-Path .env)) { Copy-Item .env.sample .env; Write-Host ".env 생성 완료" }
```

`.gitignore`에 `.env` 추가 (없으면):

**Mac/Linux:**
```bash
grep -qxF '.env' .gitignore 2>/dev/null || echo '.env' >> .gitignore
```

**Windows:**
```powershell
if (-not (Select-String -Path .gitignore -Pattern '^\.env$' -Quiet 2>$null)) {
  Add-Content .gitignore '.env'
}
```

생성 후 → **아래 안내를 출력하고 대기**:

```
✋ [사람이 할 일 1/2] — 약 2분

VS Code에서 .env 파일을 열고 아래 4개 항목을 채워주세요:

  KIS_MOCK_APP_KEY=             ← KIS Developers에서 발급받은 모의 APP Key
  KIS_MOCK_APP_SECRET=          ← 모의 APP Secret
  KIS_MOCK_ACCOUNT_NUMBER=      ← 모의 종합계좌번호 (8자리, 예: 50123456)
  KIS_MOCK_ACCOUNT_PASSWORD=    ← 모의 계좌 비밀번호

아래 두 줄은 이미 입력되어 있으니 건드리지 마세요:

  KIS_MODE=mock                 ← 이미 입력됨, 수정 불필요
  KIS_ACCOUNT_PRODUCT_CODE=01   ← 이미 입력됨, 수정 불필요

📌 계좌번호는 8자리 종합계좌번호(CANO)만 입력합니다.
   상품코드는 KIS_ACCOUNT_PRODUCT_CODE에 별도로 들어가며 기본값 "01"입니다.
   KIS_MODE=mock 과 KIS_ACCOUNT_PRODUCT_CODE=01 은 이미 입력되어 있음, 수정 불필요.

📌 APP Key 발급: https://apiportal.koreainvestment.com

입력이 완료되면 "계속해줘"라고 입력하세요.
```

"계속해줘" 입력 받으면 → Phase 4로 이동.

---

## Phase 4: .env 유효성 자동 확인 (자동 실행)

아래 검증 스크립트를 **직접 실행**:

```bash
uv run python - << 'EOF'
import os
from pathlib import Path

def load_env():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env()

key   = os.getenv("KIS_MOCK_APP_KEY", "")
secret = os.getenv("KIS_MOCK_APP_SECRET", "")
acct  = os.getenv("KIS_MOCK_ACCOUNT_NUMBER", "")
pw    = os.getenv("KIS_MOCK_ACCOUNT_PASSWORD", "")

ok = all([key, secret, acct, pw]) and "입력" not in key
print("✅ APP Key 설정 완료" if ok else "❌ .env 설정 미완료 — 값을 다시 확인하세요")
EOF
```

`❌`가 나오면 → ".env 파일의 해당 항목이 비어있습니다. 다시 채워주세요" 안내 후 대기.
`✅`가 나오면 → Phase 6으로 즉시 이동. Docker는 코어 setup에 필요하지 않다.

---

## Phase 5: 선택/고급 Docker 설치 (Lean 백테스터용)

> 학생이 `백테스트 환경 만들어줘`라고 했거나 Phase 8을 진행할 때만 실행합니다.
> `setup` / `설치해줘` 기본 경로에서는 이 Phase를 건너뜁니다.

> 📖 Mac(Intel/Apple Silicon)·Windows(WSL2) 상세 설치 절차는
> `lecture/Week14/notes/FD-14-500__docker-install.md`를 참고하세요.

먼저 설치 여부 확인:

```bash
docker --version
```

이미 있으면 Docker 실행 상태 확인:

```bash
docker ps
```

`CONTAINER ID`가 출력되면 → Phase 8 준비 완료.

### Docker 미설치 시 — OS별 자동 설치

**Mac (Homebrew 이용):**
```bash
# Homebrew 없으면 먼저 설치
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install --cask docker-desktop
```

**Windows (winget 이용 — Windows 10/11 기본 탑재):**
```powershell
# ① Docker보다 먼저 WSL 2 준비 (관리자 PowerShell에서) → 입력 후 재부팅
wsl --install        # 이미 있으면: wsl --update   (Docker는 WSL 2.1.5+ 필요)
# ② 그 다음 Docker Desktop 설치
winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements
```
> 이 강의는 WSL 2 기반 **Linux 컨테이너** 경로를 사용합니다. Windows Home 학생도 이 경로로 안내하되, Windows 컨테이너 기능과는 구분하세요. BIOS 가상화가 꺼져 있으면 엔진이 안 켜집니다.

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable --now docker
docker --version
```

Linux는 재로그인 없이 즉시 사용 가능 여부 확인:
```bash
docker ps 2>/dev/null || echo "재로그인 필요"
```

### Mac/Windows 설치 후 — ✋ 개입 필요

```
✋ [선택 단계 사람이 할 일] — Lean 고급 트랙 최초 1회만

Docker Desktop이 설치되었습니다.
아래를 진행해주세요:

  1. 바탕화면 또는 응용프로그램에서 Docker Desktop 실행
  2. 약관 동의 화면에서 "Accept" 클릭
  3. 상단 메뉴바(Mac) 또는 트레이(Windows)에
     고래 아이콘 🐋 이 나타나면 완료

준비되면 "계속해줘"라고 입력하세요.
```

"계속해줘" 입력 받으면 Docker 실행 확인:

```bash
docker ps
```

성공이면 → Phase 8 준비 완료.
실패이면 → "Docker Desktop이 실행 중인지 확인하세요 (고래 아이콘이 트레이에 있어야 합니다)" 안내.

---

## Phase 6: 코어 최종 검증 (자동 실행, Docker 제외)

아래 검증 스크립트를 **직접 실행**:

```bash
uv run python - << 'EOF'
import sys, os, subprocess
from pathlib import Path

def load_env():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

if Path(".env").exists():
    load_env()

checks = {}
checks["Python 3.12+"] = sys.version_info >= (3, 12)
checks[".env 존재"] = Path(".env").exists()
checks["APP_KEY 설정"] = bool(os.getenv("KIS_MOCK_APP_KEY","").strip())
checks["APP_SECRET 설정"] = bool(os.getenv("KIS_MOCK_APP_SECRET","").strip())
checks["계좌번호 설정"] = bool(os.getenv("KIS_MOCK_ACCOUNT_NUMBER","").strip())
checks["계좌비밀번호 설정"] = bool(os.getenv("KIS_MOCK_ACCOUNT_PASSWORD","").strip())
checks["labs/ 존재"] = Path("labs").is_dir()

for pkg in ["requests", "dotenv", "pandas", "rich", "jupyterlab", "ipykernel"]:
    try:
        __import__(pkg)
        checks[f"{pkg} 설치"] = True
    except ImportError:
        checks[f"{pkg} 설치"] = False

print("\n=== 환경 검증 결과 ===\n")
for name, ok in checks.items():
    print(f"{'✅' if ok else '❌'} {name}")

passed = sum(checks.values())
total = len(checks)
print(f"\n{passed}/{total} 통과")

if passed == total:
    print("\n🎉 설치 완료! 아래 명령으로 첫 번째 실습을 시작하세요:")
    print("  uv run python labs/lab02_price.py")
else:
    failed = [n for n, ok in checks.items() if not ok]
    print(f"\n⚠️  미완료 항목: {', '.join(failed)}")
    print("'오류 해결해줘'라고 입력하면 자동으로 해결을 시도합니다.")
EOF
```

모두 ✅이면 → 설치 완료 축하 메시지 출력.
❌가 있으면 → 해당 항목 자동 수정 시도 후 재검증.

> Phase 0~4와 Phase 6까지 끝나면 lab02~lab04 코어 실습이 모두 가능합니다.
> lab02~03은 API 연결 확인, lab04는 sample strategy 백테스팅 수업 본편입니다. (토큰 발급은 get_token()이 자동 처리)
> 아래 Phase 5·7·8은 **선택/심화 단계**(Docker/Lean + 자동매매 코딩 도우미)로, 필요할 때 진행하면 됩니다.

---

## Phase 7: KIS MCP 연결 (자동매매 코딩 도우미)

> 학생이 `MCP 연결해줘`라고 하면 이 Phase를 **직접 실행**합니다.

### 학생용 빠른 시작

**MCP(Model Context Protocol)**는 AI 코딩 에이전트에게 "KIS 전용 도우미"를 붙여 주는 기능입니다.
여기서 연결하는 **KIS Code Assistant MCP**는 한국투자증권 공식 코드·문서를 검색해서
AI가 더 정확한 KIS 코드를 짜도록 돕는 **안전한 도우미**입니다.
**주문을 넣거나 돈을 움직이지 않으며, KIS 키(APP Key)도 전혀 필요 없습니다** —
그냥 연결만 하면 바로 쓸 수 있습니다. 부담 없이 진행하세요.

### 자동 실행 절차 (에이전트가 따라야 할 순서)

> 학생이 `MCP 연결해줘`라고 하면 에이전트는 아래 0~6 단계를 **사람 개입 없이 순서대로 직접 실행**합니다.
> 단계마다 1~2줄로 결과를 보고하고, 실패하면 학생에게 `오류 해결해줘`를 안내하세요.
> 학생은 트리거 한 마디만 칩니다 — 절대경로 캡처, 설정 파일 작성, 검증까지 에이전트가 합니다. (클론 위치만 에이전트가 기본값을 제안하고 학생이 한 번 확인합니다.)

**0. 사전 도구 확인 — uv·git**

uv 확인:
```bash
uv --version
```
출력이 없으면 → **Phase 1을 먼저 실행**해 uv를 설치하고 돌아옵니다.

git 확인 (생초보 머신엔 git이 없는 경우가 흔합니다):

**Mac:**
```bash
git --version || xcode-select --install   # Xcode Command Line Tools에 git 포함
```

**Windows (PowerShell):**
```powershell
git --version
# 없으면:
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
```

**Linux:**
```bash
git --version || (sudo apt-get update && sudo apt-get install -y git)
```

**1. 클론 위치 자동 결정 — kis-lab의 형제(sibling) 폴더**

`pwd`로 본 현재 폴더가 kis-lab입니다. open-trading-api는 **kis-lab과 같은 부모 폴더 아래 나란히** 둡니다 (학생이 ~/Projects 같은 폴더를 미리 만들 필요 없음).

**Mac/Linux:**
```bash
CLONE_PARENT="$(dirname "$(pwd)")"
CLONE_DIR="$CLONE_PARENT/open-trading-api"
echo "클론 위치: $CLONE_DIR"
```

**Windows (PowerShell):**
```powershell
$CloneParent = Split-Path -Parent (Get-Location)
$CloneDir = Join-Path $CloneParent 'open-trading-api'
Write-Host "클론 위치: $CloneDir"
```

> **WSL 학생**: kis-lab도 WSL 안에서 작업해야 경로 해석이 깨지지 않습니다. Windows 쪽 폴더에 kis-lab을 두고 WSL에서 클론하면 절대경로가 어긋납니다.

위 명령을 실행한 뒤 → **아래 안내를 출력하고 대기**:

```
✋ [학생 확인] — 클론 위치

open-trading-api를 아래 위치에 받겠습니다:
  <계산된 $CLONE_DIR 값>

이대로 좋으면 "계속해줘", 다른 위치를 원하면 그 경로를 알려주세요.
```

"계속해줘" 입력 시 → 계산된 `$CLONE_DIR`을 그대로 사용해 Step 2로 진행.
다른 경로 입력 시 → 학생이 입력한 경로를 `$CLONE_DIR`(`$CloneDir`)로 대체한 뒤 Step 2로 진행.

**2. 레포 클론 + uv sync (이미 있으면 건너뜀)**

폴더 이름 `MCP/KIS Code Assistant MCP`에는 **공백**이 있으므로 이후 args 배열에서도 **하나의 항목**으로 유지하세요(쪼개지 마세요).

**Mac/Linux:**
```bash
[ -d "$CLONE_DIR" ] || git clone https://github.com/koreainvestment/open-trading-api.git "$CLONE_DIR"
( cd "$CLONE_DIR" && uv sync )
( cd "$CLONE_DIR/MCP/KIS Code Assistant MCP" && uv sync )
```

**Windows (PowerShell):**
```powershell
if (-not (Test-Path $CloneDir)) {
  git clone https://github.com/koreainvestment/open-trading-api.git $CloneDir
}
Push-Location $CloneDir; uv sync; Pop-Location
Push-Location (Join-Path $CloneDir 'MCP\KIS Code Assistant MCP'); uv sync; Pop-Location
```

(선택) 서버가 실제로 뜨는지 health check:

**Mac/Linux:**
```bash
( cd "$CLONE_DIR/MCP/KIS Code Assistant MCP" && PORT=8081 uv run server.py ) &
sleep 2 && curl -s http://localhost:8081/health ; kill %1
```
→ `{"status":"healthy", ...}` 출력 시 정상.

**3. 에이전트별 설정 파일 작성 — 자기 정체에 맞는 한 파일만 쓰세요**

학생 다수는 **VS Code GitHub Copilot**을 씁니다 → 기본 경로는 그 파일입니다. 당신이 Claude Code/Codex로 실행 중이면 해당 파일로 대신 쓰세요. **`<ABS_CLONE>` 자리에는 1단계에서 캡처한 절대경로(`$CLONE_DIR`/`$CloneDir`)를 그대로 박아 넣어** 학생이 손댈 일이 없게 만듭니다.

| 에이전트 | 작성 파일 (kis-lab 루트 기준) | 최상위 키 |
|----------|-------------------------------|-----------|
| **VS Code Copilot (기본)** | `.vscode/mcp.json` | `servers.kis-code-assistant` |
| Claude Code | `.mcp.json` | `mcpServers.kis-code-assistant` |
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.kis-code-assistant]` |
| Gemini CLI | `~/.gemini/settings.json` | `mcpServers.kis-code-assistant` |

**VS Code Copilot — `.vscode/mcp.json` (기본):**
```json
{
  "servers": {
    "kis-code-assistant": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "<ABS_CLONE>/MCP/KIS Code Assistant MCP", "run", "server.py", "--stdio"]
    }
  }
}
```

**Claude Code — `.mcp.json`:**
```json
{
  "mcpServers": {
    "kis-code-assistant": {
      "command": "uv",
      "args": ["--directory", "<ABS_CLONE>/MCP/KIS Code Assistant MCP", "run", "server.py", "--stdio"]
    }
  }
}
```

**Codex CLI — `~/.codex/config.toml`:**
```toml
[mcp_servers.kis-code-assistant]
command = "uv"
args = ["--directory", "<ABS_CLONE>/MCP/KIS Code Assistant MCP", "run", "server.py", "--stdio"]
```

**Gemini CLI — `~/.gemini/settings.json`:**
```json
{
  "mcpServers": {
    "kis-code-assistant": {
      "command": "uv",
      "args": ["--directory", "<ABS_CLONE>/MCP/KIS Code Assistant MCP", "run", "server.py", "--stdio"]
    }
  }
}
```

> Windows에서 `uv`가 인식되지 않으면 `where uv`로 전체 경로를 찾아 `"command"` 자리에 그 절대경로를 넣으세요.

**4. .gitignore 보호 (필수)**

kis-lab 루트의 `.gitignore`에 다음 두 줄이 없으면 추가합니다 — 설정 파일에 학생 머신의 절대경로가 들어가 있어 그대로 커밋되면 다른 환경에서 깨집니다:

```
.mcp.json
.vscode/mcp.json
```

**5. 검증 — 에이전트별 자동 실행**

**VS Code Copilot (기본):**
- `.vscode/mcp.json` 작성 후 **VS Code를 완전히 종료하고 다시 엽니다**(창 새로고침 ❌, 종료 후 재실행 ✅).
- 재실행되면 Copilot Chat 도구 패널에 `kis-code-assistant`가 보여야 정상.

**Claude Code:**
```bash
claude mcp list
```
→ `kis-code-assistant: ... - ✓ Connected` 줄이 있으면 통과. 이미 켜진 세션이면 Claude Code를 한 번 재시작해야 도구가 로드됩니다.
project `.mcp.json`은 첫 로드 시 "이 MCP 서버를 신뢰하시겠습니까?" 승인 창이 뜹니다 — 승인해야 도구가 로드됩니다(이미 실행 중이면 재시작).

**Codex CLI:**
```bash
codex mcp list
```
→ `kis-code-assistant`가 표시되면 통과.

**Gemini CLI:**
`gemini`를 재시작한 뒤 `/mcp` 를 입력하면 목록에 `kis-code-assistant`가 보이면 통과.

**6. 실제 도구 호출 확인 (실연)**

학생에게 다음 질문을 직접 던지게 하고 응답을 확인합니다:

> **"kis-code-assistant MCP로 현재가 조회 API의 tr_id를 검색해줘. 어느 MCP 도구를 호출했는지 출처도 같이."**

- ✅ 정상: 응답에 `search_domestic_stock_api` 같은 **도구 호출 흔적**이 보이고, `FHKST01010100`이 함께 나옴.
- ⚠️ 실패: `FHKST01010100`만 답하고 도구 호출 흔적이 없으면 MCP가 실제로 안 붙은 상태 — 학생 일반 지식이나 로컬 문서로 답한 것입니다. 5단계 검증부터 다시 점검.

### 두 개의 키 파일 — 헷갈리지 마세요 (.env vs kis_devlp.yaml)

| 파일 | 위치 | 누가 읽나 | 언제 필요 |
|------|------|-----------|-----------|
| `.env` | kis-lab 폴더 | lab02~lab03 (`src/kis_client.py`) | Phase 3에서 이미 작성 |
| `kis_devlp.yaml` | `~/KIS/config/kis_devlp.yaml` | open-trading-api의 MCP·백테스터 | Phase 8(백테스트)에서 작성 |

- **같은 KIS 계좌**를 쓰지만 **파일이 다릅니다.** 한쪽에 넣었다고 다른 쪽에 자동 반영되지 않습니다.
- 모의(mock)는 `kis_devlp.yaml`의 `paper_app`·`paper_sec`·`my_paper_stock`(+ `my_htsid`)을 채우고
  서버 구분은 `vps`(모의)로 사용합니다.
- **이번 Phase 7의 코드 도우미 MCP는 키가 전혀 필요 없습니다** — `kis_devlp.yaml` 작성은 Phase 8에서 합니다.

### (심화) KIS Trading MCP — 기본값 아님 ⚠️

- 자연어로 **실제 주문을 넣는** "KIS Trading MCP"도 공식 레포에 들어 있습니다.
- ⚠️ **실제 매매가 발생**할 수 있으므로 강의 기본 경로에서는 **연결하지 않습니다.**
  나중에 쓰더라도 반드시 **모의(mock) 전용 + 교수 안내 + 주문 전 확인**을 거치세요.
- 지금 단계에서 연결할 도우미는 **Step 1~3의 코드 도우미(KIS Code Assistant) 하나뿐**입니다.

---

## Phase 8: 선택/고급 — 더 정교한 슬리피지·체결 모델 (Lean, Docker)

> 학생이 `백테스트 환경 만들어줘`라고 하면 이 Phase를 **직접 실행**합니다.
> Docker가 필요합니다 — 아직 안 깔았으면 먼저 Phase 5를 끝내고 Docker Desktop을 실행해 두세요.

> 📌 **코어 Week14는 Docker 없이 완주합니다.** `labs/lab04_backtest_demo.py`를 실행하면
> 백테스트→모의주문 간극 비교 데모가 오프라인에서도 동작합니다(`uv run python labs/lab04_backtest_demo.py`).
> Phase 8은 그 위의 **선택 확장** — Lean 엔진으로 더 정교한 슬리피지·체결 모델을 쓰고 싶을 때 진행합니다.

### 백테스팅이 뭔가요

**백테스팅**은 내가 만든 매매 전략을 **과거 데이터로 미리 돌려 보는** 것입니다.
한국투자증권 공식 레포는 **QuantConnect Lean**이라는 백테스트 엔진을 Docker로 제공합니다.
전략을 고르거나 직접 만든 뒤(`.kis.yaml`) 실행하면, 수익률·지표·HTML 리포트를 받아볼 수 있습니다.

### Step 1 — 백테스터 실행

Phase 7에서 클론한 **open-trading-api 폴더**를 그대로 사용합니다.

**Mac/Linux:**
```bash
cd <클론_절대경로>/backtester     # 예: ~/Projects/open-trading-api/backtester
./start.sh
```

**Windows:** `start.sh`는 Unix 전용 도구(`lsof`·`kill`·`trap`)를 쓰기 때문에 PowerShell이나 Git Bash에서는 잘 안 됩니다.
**WSL(Ubuntu)에서 실행**하세요:

1. WSL Ubuntu 설치/실행 (PowerShell 관리자 권한에서 `wsl --install -d Ubuntu` → 재부팅 → Ubuntu 실행)
2. **레포를 WSL 안에서 다시 클론**합니다 (Windows 쪽 폴더 말고 WSL 홈에서):
   ```bash
   cd ~ && git clone https://github.com/koreainvestment/open-trading-api.git
   cd open-trading-api && uv sync
   ```
3. 백테스터 실행:
   ```bash
   cd ~/open-trading-api/backtester
   ./start.sh
   ```

> `bash: ... 인식되지 않습니다` 또는 `lsof: command not found`가 나오면 PowerShell/Git Bash가 아니라 **WSL Ubuntu**에서 진행하세요.

- `start.sh`는 백엔드(`:8002`)와 프론트엔드(`:3001`)를 함께 띄웁니다.
- **최초 1회**에는 `scripts/setup_lean_data.sh`가 자동으로 돌면서
  **`quantconnect/lean` Docker 이미지를 받습니다 (약 2~5GB, 수 분 소요)** — 처음엔 시간이 좀 걸립니다.
- 함께 장시간 한국거래소(KRX) 종목 마스터·시장시간 데이터도 내려받습니다.
- 프론트엔드 설치를 위해 **Node.js 18+** 가 필요합니다. `node -v`로 확인하고, 없으면 설치하세요:
  - Mac: `brew install node`
  - Windows: `winget install OpenJS.NodeJS.LTS` (WSL이면 WSL Ubuntu 안에서 설치)
  - 또는 https://nodejs.org 에서 LTS 버전 다운로드

### Step 1.5 — 백테스트 데이터 중복키 정리 (⚠️ 최초 1회 · Mac/Linux/WSL)

`start.sh`가 자동으로 받은 한국거래소(KRX) 종목 데이터(`symbol-properties`)에는 **같은 코드가 두 번**
등장하는 항목이 있어, 그대로 두면 Lean이 `Encountered duplicate key` 오류로 **모든 백테스트가 실패**합니다.
`start.sh`로 서버가 뜬 뒤(데이터 다운로드 완료 후) **새 터미널**에서 아래를 1회 실행해 중복을 제거하세요.
(이미 깔끔하면 아무것도 바뀌지 않습니다 — 여러 번 실행해도 안전)

```bash
F="<클론_절대경로>/backtester/.lean-workspace/data/symbol-properties/symbol-properties-database.csv"
awk -F, 'NR==1{print;next} /^#/{print;next} {k=$1","$2","$3; if(!seen[k]++) print}' "$F" > "$F.tmp" && mv "$F.tmp" "$F"
```

> 백테스트가 `duplicate key`로 실패하면 이 단계를 빼먹은 것입니다 — 위 명령 실행 후 다시 시도하세요.

### Step 2 — 키 파일(kis_devlp.yaml) 준비 — ✋ 한 번 개입

백테스터가 가격 데이터를 모으려면 KIS 키가 필요합니다. **Phase 7에서 설명한 `kis_devlp.yaml`**을 사용합니다 (`.env`와는 별개 파일).

1. 키를 둘 폴더를 만듭니다:
   - Mac/Linux(WSL 포함): `mkdir -p ~/KIS/config`
   - Windows(PowerShell): `New-Item -ItemType Directory -Force ~\KIS\config`
2. 템플릿 `kis_devlp.yaml`은 **open-trading-api 레포 루트**에 들어 있습니다. 이 파일을 `~/KIS/config/`로 복사한 뒤 거기서 편집합니다:
   - Mac/Linux(WSL 포함): `cp <클론_절대경로>/kis_devlp.yaml ~/KIS/config/`
   - Windows(PowerShell): `Copy-Item <클론_절대경로>\kis_devlp.yaml ~\KIS\config\`
3. `~/KIS/config/kis_devlp.yaml`을 열어 **모의(mock) 항목만** 채웁니다:

```
✋ [사람이 할 일] — kis_devlp.yaml 모의 항목 작성

  paper_app:       ← 모의 APP Key
  paper_sec:       ← 모의 APP Secret
  my_paper_stock:  ← 모의 종합계좌번호 (8자리)
  my_htsid:        ← HTS 아이디

서버 구분은 vps(모의)를 사용합니다.
```

> 키를 채운 뒤 **백테스터(Step 3)를 실행하면 그 키로 데이터를 받아옵니다.** 별도 연결 테스트가 필요하면 교수와 함께 진행하세요.

> 📌 **강의 기본은 모의(mock)입니다.** 공식 안내에 따르면 실전(live) 키가 모의보다
> **백테스트 데이터가 더 정확**(모의는 거래량/호가에 빈틈이 있음)하지만,
> **안전을 위해 수업에서는 모의를 기본**으로 씁니다. 실전 전환은 교수 안내 후에만 하세요.

### Step 3 — 브라우저에서 백테스트 실행

1. 웹브라우저에서 **http://localhost:3001** 접속
2. 미리 준비된 **10개 프리셋 전략 중 하나를 고르거나**, 직접 만든 `.kis.yaml` 전략을 불러옵니다
3. 실행하면 수익률·지표와 함께 **HTML 리포트**가 생성됩니다

> 목표: 투자대회 전략을 재현 → `strategy_builder`로 전략을 만들고 → `.kis.yaml`로 저장 → `backtester`에서 검증.

---

## 실습 진행 — lab별 자동 실행

학생이 "lab02" 또는 "현재가 조회해줘"라고 하면:

1. `labs/lab02_price.py`를 열고 `# TODO:` 위치 파악
2. 해당 부분 코드 작성 (아래 API 정보 참조)
3. 즉시 실행:
   ```bash
   uv run python labs/lab02_price.py
   ```
4. 오류 발생 시 자동 분석 후 수정 제안

> 토큰 발급은 별도 fill-in 실습이 아니라 `src/kis_client.py`의 `get_token()`이 자동 처리한다
> (mode별·만료시각 캐시 → 재사용, EGW00133 회피). 발급 원리는 노트북 FD-14-900 첫 셀과 FD-14-300 노트 참고.

---

## KIS API 핵심 정보 (AI 에이전트 코드 생성 참조용)

### Base URL

```python
# KIS_MODE에 따라 자동 분기 (오타·미설정 시 안전하게 mock으로 폴백)
import os
MODE = os.getenv("KIS_MODE", "mock")
BASE_URL = (
    "https://openapi.koreainvestment.com:9443"
    if MODE == "live"
    else "https://openapivts.koreainvestment.com:29443"
)
APP_KEY      = os.getenv("KIS_LIVE_APP_KEY"        if MODE == "live" else "KIS_MOCK_APP_KEY")
APP_SECRET   = os.getenv("KIS_LIVE_APP_SECRET"     if MODE == "live" else "KIS_MOCK_APP_SECRET")
ACCOUNT      = os.getenv("KIS_LIVE_ACCOUNT_NUMBER" if MODE == "live" else "KIS_MOCK_ACCOUNT_NUMBER")
PRODUCT_CODE = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")
```

### 토큰 발급

```python
def get_token():
    res = requests.post(f"{BASE_URL}/oauth2/tokenP", json={
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    })
    res.raise_for_status()
    return res.json()["access_token"]
```

### 공통 헤더

```python
def headers(token, tr_id):
    return {
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
        "content-type": "application/json"
    }
```

### 주요 API 엔드포인트

| 기능 | Method | Path | tr_id (모의) | tr_id (실전) |
|------|--------|------|-------------|-------------|
| 현재가 조회 | GET | /uapi/domestic-stock/v1/quotations/inquire-price | FHKST01010100 | FHKST01010100 |
| 매수 주문 | POST | /uapi/domestic-stock/v1/trading/order-cash | VTTC0802U | TTTC0802U |
| 매도 주문 | POST | /uapi/domestic-stock/v1/trading/order-cash | VTTC0801U | TTTC0801U |
| 잔고 조회 | GET | /uapi/domestic-stock/v1/trading/inquire-balance | VTTC8434R | TTTC8434R |

### 현재가 조회 예시

```python
def get_price(token, ticker="005930"):  # 005930 = 삼성전자
    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers(token, "FHKST01010100"),
        params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": ticker}
    )
    res.raise_for_status()
    data = res.json()["output"]
    # ⚠️ inquire-price output에는 종목명(hts_kor_isnm) 필드가 없다 → 종목코드로 출력
    print(f"{ticker}: {int(data['stck_prpr']):,}원")
```

---

## 오류 자동 해결 규칙

학생이 "오류 해결해줘" 또는 에러 메시지를 붙여넣으면
아래 테이블을 참조해서 자동으로 수정 명령을 실행한다:

| 오류 | 자동 실행 |
|------|-----------|
| `ModuleNotFoundError` | `uv add <패키지명>` |
| `EGW00123` (APP Key 오류) | `.env` 파일 열어서 확인 요청 |
| `EGW00121`·`EGW00133` (토큰 만료·재발급 쿨다운) | 기존 토큰을 재사용하고, 마지막 발급 후 1분 이상 지난 뒤에만 재발급 |
| `ConnectionError` | `curl -I https://openapivts.koreainvestment.com:29443` 로 연결 테스트 |
| `.env` 관련 | `cp .env.sample .env` 재실행 |
| `uv: command not found` | Phase 1 재실행 |
| `docker: command not found` | Phase 5 재실행 |
| `Permission denied` (Linux) | `sudo usermod -aG docker $USER && newgrp docker` |

---

## 보안 규칙

1. `.env` 파일 내용을 절대 출력하거나 채팅창에 붙여넣지 않는다
2. APP Key를 코드에 직접 쓰지 않는다 (`os.getenv()` 사용)
3. `KIS_MODE=mock`이 기본값 — 실전(live) 전환은 교수 안내 후에만

---

## 참고 링크

- KIS API 포털: https://apiportal.koreainvestment.com
- 공식 샘플: https://github.com/koreainvestment/open-trading-api
- AI Extensions: https://github.com/koreainvestment/kis-ai-extensions
- uv 문서: https://docs.astral.sh/uv
