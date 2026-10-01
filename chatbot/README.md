# 챗봇판 (라이트) — Claude.ai · ChatGPT · Gemini

CLI 없이 챗봇에서 쓰는 판이다. 판정·서류 규칙은 그대로 들어가고, 일괄 스캔·쿠키 수집·파일 자동 기록은 빠진다 (그건 CLI 플러그인 전용).

**기본 설치법은 로더다 — `LOADER.md`의 문단 하나를 챗봇 지시문 칸에 붙여넣으면 끝.** 파일 업로드가 전혀 필요 없고, 규칙은 이 저장소에서 매 세션 실시간으로 당겨온다.

업로드 방식(오프라인·헤비 유저용 대안):

| 대상 | 쓸 파일 | 올리는 곳 |
|---|---|---|
| Claude.ai | `chwijun-copilot-lite.zip` | 설정 → Capabilities → Skills → 업로드 (유료 플랜) |
| ChatGPT | `chatgpt-instructions.md` + `knowledge/` 7개 | GPTs → Create (Plus 플랜) |
| Gemini | `gemini-instructions.md` + `knowledge/` 7개 | Gem 만들기 |

공통 사용법: 설치 후 첫 대화에서 "온보딩"이라고 하면 직군 인터뷰로 프로필을 만들어 준다 — 그 프로필.md를 지식/프로젝트에 넣어두면 끝.

`knowledge/`는 `skills/resume-writing/`의 사본이다. 원본이 바뀌면 여기도 다시 복사한다.
