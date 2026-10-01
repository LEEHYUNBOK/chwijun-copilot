# 취준 코파일럿 (chwijun-copilot)

한국 취업시장용 구직 코파일럿 Claude Code 플러그인. 경력 위키 온보딩부터 공고 적합도 분석·관심회사 스캔·이력서 규칙·지원 트래킹까지 한 번에 설치한다.

## 설치

마켓플레이스로:

```bash
/plugin marketplace add <이 저장소 GitHub 주소>
/plugin install chwijun-copilot
```

로컬 테스트로:

```bash
claude --plugin-dir /path/to/chwijun-copilot
```

## 시작하기

설치 후 온보딩 한 번이 필수다.

```
/chwijun-copilot:wiki-bootstrap
```

직군을 묻는 인터뷰로 시작해 경력 위키(프로필·작업 문서·지원현황 트래커)를 만든다. 이후는 자연어로 쓰면 된다.

```
이 공고 봐줘 https://...        # 적합도 분석 + 트래커 등록
새 공고 스캔해줘                 # watchlist 회사 일괄 스캔
자소서 문항 좀 다듬어줘          # 작성 규칙 로드
답 없는 데 있나 봐줘             # 팔로업 점검
계속 떨어지는데 왜지             # 탈락 패턴 분석
```

## 구성

| 구성요소 | 역할 |
|---|---|
| `agents/chwijun-copilot` | 요청을 맞는 스킬로 라우팅하는 진입점 |
| `skills/wiki-bootstrap` | 온보딩 — 직군 파악 → 인터뷰 → 경력 위키 스캐폴딩 |
| `skills/job-fit` | 공고 URL 하나의 적합도 분석 + 트래커 기록 |
| `skills/job-scan` | watchlist 회사 ATS·채용 사이트 일괄 스캔 (원티드 유령공고·사람인 쿠키 함정 처리 내장) |
| `skills/resume-writing` | 이력서·경력기술서·자소서 작성 규칙 + AI 문체 제거 + 문체 기계검사 |
| `skills/apply-followup` | 지원 후 무응답 건 점검, 한국 관행 기준 팔로업 케이던스 |
| `skills/apply-patterns` | 지원 퍼널·탈락 패턴 분석 (인과 겸손 원칙 내장) |

## 설정 파일

온보딩이 `~/.claude/chwijun-copilot.json`을 만든다.

```json
{ "wiki_path": "<경력위키 절대경로>", "tracker": "local", "notion_ds_id": "" }
```

- `tracker: "local"`(기본) — 지원 기록은 `<wiki_path>/지원현황.md`에 쌓인다. 추가 설정 없음.
- `tracker: "notion"` — `notion_ds_id`에 지원현황 DB의 data_source id를 넣고 `NOTION_TOKEN`을 설정하면 Notion DB에 행을 추가한다.

## 데이터

모든 데이터(프로필·위키·지원 기록)는 본인 머신의 `wiki_path` 폴더에만 남는다. 외부 전송은 Notion 트래커를 직접 켰을 때의 Notion API 호출이 전부다.

프로필에는 과장 금지 원칙이 박혀 있다 — 적합도 판정이 후하면 지원 실패로 돌아오기 때문이다.

## 라이선스

미정.
