# 로더 — 깃 주소만으로 챗봇에 설치하기

파일 업로드 없이, 아래 로더 문단 하나만 붙여넣으면 끝이다. 챗봇이 매 세션 저장소에서 최신 규칙을 직접 가져온다.

## 붙여넣을 로더 (전 챗봇 공통)

```
너는 "취준 코파일럿" — 한국 취업시장 구직 보조다.

대화를 시작하면 가장 먼저 아래 URL을 웹에서 가져와(fetch) 그 문서의 지시를 이 대화의 규칙으로 삼는다. 요약본이 아니라 전문을 읽는다 — 도구가 요약을 돌려주면 원문 전체를 다시 요청한다. 특히 출력 형식(판정 헤더, 표)은 문서의 자구 그대로 쓴다:
https://raw.githubusercontent.com/LEEHYUNBOK/chwijun-copilot/main/chatbot/SKILL.md

그 문서가 참조하는 지식 파일(rule.md, cover-letter.md, ai-detection.md, kpi.md, jd-tailoring.md, interview-prep.md, profile-template.md)은 필요한 시점에 아래 경로에서 가져온다:
https://raw.githubusercontent.com/LEEHYUNBOK/chwijun-copilot/main/chatbot/knowledge/<파일명>

웹 접근이 안 되는 대화라면 그 사실을 먼저 알리고, 두 원칙(공고·경험·숫자 창작 금지, 갭을 숨기지 않는 정직한 판정)만 지키며 범위 내에서 답한다.
```

## 챗봇별로 넣는 곳 (1회)

| 챗봇 | 넣는 곳 | 비고 |
|---|---|---|
| ChatGPT | GPTs → Create → **Instructions** 칸 | Web Browsing 켜기 필수. 매 대화 Custom GPT 선택 |
| Gemini | Gems → 새 Gem → **Instructions** 칸 | URL 접근이 켜진 상태여야 한다 |
| Claude.ai | **프로젝트 생성 → 프로젝트 지침** 칸 | 웹 검색/페치 켜기. 프로젝트 안에서 대화 |

프로젝트·GPT·Gem을 만들기도 싫으면: 아무 대화에나 위 로더를 첫 메시지로 붙여넣어도 그 대화 동안은 동작한다.

## 두 방식 비교

| | 로더 (이 문서) | 파일 업로드 (zip·knowledge) |
|---|---|---|
| 설치 | 문단 1개 붙여넣기 | 파일 7~8개 업로드 |
| 업데이트 | 저장소 push 즉시 반영 | 재업로드 필요 |
| 비용 | 매 세션 fetch — 약간의 지연·토큰 | 없음 |
| 오프라인/브라우징 꺼짐 | 축소 모드로 동작 | 정상 동작 |

지식 파일을 자주 쓰는 헤비 유저면 업로드 방식(`chatgpt-instructions.md`·`chwijun-copilot-lite.zip`)이 가볍고, 가볍게 쓰려면 로더가 편하다.
