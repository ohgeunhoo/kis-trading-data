"""lab06 — KIS Code Assistant MCP를 코드에서 직접 호출해보기.

§500 강의의 실습 헬퍼. 학생은 보통 AI 에이전트(Copilot Chat·Claude Code) 채팅창으로
MCP에게 질문하지만, ==MCP 안에서 실제로 무슨 일이 벌어지는지== 한 번은 손으로 직접
보는 것이 중요하다 — "마법 박스"가 아니라 ==검색 엔진 + 코드 fetcher==라는 사실을
체감해야 응답을 비판적으로 읽을 수 있다.

이 lab은 두 함수를 제공한다:
  search(category, **kwargs) — kis-code-assistant MCP의 search_<category>_api 도구를
                                stdio JSON-RPC로 호출. 검색 결과(함수명·url_main 등)
                                메타데이터를 파이썬 dict로 돌려준다.
  read_source(url_main)      — search 결과의 url_main URL에서 실제 GitHub 코드를
                                가져온다. ==그 코드 안에 tr_id가 있다.==

전형적인 흐름 (= AI 에이전트가 채팅 뒤에서 하는 일):
  1) hits = search("domestic_stock", subcategory="기본시세", function_name="inquire_price")
  2) url  = hits["results"][0]["url_main"]
  3) code = read_source(url)        # tr_id 가 이 안에 있다

⚠️ 안전·전제 조건:
  - KIS Code Assistant MCP 는 ==키 불필요·주문 없음== — 그냥 검색·코드 조회 도우미다.
  - open-trading-api 클론이 sibling 위치(kis-lab 부모 폴더)에 있어야 한다.
    먼저 Phase 7(`MCP 연결해줘`)을 끝낸 상태를 가정한다.
  - 환경변수 OPEN_TRADING_API 로 다른 클론 경로 지정 가능.
  - search 는 오프라인 동작(서버 내장 data.csv 검색). read_source 는 GitHub raw fetch
    이므로 인터넷이 필요하고, 끊겨 있으면 깔끔하게 에러 메시지로 끝난다.

실행:  uv run python labs/lab06_mcp_query.py     (Phase 7 완료 후)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# ---- 클론 위치 자동 해석 (sibling 기본 + 환경변수 override) ------------------
_SIBLING = Path(__file__).resolve().parent.parent.parent / "open-trading-api"
CLONE = Path(os.environ.get("OPEN_TRADING_API", str(_SIBLING)))
MCP_DIR = CLONE / "MCP" / "KIS Code Assistant MCP"

# 카테고리 → MCP 도구 이름 매핑 (server.py의 @mcp.tool 등록과 1:1)
CATEGORY_TO_TOOL = {
    "auth": "search_auth_api",
    "domestic_stock": "search_domestic_stock_api",
    "domestic_bond": "search_domestic_bond_api",
    "domestic_futureoption": "search_domestic_futureoption_api",
    "overseas_stock": "search_overseas_stock_api",
    "overseas_futureoption": "search_overseas_futureoption_api",
    "elw": "search_elw_api",
    "etfetn": "search_etfetn_api",
}


def _ensure_setup() -> None:
    if not MCP_DIR.exists():
        print(
            "❌ open-trading-api 클론을 찾을 수 없습니다.\n"
            f"   예상 위치: {MCP_DIR}\n"
            "   먼저 'MCP 연결해줘' (Phase 7) 을 실행해 클론·uv sync 부터 끝내세요.\n"
            "   (다른 위치에 클론했다면 환경변수 OPEN_TRADING_API 로 경로 지정)"
        )
        sys.exit(1)


async def _rpc_session(calls):
    """stdio 모드로 MCP 서버를 띄우고, 핸드셰이크 후 calls 를 순서대로 보낸다."""
    proc = await asyncio.create_subprocess_exec(
        "uv",
        "--directory",
        str(MCP_DIR),
        "run",
        "server.py",
        "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    assert proc.stdin is not None and proc.stdout is not None  # PIPE 로 띄웠으므로 보장
    stdin, stdout = proc.stdin, proc.stdout

    async def send(req):
        stdin.write((json.dumps(req) + "\n").encode())
        await stdin.drain()

    async def recv(timeout=30.0):
        line = await asyncio.wait_for(stdout.readline(), timeout)
        return json.loads(line) if line else None

    responses = []
    try:
        # MCP 초기화 핸드셰이크
        await send(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "lab06_mcp_query", "version": "0.1"},
                },
            }
        )
        await recv()
        await send(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        )

        for i, req in enumerate(calls, start=1):
            req = {**req, "id": i, "jsonrpc": "2.0"}
            await send(req)
            responses.append(await recv())
    finally:
        proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), 5)
        except asyncio.TimeoutError:
            proc.kill()
    return responses


def search(category: str, **kwargs) -> dict:
    """카테고리별 search_*_api 도구를 호출한다.

    Args:
        category: 'auth' / 'domestic_stock' / 'domestic_bond' /
                  'domestic_futureoption' / 'overseas_stock' /
                  'overseas_futureoption' / 'elw' / 'etfetn' 중 하나.
        **kwargs: subcategory, api_name, function_name, description, response
                  중 일부를 지정 (조합할수록 좁혀짐).

    Returns:
        {'status', 'message', 'total_count', 'results':[{...}, ...]} 형태의 dict.
        각 result 는 function_name, api_name, category, subcategory,
        url_main, url_chk 를 담는다.
    """
    _ensure_setup()
    tool = CATEGORY_TO_TOOL.get(category)
    if tool is None:
        return {
            "status": "error",
            "message": f"unknown category: {category} (allowed: {list(CATEGORY_TO_TOOL)})",
            "total_count": 0,
            "results": [],
        }

    call = {"method": "tools/call", "params": {"name": tool, "arguments": {**kwargs}}}
    [resp] = asyncio.run(_rpc_session([call]))
    sc = resp.get("result", {}).get("structuredContent")
    if sc:
        return sc
    # fallback: content[0].text 의 JSON 문자열에서 파싱
    content = resp.get("result", {}).get("content", [])
    if content and content[0].get("type") == "text":
        try:
            return json.loads(content[0]["text"])
        except Exception:
            pass
    return {"status": "error", "message": str(resp), "total_count": 0, "results": []}


def read_source(url_main: str, url_chk: str | None = None) -> str:
    """search 결과의 url_main(과 옵션으로 url_chk) 에서 실제 GitHub 코드를 가져온다.

    Args:
        url_main: search 결과의 'url_main' 필드 (examples_llm/.../*.py).
        url_chk:  선택. 체크 파일 (chk_*.py) 의 URL.

    Returns:
        성공: 메인 코드 텍스트 (FastMCP 의 ReadResourceContents wrap 을 풀어 원문 반환).
        실패: '❌ ...' 로 시작하는 에러 메시지.
    """
    import re

    _ensure_setup()
    args = {"url_main": url_main}
    if url_chk:
        args["url_chk"] = url_chk
    call = {
        "method": "tools/call",
        "params": {"name": "read_source_code", "arguments": args},
    }
    [resp] = asyncio.run(_rpc_session([call]))
    sc = resp.get("result", {}).get("structuredContent", {}) or {}
    main = (sc.get("results") or {}).get("main") or {}
    if main.get("status") != "success":
        return f"❌ read_source 실패: {main.get('message', 'unknown error')}"

    text = main.get("content", "")
    # 서버 측은 fastmcp 의 ReadResourceContents 객체를 str() 변환해 보내므로 unwrap 한다.
    # 예: "[ReadResourceContents(content='실제코드...', mime_type='text/plain')]"
    if text.startswith("[ReadResourceContents("):
        m = re.search(r"content='(.*)', mime_type=", text, re.DOTALL)
        if m:
            try:
                return m.group(1).encode().decode("unicode_escape")
            except Exception:
                return m.group(1)
    return text


def _demo():
    print("=" * 70)
    print("§500 lab06 — KIS Code Assistant MCP 직접 호출 데모")
    print("=" * 70)
    print(f"\n클론 위치: {CLONE}")
    print(f"MCP 서버:  {MCP_DIR}/server.py\n")

    # 1단계: search
    print(
        '[1단계] search("domestic_stock", subcategory="기본시세", function_name="inquire_price")'
    )
    hits = search(
        "domestic_stock", subcategory="기본시세", function_name="inquire_price"
    )
    print(f"  → status: {hits.get('status')}, total_count: {hits.get('total_count')}")
    for r in (hits.get("results") or [])[:3]:
        print(f"    • {r['function_name']} — {r['api_name']}")
        print(f"        url_main: {r['url_main']}")

    if not hits.get("results"):
        print("\n❌ 검색 결과 없음. 클론·data.csv 상태를 확인하세요.")
        return

    # 2단계: read_source
    first_url = hits["results"][0]["url_main"]
    print(f'\n[2단계] read_source(...) for "{hits["results"][0]["function_name"]}"')
    code = read_source(first_url)
    if code.startswith("❌"):
        print(f"  {code}")
        print("  (인터넷 연결을 확인하세요 — read_source 는 GitHub raw fetch입니다)")
        return

    # 코드에서 tr_id 가 정의된 라인을 단순 grep
    tr_id_line = next(
        (
            ln.strip()
            for ln in code.splitlines()
            if "tr_id" in ln.lower() and "=" in ln and '"' in ln
        ),
        None,
    )
    print(f"  → 코드 길이: {len(code)} bytes")
    if tr_id_line:
        print(f"  → 코드 안 tr_id 라인: {tr_id_line}")
    print("\n  ✓ MCP 는 마법 박스가 아니라 ==검색 엔진 + 코드 fetcher==임을 확인.")
    print("    AI 에이전트가 채팅 뒤에서 정확히 이 두 단계를 돈다.")


if __name__ == "__main__":
    _demo()
