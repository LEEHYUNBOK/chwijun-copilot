# 회귀 eval 스위트

`claude plugin eval`(Claude Code ≥ 2.1.269) 기반 회귀 테스트. 과거에 실제로 실패했던 입력을 재현 케이스로 고정해, 스킬 변경이 알려진 동작을 깨뜨리지 않는지 확인한다.

## 실행

```bash
claude plugin eval . --scaffold --ablation none -j 4 \
  --allow-tools Write Edit \
  --judge-model claude-sonnet-5-5 \
  --no-publish --trust-plugin --max-cost-usd 20
```

- exit 0 = 전 케이스 통과. 1회 전체 실행 약 2분 · $3 내외.
- `--scaffold` 필수 — 각 케이스의 `scaffold.sh`가 샌드박스 임시 HOME에 config·픽스처를 심는다.
- `--judge-model claude-sonnet-5-5` 필수 — 기본 judge(haiku)는 한국어 루브릭을 오판한다(규약을 지킨 트래커 파일을 FAIL로 채점한 사례를 파일 증거로 확인).
- `--ablation none` — 회귀 목적이라 플러그인 없는 대조군 비교가 불필요.

## 케이스 (6종)

| 케이스 | 재현 대상 (원 결함/규칙) | 채점 |
|---|---|---|
| `d2-tracker-format` | D-2·D-4: 트래커 섹션 삽입 위치·`####` 본문 강등·`### 적합도 분석` | regex + LLM(구조·정직 판정) |
| `d8-broken-watchlist` | D-8: 깨진 watchlist JSON → 진단 후 중단(추측 스캔·필터 확장·등록 금지) | regex(링크 수 불변) + LLM |
| `rule-no-profile` | job-fit §1: 프로필 부재 시 세션 사실 대체+출처 고지+형식 유지 | regex(N/100) + LLM |
| `rule-attribution` | wiki-bootstrap §2-3: 멀티 회사 성과의 회사 귀속 질문(추측 단정 금지) | LLM |
| `rule-contradiction` | wiki-bootstrap §0 / resume-writing §1: 자료-진술 모순 즉시 대조 | LLM |
| `rule-output-volume` | wiki-bootstrap §2-3: 산출량(100장)을 성과로 받지 않음 | LLM |

## 설계 메모 (케이스 추가 시 지킬 것)

- **프롬프트는 스킬을 명시 호출**("job-fit 스킬로 …"): 자연어 트리거는 샌드박스에서 비결정적(1턴 일반 답변으로 끝나는 런 실측)이라 회귀가 플레이키해진다. 라우팅 검증은 이 스위트의 몫이 아니다(X7·채널 E2E가 담당).
- **scaffold는 인라인 불가** — `scaffold_script: scaffold.sh`처럼 파일 경로만 받는다.
- **멀티턴 핑퐁 재현 불가** — 마지막 턴만 채점된다. 인터뷰형 규칙은 "한 발화에 맥락을 담은 단일턴"으로 축소하거나, 수동 재검증(`qa-시뮬레이션/재검증-규칙4/`)으로 보완한다.
- **LLM grader 루브릭에는 "허용되는 것" 목록을 명시**할 것 — judge가 `---` 구분선이나 규약상 필수인 `###` 소제목까지 위반으로 읽는 오판이 실측됐다.
- regex의 `target: last_message`는 판정문이 중간 턴에 나오면 놓친다 — 상태 검사는 `{source: file, path}`, 발화 검사는 `trace` 권장.
- 새 결함을 수정하면: 그 결함을 일으킨 입력을 케이스로 추가하고, 수정 전 커밋에서 FAIL·수정 후 PASS를 확인한다.

## 기준 기록 (2026-10-02, HEAD 기준)

6/6 케이스 × 2런 전부 1.0, exit 0 (judge=sonnet). 조정 이력: 트리거 비결정 2건(no-profile·attribution — 명시 호출로 고정), judge 오판 2건(structure·asks-which-company — 루브릭에 허용 목록 명시 + judge 모델 승격).
