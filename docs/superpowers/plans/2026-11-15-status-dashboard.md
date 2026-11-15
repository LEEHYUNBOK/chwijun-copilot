# 위키 상태 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/chwijun-copilot:status`로 위키 문서마다 "면접에서 버틸 만큼 채워졌나"를 7칸으로 채점하고, 그 결과를 정적 HTML 한 장으로 본다. 부족한 칸은 질문 하나씩으로 채운다.

**Architecture:** LLM(스킬)은 바뀐 문서만 읽어 칸별 판정을 낸다. 퍼센트는 계산하지 않는다. `scripts/status.py`(표준 라이브러리만)가 판정을 검증해 `<wiki_path>/.status/scores.json`에 쌓고, 채움률을 계산하고, `<wiki_path>/.status/index.html`을 다시 만든다. 채우기는 같은 스킬이 인자를 받아 처리한다. 질문 → 위키 수정안 → 사용자 확인 → 반영 → 그 문서 재채점 순서다.

**Tech Stack:** Python 3 표준 라이브러리(json·hashlib·unicodedata·re·argparse·html), 정적 HTML+CSS+바닐라 JS, Claude Code 스킬(SKILL.md).

**Spec:** `docs/status-dashboard/README.md`(「지금까지 합의된 설계」 표) + `docs/status-dashboard/01_채점기준_v4.md`(채점 기준, 2026-11-15 고정). 검증 경위는 같은 폴더의 07~14. 이슈 #14(대시보드)·#18(기준 개정).

## Global Constraints

- 판정 단계: 충분함 1 / 부족함 0.5 / 비어 있음 0 / 한계 명시 = 분모 제외. 채움률 = 점수 합 ÷ (7 − 한계 명시 칸 수) × 100. 가중치는 전 칸 동일
- **LLM은 칸별 판정만 낸다. 채움률은 스크립트가 계산한다** (v2 #7). 스킬 지시문 어디에도 LLM에게 퍼센트를 쓰게 하지 않는다
- 채움률은 항상 `N% (점수 합 X / 분모 Y, 한계 명시 Z칸)` 셋을 같이 표시한다 (v1 #9)
- 문서 유형: 프로젝트 / 장애 / 조사 (v4 #1) + **제외**(목차·개요·정정이력·프로필·트래커처럼 채점 대상이 아닌 문서 — 설계 표 「채점 대상」 행)
- 채점 출력에 사람 이름·지원 회사명·티켓 번호·테이블명·코드 식별자를 쓰지 않는다. 근거 위치는 절 이름으로만 (v1 #8, v2 #6)
- 위키 수정은 **사용자 확인 후에만**. 사용자가 말하지 않은 사실·숫자를 만들지 않는다. 답이 없으면 비워 둔다
- 외부 의존성 추가 금지. HTML은 외부 JS 없음. 외부 리소스는 Pretendard CSS 한 줄만 허용(`docs/index.html`과 같은 URL)
- 색·폰트 토큰은 `docs/index.html` 11~22행의 라이트/다크 토큰을 그대로 쓴다. 라이트 기본 + 우상단 테마 토글
- 대시보드 데이터는 사용자 위키 폴더(`<wiki_path>/.status/`)에만 저장한다. 리포에는 커밋하지 않는다
- 스크립트 경로 규약: `<스킬 베이스 디렉터리>/../../scripts/status.py` (job-fit과 같음)

## Review Focus

1. **macOS 한글 파일명(NFD)** — iCloud·Finder에서 온 파일명은 자모가 분리된 상태(NFD)일 수 있다. 같은 문서가 키 두 개로 쌓이면 안 된다 → 키는 NFC로 정규화한다. Task 2에서 테스트
2. **채점 뒤 문서를 고침** — 화면에 옛 점수가 최신처럼 보이면 안 된다 → "채점 후 수정됨" 표시를 단다. Task 4에서 테스트
3. **문서 삭제·이름 변경** — 사라진 문서의 점수가 남으면 안 된다 → scan이 `removed`로 보고하고, render는 파일이 없는 항목을 그리지 않는다. Task 2·4에서 테스트
4. **LLM 출력 형식이 깨짐** — 판정 줄 누락, 칸이 6개, 부족함 칸에 질문이 없음. 트레이스백이 아니라 무엇이 틀렸는지 한 줄로 알리고 exit 2 → Task 3에서 테스트
5. **전 칸 한계 명시**(분모 0) — 0으로 나누지 말고 `판정 불가 (전 칸 한계 명시)`로 표시한다. Task 1에서 테스트

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `scripts/status.py` (생성) | 채점 결과 파싱·검증·저장(scores.json), 변경 감지, 채움률 계산, HTML 생성. 서브커맨드 `scan`·`record`·`render`·`--selftest` |
| `scripts/test_scripts.sh` (수정) | status.py 스모크 테스트 추가 |
| `skills/status/SKILL.md` (생성) | `/chwijun-copilot:status` — 채점 흐름(인자 없음)과 채우기 흐름(`<문서> [칸]`) |
| `skills/status/rubric.md` (생성) | 채점 기준 v4의 판정용 본문(변경 이력 제외) + `제외` 유형 + 출력 형식 |
| `agents/chwijun-copilot.md`, `README.md` (수정) | 스킬 라우팅·목록·변경 이력에 status 추가 |

---

### Task 1: 채점 결과 파서와 채움률 계산

**Files:**
- Create: `scripts/status.py`
- Modify: `scripts/test_scripts.sh` (마지막 `[ $fail -eq 0 ]` 줄 앞)

**Interfaces:**
- Produces:
  - `SCORE: dict[str, float] = {"충": 1.0, "부": 0.5, "비": 0.0}`
  - `CELLS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")`
  - `TYPES = ("프로젝트", "장애", "조사", "제외")`
  - `rate(cells: list[str]) -> tuple[float, int]` — (점수 합, 분모). `한`은 분모 제외
  - `fill_text(cells: list[str]) -> str` — `"57.1% (점수 합 4.0 / 분모 7, 한계 명시 0칸)"` / 분모 0이면 `"판정 불가 (전 칸 한계 명시)"`
  - `parse_result(text: str) -> dict` — 반환 `{"type": str, "cells": list[str], "rows": list[dict]}`. rows 원소는 `{"cell": "C1", "verdict": "부족함", "where": str, "why": str, "ask": str}`. 형식 오류는 `ValueError("<무엇이 틀렸는지 한 줄>")`
- 입력 형식(rubric.md 「출력 형식」과 같음): `유형: <문서> = <유형>` 한 줄, 칸 표 `| C1 | 판정 | 근거 위치 | 이유 | 채우기 질문 |`, `판정: <문서> = 충,부,비,한,부,충,부` 한 줄. 유형이 `제외`면 표·판정 줄 없이 `제외 이유: <한 줄>`만 있다 → `cells == []`, `rows == []`, `"reason"` 키 추가

- [ ] **Step 1: 셀프테스트 작성** — `status.py`에 `selftest()`를 두고 `--selftest`로 실행한다(track_add.py와 같은 방식). 단언:

```python
assert rate(list("부부충부충충충")) == (5.5, 7)
assert rate(list("충부충부한충부")) == (4.5, 6)
assert fill_text(list("충부부부부부부")) == "57.1% (점수 합 4.0 / 분모 7, 한계 명시 0칸)"
assert fill_text(list("한한한한한한한")) == "판정 불가 (전 칸 한계 명시)"
r = parse_result(SAMPLE_OK)          # 유형 조사, 판정 줄 충,부,충,부,비,충,충, C2·C4·C5 행에 이유·질문
assert r["type"] == "조사" and r["cells"] == list("충부충부비충충")
assert [x["cell"] for x in r["rows"]] == list(CELLS)
assert parse_result(SAMPLE_EXCLUDED) == {"type": "제외", "cells": [], "rows": [], "reason": "목차 문서"}
for bad, word in [(SAMPLE_NO_VERDICT, "판정 줄"), (SAMPLE_SIX_CELLS, "7칸"),
                  (SAMPLE_NO_QUESTION, "C4"), (SAMPLE_BAD_TYPE, "유형")]:
    try: parse_result(bad); assert False
    except ValueError as e: assert word in str(e)
```

`SAMPLE_*`는 같은 파일의 모듈 상수로 둔다(가상 문서명 `doc`, 실제 위키 내용 금지).

- [ ] **Step 2: 실패 확인** — Run: `python3 scripts/status.py --selftest` / Expected: `NameError` 또는 파일 없음

- [ ] **Step 3: 구현** — 판정 줄 정규식은 `docs/status-dashboard/집계.py`의 `LINE`, 유형은 `KIND`(+`제외`)를 재사용한다. 표 행은 `^\|\s*(C[1-7])\s*\|`로 시작하는 줄을 `|`로 나눈다. 판정 줄의 칸과 표의 판정 단어가 다르면 `ValueError("C3: 표는 부족함, 판정 줄은 충")`. 부족함·비어 있음 행의 이유·질문이 비었거나 `-`면 `ValueError("C4: 부족함인데 채우기 질문이 없음")`

- [ ] **Step 4: 통과 확인** — Run: `python3 scripts/status.py --selftest` / Expected: `selftest OK`

- [ ] **Step 5: test_scripts.sh에 한 줄 추가** — `python3 status.py --selftest >/dev/null || { echo "FAIL: status --selftest"; fail=1; }`. `py_compile` 목록에도 `status.py` 추가. Run: `bash scripts/test_scripts.sh` / Expected: `ALL PASS`

- [ ] **Step 6: Commit** — `git add scripts/status.py scripts/test_scripts.sh && git commit -m "feat(status): 채점 결과 파서와 채움률 계산"`

---

### Task 2: 변경 감지 (`scan`)

**Files:**
- Modify: `scripts/status.py`, `scripts/test_scripts.sh`

**Interfaces:**
- Consumes: 없음(파일 시스템)
- Produces:
  - `doc_key(path: Path, wiki: Path) -> str` — `wiki` 기준 상대 경로, **NFC 정규화**, `/` 구분
  - `load(wiki: Path) -> dict` — `<wiki>/.status/scores.json`, 없으면 `{"rubric": "v4", "docs": {}}`
  - `save(wiki: Path, data: dict) -> None` — `.status/` 없으면 만든다. `ensure_ascii=False, indent=1`
  - `scan(wiki: Path) -> dict` — `{"changed": [key...], "unchanged": [key...], "removed": [key...]}`. 대상은 `wiki` 아래 `*.md` 전체(숨김 폴더 `.*` 제외). changed = 저장된 항목이 없거나 sha256이 다름. removed = 저장돼 있으나 파일이 없음
  - CLI: `python3 status.py scan <wiki_path>` → 위 dict를 JSON으로 stdout
- scores.json 스키마: `{"rubric": "v4", "docs": {"<key>": {"sha256": str, "type": str, "cells": [...], "rows": [...], "reason": str?, "scored_at": "YYYY-MM-DD"}}}`

- [ ] **Step 1: 테스트 추가** (test_scripts.sh, 임시 위키 `/tmp/st_wiki_$$`)
  - 빈 `.status` 없는 위키에 `a.md`, `b.md` → `scan`의 changed == [a.md, b.md], removed == []
  - `scores.json`에 a.md의 현재 sha256을 넣어 두면 a.md는 unchanged
  - NFD 파일명: `python3 -c "import unicodedata,pathlib; pathlib.Path('/tmp/st_wiki_$$/'+unicodedata.normalize('NFD','문서.md')).write_text('x')"` 후, scores.json에 NFC 키 `문서.md`로 같은 해시를 넣으면 unchanged에 `문서.md`가 한 번만 나온다(Review Focus 1)
  - scores.json에만 있는 `gone.md` → removed == ["gone.md"] (Review Focus 3)
  - `.status/x.md`(숨김 폴더)는 결과에 나오지 않는다
- [ ] **Step 2: 실패 확인** — Run: `bash scripts/test_scripts.sh` / Expected: scan 관련 FAIL
- [ ] **Step 3: 구현** — 위 시그니처대로. `rglob("*.md")`에서 경로 조각 중 `.`으로 시작하는 것이 있으면 건너뛴다
- [ ] **Step 4: 통과 확인** — Run: `bash scripts/test_scripts.sh` / Expected: `ALL PASS`
- [ ] **Step 5: Commit** — `feat(status): 위키 변경 감지 scan`

---

### Task 3: 판정 기록과 유출 검사 (`record`)

**Files:**
- Modify: `scripts/status.py`, `scripts/test_scripts.sh`

**Interfaces:**
- Consumes: `parse_result`, `doc_key`, `load`, `save` (Task 1·2)
- Produces:
  - `leaks(source: str, output: str) -> list[str]` — 원문에서 식별자 꼴 토큰을 뽑아 출력에 그대로 나온 것을 반환. 토큰 패턴: `[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+`(밑줄), `[a-z]+[A-Z][A-Za-z]+` 및 `[A-Z][a-z]+[A-Z][A-Za-z]+`(카멜), `[A-Z]{2,}-[0-9]+`(티켓), 한국어 이름 꼴 `(?:담당|팀장|PM)\s*([가-힣]{2,4})`의 이름 부분. 13 재테스트에서 원문 대조로 쓴 방식과 같다
  - `record(wiki: Path, doc: str, result_path: Path) -> dict` — 결과 파일을 `parse_result`로 검증, 원문 대비 `leaks`가 비어 있지 않으면 `ValueError("출력에 원문 식별자: <토큰들>")`, 통과하면 scores.json의 해당 키를 현재 sha256·오늘 날짜로 덮어쓰고 그 항목을 반환
  - CLI: `python3 status.py record <wiki_path> <문서 상대경로> <result.md>` — 성공 시 `기록: <key> <fill_text>` 출력·exit 0, `ValueError`는 메시지 한 줄·exit 2 (Review Focus 4)
- **허용 목록:** 제품·도구 이름(예: `MySQL`, `jMeter`)이 원문과 출력에 함께 나오면 걸린다. 그래서 `leaks`는 `ALLOW = {"MySQL", "jMeter", "OpenTelemetry", "GitHub", "GitLab", "PostgreSQL", "MariaDB"}`를 뺀다. 13 재테스트에서 실제로 걸린 두 개(`MySQL`·`jMeter`)가 근거다

- [ ] **Step 1: 테스트 추가**
  - 원문 `원인은 user_point 테이블과 PointService였다. KAN-12 참고. 담당 홍길동` + 출력 이유 칸에 `user_point` → exit 2, stderr에 `user_point`
  - 같은 원문 + 출력에 `포인트 테이블`(일반어) → exit 0, scores.json에 키·`cells`·`sha256` 저장
  - 출력 채우기 질문에 `홍길동` → exit 2
  - 판정 줄 없는 결과 파일 → exit 2, 트레이스백 없음(`grep -q Traceback`이 실패해야 함)
  - `제외` 결과 → exit 0, 저장된 항목의 `type == "제외"`
- [ ] **Step 2: 실패 확인** — `bash scripts/test_scripts.sh` / Expected: record 관련 FAIL
- [ ] **Step 3: 구현** — 위 시그니처대로
- [ ] **Step 4: 통과 확인** — Expected: `ALL PASS`
- [ ] **Step 5: Commit** — `feat(status): 판정 기록과 원문 식별자 유출 검사`

---

### Task 4: 대시보드 HTML (`render`)

**Files:**
- Modify: `scripts/status.py`, `scripts/test_scripts.sh`

**Interfaces:**
- Consumes: `load`, `rate`, `fill_text`, `doc_key`, `CELLS` (Task 1·2)
- Produces:
  - `render(wiki: Path) -> Path` — `<wiki>/.status/index.html`을 쓰고 경로 반환
  - CLI: `python3 status.py render <wiki_path>` → 경로 한 줄 출력

**화면 결정 (frontend-design 6줄 선언):**
- 미학: 밀도 높은 · 점검표 · 무채색 기반 / 참조점: 리포의 `docs/index.html`(같은 제품의 얼굴)
- 타이포: Pretendard Variable, 크기 13/15/18/24px, 굵기 400/600/700
- 색: `docs/index.html` 토큰 그대로. 칸 상태 = 충분함 `--ok` / 부족함 `--warn` / 비어 있음 `--bad` / 한계 명시 `--text-faint`. 주색 `--accent`는 "명령어 복사" 버튼에만
- 간격: 4px 기준, 4/8/12/16/24 / 형태: radius 6px 하나, 면 구분은 경계선(`--border`)만, 그림자 없음

**화면 구성:**
- 상단 요약 한 줄: `채점 문서 N개 · 평균 채움률 M% · 채점 후 수정됨 K개 · 제외 E개`. 평균은 판정 불가 문서를 뺀 문서별 채움률의 산술 평균
- 문서 목록: 채움률 오름차순(가장 부족한 문서가 위). 행마다 문서명 · 유형 · `fill_text` · 칸 7개 칩(C1~C7, 상태색 + 글자 `충/부/비/한`, 색만으로 구분하지 않음) · 채점일
- 행을 펼치면 부족함·비어 있음 칸마다 `칸 이름 — 이유` + `채우기 질문` + **명령어 복사** 버튼. 복사 문자열은 `/chwijun-copilot:status <문서 키> <칸>`. `navigator.clipboard` 실패 시 버튼 옆에 문자열을 선택 가능한 텍스트로 보여준다
- 현재 파일 sha256 ≠ 저장된 sha256이면 행에 `채점 후 수정됨` 배지(Review Focus 2). 파일이 없으면 행을 그리지 않는다(Review Focus 3)
- `제외` 문서는 맨 아래 접힌 목록 한 줄씩(문서명 — 제외 이유)
- 빈 상태: 채점된 문서가 0개면 `아직 채점한 문서가 없습니다. /chwijun-copilot:status 를 실행하세요` 한 문장
- 모든 텍스트는 `html.escape`. 데이터는 `<script type="application/json">`에 넣고 JS가 그린다 — 이스케이프는 `</` → `<\/` 치환
- 테마: `docs/index.html` 255~265행의 토글 스크립트와 같은 방식(localStorage 키 `status-theme`, try/catch). 360px 폭에서 가로 스크롤 없음(칩 줄은 줄바꿈)

- [ ] **Step 1: 테스트 추가** — 임시 위키에 문서 3개를 record한 뒤 render:
  - `index.html`이 생기고 `57.1% (점수 합 4.0 / 분모 7, 한계 명시 0칸)` 문자열이 들어 있다
  - 기록 후 a.md 내용을 바꾸고 render → `채점 후 수정됨`이 나온다
  - b.md를 지우고 render → b.md 키가 HTML에 없다
  - 문서명에 `<script>`가 들어간 가짜 키를 scores.json에 넣고 render → HTML에 `<script>alert` 원문이 없다
  - 빈 위키 render → 빈 상태 문장이 있다
- [ ] **Step 2: 실패 확인** — Expected: render 관련 FAIL
- [ ] **Step 3: 구현** — HTML 템플릿은 `status.py` 안의 문자열 상수 하나. 외부 JS 없음
- [ ] **Step 4: 통과 확인** — Expected: `ALL PASS`. 추가로 생성된 HTML을 브라우저(360px·1280px, 라이트·다크)로 열어 눈으로 확인한다
- [ ] **Step 5: Commit** — `feat(status): 정적 대시보드 HTML`

---

### Task 5: 스킬 `/chwijun-copilot:status`

**Files:**
- Create: `skills/status/SKILL.md`, `skills/status/rubric.md`
- Modify: `agents/chwijun-copilot.md`(스킬 라우팅 표에 한 행), `README.md`(스킬 목록 + 변경 이력)

**Interfaces:**
- Consumes: CLI `status.py scan|record|render` (Task 2~4)

**rubric.md** — `docs/status-dashboard/01_채점기준_v4.md`에서 다음 절만 그대로 옮긴다. 「판정 원칙」, 「판정 4단계」, 「7개 칸」, 「문서 유형별 읽는 법」, 「C4·C5 감점 귀속」, 「C5 내용 유형 예시」, 「출력 형식」, 「출력 규칙」. 변경 이력·재테스트 기록·「약점」 절은 옮기지 않는다. 채움률 계산 문장은 "스크립트가 계산한다, 쓰지 않는다"만 남긴다. 그 위에 두 가지를 더한다.
- 유형 `제외`: 목차·개요·정정이력·프로필·지원현황 트래커·브랜드 가이드처럼 경력 소재가 아닌 문서. 출력은 `유형: <문서> = 제외` + `제외 이유: <한 줄>`만
- 맨 위 한 줄: `기준 v4 (2026-11-15). 검증 기록: 리포 docs/status-dashboard/`

**SKILL.md** — frontmatter `name: status`, description은 다음 상황을 트리거로 쓴다. "위키 뭐가 부족해?", "위키 채움 상태", "몇 퍼센트 쌓였어", "/chwijun-copilot:status", 부족 칸 채우기. 본문 절은 다음과 같다.

0. 준비 — `~/.claude/chwijun-copilot.json`의 `wiki_path`. 없으면 wiki-bootstrap 안내 후 중단(apply-followup 0절과 같은 문구). `--wiki <경로>` 인자가 있으면 그 경로를 우선한다(설정 파일을 만들지 않고 다른 위키를 볼 때)
1. **채점 흐름(인자 없음)**
   1. `python3 "<스킬 베이스 디렉터리>/../../scripts/status.py" scan <wiki_path>`
   2. `changed`가 0개면 바로 3단계로
   3. changed 문서마다: `rubric.md`와 그 문서 **한 개만** 읽고 판정 출력을 scratch 파일에 쓴다. 문서 안의 링크는 열지 않는다. changed가 5개를 넘으면 서브에이전트에 5개씩 나눠 맡긴다. 지시문은 rubric.md 경로 + 문서 경로 + "결과를 <파일>에 쓴다"뿐이고, 대화 맥락·이전 점수는 주지 않는다
   4. 문서마다 `status.py record ...`. exit 2면 메시지대로 그 문서만 다시 채점(최대 1회), 또 실패하면 건너뛰고 보고
   5. `status.py render <wiki_path>` → 경로를 알려주고 `open`으로 연다
   6. 채팅 보고: 가장 부족한 문서 3개의 `fill_text`와 빈 칸 이름. 퍼센트는 record·render 출력에서 그대로 옮긴다(직접 계산 금지)
2. **채우기 흐름(`<문서 키> [칸]`)**
   1. scores.json에서 그 문서의 부족함·비어 있음 칸을 고른다(칸 지정 시 그 칸만)
   2. 칸마다 저장된 `채우기 질문`을 **한 번에 하나** 묻는다
   3. 답을 받으면 위키 문서의 어느 절에 무엇을 넣을지 수정안을 보여주고 확인을 받는다. 확인 전에는 쓰지 않는다
   4. "모른다·측정 안 했다"면 비워 둔다. 사용자가 원하면 그 사실을 「주의」에 한 줄로 적는 안을 제시한다. 이렇게 하면 한계 명시가 되어 분모에서 빠진다. 화면에는 한계 명시 칸 수로 남는다는 점을 함께 말한다
   5. 다 끝나면 그 문서만 채점 흐름 3~5단계를 다시 한다
3. 원칙 — 사용자가 말하지 않은 사실·숫자를 만들지 않는다. 동료 실명을 위키에 쓰지 않는다. 퍼센트는 스크립트 출력만 인용한다

- [ ] **Step 1: 라우팅 확인 시나리오 작성** — 새 세션(`claude --plugin-dir .`)에서 확인할 프롬프트 3개를 PR 설명에 적는다. ① "위키 뭐가 부족한지 봐줘" → status 스킬 로드 ② "/chwijun-copilot:status 문서.md C5" → 채우기 흐름 ③ 설정 파일이 없는 상태 → wiki-bootstrap 안내
- [ ] **Step 2: rubric.md·SKILL.md 작성**, agents 라우팅 한 행, README 스킬 표 한 행 + 변경 이력 한 줄
- [ ] **Step 3: 스모크** — 임시 위키(가상 문서 3개: 프로젝트 1·장애 1·목차 1)에 `--wiki`로 시나리오 ①을 실행해서 확인한다. scores.json에 3개 항목이 생기고, 목차 문서는 `제외`이고, HTML이 열리고, 채팅 보고의 퍼센트가 HTML과 같아야 한다. 시나리오 ②로 칸 하나를 채운 뒤 그 문서만 재채점됐는지 본다(scored_at·sha256 변경). 시나리오 ③도 확인
- [ ] **Step 4: 개인 흔적 검사** — `bash scripts/sync_lite.sh`를 실행하면 `skills/` 전체에 `TRACES` 패턴을 grep한다. 흔적이 0건이어야 한다(exit 0). `bash scripts/test_scripts.sh` ALL PASS
- [ ] **Step 5: Commit** — `feat(status): /chwijun-copilot:status 스킬`

---

### Task 6: 본인 위키로 첫 실행 (리포 밖)

리포에 커밋하지 않는 검증 단계다. 설계 표의 「대상 위키: 본인 위키 먼저」를 이행한다.

- [ ] **Step 1:** `/chwijun-copilot:status --wiki <개인 위키 경로>` 실행. 설정 파일은 만들지 않는다
- [ ] **Step 2: 대조** — 13 재테스트에서 다수결이 난 10문서의 이번 판정을 다수결과 칸별로 비교한다. 다른 칸 수를 센다(채점자 1명이므로 2:1 칸은 달라도 정상). 차이가 13의 불일치 칸 밖에서 나오면 그 칸을 기록한다
- [ ] **Step 3:** 사용자에게 HTML을 보여주고 문서 하나를 골라 채우기 흐름을 실제로 1회 돈다
- [ ] **Step 4: Codex 최종 검증** — 설계 표 「최종 검증: Codex」. `codex exec --skip-git-repo-check -s read-only --ephemeral`로 구현 브랜치 diff와 이 계획·`rubric.md`·v4 기준을 함께 읽힌다. 확인 항목은 네 가지다. ① 계획의 Interfaces·Global Constraints를 지켰나 ② Review Focus 5건이 테스트로 고정됐나 ③ 스킬 지시문에 LLM이 퍼센트를 내는 경로가 남았나 ④ 유출 검사가 우회되는 경로가 있나. 지적은 수용/기각과 근거를 남긴다. 수치 지적은 스크립트로 재확인한다
- [ ] **Step 5:** 결과(대조표·사용자 피드백·Codex 감사)를 `docs/status-dashboard/15_첫실행.md`에 기록한다. 공개본은 문서명·수치만 남기고 원문 인용은 뺀다. 이슈 #14에 댓글

---

## 하지 않는 것 (YAGNI — 필요해지면 그때)

- 직군별 채점(#16), 설명 가능성 테스트(#15), 지원현황 지표·포트폴리오 보기(#17)
- 웹 서버·DB·실시간 갱신. HTML은 render할 때마다 새로 쓴다
- 챗봇 라이트판 이식 — 스크립트 실행이 전제라 제외
- v5 예시 보강(C6 둘 이상 명시·C5/C7 예시)은 rubric.md만 고치면 되므로 구현과 독립적으로 언제든 반영한다
