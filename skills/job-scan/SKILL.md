---
name: job-scan
description: watchlist의 관심 회사 채용페이지와 채용 사이트 검색을 한 번에 훑어 새 공고만 골라 적합도 분석 후 지원현황 트래커에 등록한다. "새 공고 스캔해줘"처럼 온디맨드로 실행한다.
---

# job-scan — 관심 회사 공고 온디맨드 스캔

watchlist 회사들의 ATS를 훑어 **새로 올라온 공고** 중 사용자 직군에 맞는 것만 골라 적합도를 매기고 트래커에 넣는다.
개별 URL 하나를 분석하는 건 `job-fit`이고, 이건 **여러 회사를 한 번에 훑는 배치**다.

실행 예: "새 공고 스캔해줘", "A사·B사만 스캔", "/chwijun-copilot:job-scan"

경로 규약: 이 스킬의 베이스 디렉터리 기준 두 단계 위가 플러그인 루트다. 스크립트는 `<스킬 베이스 디렉터리>/../../scripts/`에 있다.

## 0. 원칙

- **중복 금지.** 트래커에 이미 있는 공고(지원 링크 URL 대조)는 건너뛴다.
- **창작 금지.** 공고 본문에서 못 뽑은 요구사항은 지어내지 않는다.
- **과잉 등록 금지.** 프로필의 직군·연차에 맞는 것만. 명백한 타직군은 등록 자체를 안 한다. 제목 필터 기준은 watchlist.json의 `filters`다.
- **대기업 신입 공채도 등록 대상이다** — 신입 트랙이라는 이유만으로 제외하지 않는다. 대신 "신입 등급으로 재시작"이라는 조건을 본문에 사실로 남긴다.

## 1. 준비

- 설정: `~/.claude/chwijun-copilot.json`을 읽는다. 없으면 `/chwijun-copilot:wiki-bootstrap` 온보딩을 안내하고 중단한다.
- watchlist: `<wiki_path>/watchlist.json`. 없으면 플러그인의 `templates/watchlist.json`을 복사해 주고 직군에 맞게 채우라고 안내한 뒤 중단한다.
- 프로필: `<wiki_path>/프로필.md` (job-fit과 동일 기준)
- 기존 등록분(dedup 셋): `tracker`가 local이면 `<wiki_path>/지원현황.md`의 `- 링크:` 줄 전수, notion이면 `track_add.py --ds <notion_ds_id> --list`로 전수 조회해 `링크` 필드를 쓴다.
- 인자로 특정 회사가 지정되면 그 회사만.

## 2. 회사별 공고 목록 수집 (ATS별)

Bash + curl로 목록을 받고 제목으로 1차 필터한다. **상세는 필터 통과분만 가져온다** (목록이 수백 개인 회사가 있으므로 반드시 제목 필터 먼저).

| ats | 목록 | 항목 |
|---|---|---|
| ashby | `curl -s https://api.ashbyhq.com/posting-api/job-board/<slug>` | `jobs[]`: title · location · jobUrl · descriptionPlain |
| greenhouse | `curl -s https://boards-api.greenhouse.io/v1/boards/<slug>/jobs` | `jobs[]`: title · location.name · absolute_url · id (상세: `.../jobs/<id>`) |
| greetinghr (호스팅) | `curl -sL https://<slug>.career.greetinghr.com/ko/` → `<script id="__NEXT_DATA__">` → queries 중 `["openings"]` (`/ko/main`은 404 — 쓰지 않는다) | openingId · title · dueDate. 상세: `/ko/o/<id>` |
| greetinghr (임베드) | `/ko/`가 404면 slug 오타이거나 호스팅 랜딩이 없는 것 — 둘은 404로 구분되지 않으니 slug부터 재확인하고, 맞는데도 404면 watchlist의 `list_url`(회사 자체 채용페이지)을 받아 HTML에서 `/ko/o/(\d+)` 링크로 openingId·title 열거 | 상세는 동일하게 greetinghr `/ko/o/<id>` __NEXT_DATA__ getOpeningById |
| toss | `GET api-public.toss.im/api/v3/ipd-eggnog/career/jobs` → `success` 내 job 배열 | 각 job: title · company_name · 자회사(metadata name에 "자회사/소속") · location.name · absolute_url(`?gh_jid=`) · application_deadline. 상세: `.../career/jobs/{gh_jid}` → `success.content`(HTML). 연차는 제목·본문에서 |
| saramin_company | `curl -sL -A "<브라우저 UA>" <list_url>` → HTML에서 `rec_idx=(\d+)` 정규식으로 열거. list_url은 `company-info/view-inner-recruit?csn=<csn>` 형태를 쓴다(`company-info/view`는 rec_idx가 안 나온다) | 상세: `python3 "<스킬 베이스 디렉터리>/../../scripts/fetch_jd.py" "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=<id>"` — 쿠키 절차·og 메타(경력·마감일) 추출 내장. curl로 view-detail을 직접 치지 않는다(쿠키 없으면 타 공고 본문이 온다). **⚠️ 사람인은 발췌본이다** — 자체 ATS가 있는 회사는 반드시 그쪽을 정본으로 쓴다 |
| custom / list_scan:false | 자동화 불가 | 목록 스킵하되 **보고에 "수동 대상"으로 명시**(조용히 빠뜨리지 않음). 사용자가 개별 URL 주면 job-fit로 |

**제목 1차 필터** — watchlist.json `filters.include` 중 하나 포함 AND `filters.exclude` 미포함 AND 희망 근무지. `Senior/Staff/Lead/Principal/시니어`는 버리지 말고 남겨서 분석 단계에서 판정한다(연차 정보가 제목에만 없을 수 있음).

## 2-1. 채용 사이트 전체 검색 (boards)

`watchlist.json`의 `boards[]`를 회사 스캔과 **별개로** 돈다. 회사 ATS가 아니라 사이트 전체 검색이므로 범위가 더 넓다.

- `search_url`의 `{kw}`에 `keywords[]`를 하나씩 URL 인코딩해 넣고 **키워드마다 한 번씩** curl 한다.
- **User-Agent 헤더 필수.** 없으면 차단된다: `curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"`
- 사람인은 목록 HTML에서 `rec_idx=(\d+)` 를 정규식으로 열거해 **키워드 간 합집합·중복제거**한다.
- 상세는 rec_idx마다 `python3 "<스킬 베이스 디렉터리>/../../scripts/fetch_jd.py" "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=<id>"` (쿠키 절차 내장, `detail_url` 직접 curl 금지). 출력 `note`에 "og:title 토큰 없음"이 뜨면 본문과 og:title이 같은 공고인지 대조. 본문이 이미지뿐인 공고가 흔하다 — 그 경우 og:title·og:description(회사명·직무명·경력·마감일)만 확보하고 못 뽑은 항목은 "확인불가"로 둔다.
- 검색 필터(지역·연차)는 `search_url`에 쿼리로 박는다 — 본인 조건에 맞게 watchlist에서 조정.
- boards 키워드·필터도 watchlist.json이 기준이다. 프로필의 직군이 복수면(개발+기획 등) 양쪽 키워드를 모두 넣으라고 안내한다.

**등록 상한.** 채용 사이트 검색은 중소·스타트업이 대량으로 섞인다. dedup 후 신규가 `max_register_per_run`(기본 15)을 넘으면 **적합도 높은 순으로 상한까지만 등록**하고, 나머지는 등록하지 말고 보고에 "상한 초과 N건 미등록"으로 **반드시 숫자를 남긴다**. 조용히 자르지 않는다.

## 3. dedup

목록에서 얻은 각 공고 URL을 트래커의 기존 지원 링크와 대조. 이미 있으면 스킵. **남은 게 없으면** "새 공고 없음"으로 보고하고 끝낸다.

## 4. 분석 & 등록 (job-fit 재사용)

새 공고 각각에 대해 `job-fit` 스킬의 3~4단계를 적용한다:

- 본문 상세 수집 → 요구사항 추출 → 프로필.md 기준 적합도 판정
- 트래커 기록은 job-fit §4의 규약 그대로 — local이면 지원현황.md 섹션 추가, notion이면 track_add.py (`--ds <notion_ds_id>`). 본문 md는 스크래치 폴더에 쓴 뒤 넘긴다.
- **fitLevel 하 + applyRecommendation 부적합**인 것은 등록하되 상태를 명확히 표기하거나, 사용자가 "상/중만"을 원하면 등록 생략하고 목록에만 언급

여러 공고는 병렬로 처리해도 된다. 단 등록(트래커 쓰기)은 순차로.

## 5. 보고

```
스캔: N개 회사 + 검색 키워드 M개 · 신규 공고 M개 발견 · 등록 K개 (상한 초과 미등록 X개)
- [회사] 직무 · 적합도 상/중/하 · 추천  → 기록 위치
- (부적합/무관 스킵분 요약)
```

적합도 높은 순으로. 새 게 없으면 그렇게 보고.

## watchlist 확장

새 회사를 넣으려면 그 회사 **채용 페이지 URL**을 받아 ats/slug를 확인하고 `<wiki_path>/watchlist.json`에 추가한다.

- `*.career.greetinghr.com/ko/o/*` → greetinghr, slug=서브도메인
- `jobs.ashbyhq.com/<org>/*` → ashby, slug=org
- `boards.greenhouse.io/<org>/*` 또는 `<org>.jobs` (gh_jid) → greenhouse, slug=org
- 그 외 자체 사이트 → custom (목록 자동화 불가, 개별 URL만 job-fit)
