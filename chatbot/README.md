# 챗봇판 (라이트) — Claude.ai · ChatGPT · Gemini

CLI 없이 챗봇에서 쓰는 판이다. 판정·서류 규칙은 그대로 들어가고, 일괄 스캔·쿠키 수집·파일 자동 기록은 빠진다 (그건 CLI 플러그인 전용).

| 대상 | 쓸 파일 | 올리는 곳 |
|---|---|---|
| Claude.ai | `chwijun-copilot-lite.zip` | 설정 → Capabilities → Skills → 업로드 (유료 플랜) |
| ChatGPT | `chatgpt-instructions.md` + `knowledge/` 7개 | GPTs → Create (Plus 플랜) |
| Gemini | `gemini-instructions.md` + `knowledge/` 7개 | Gem 만들기 |

각 instructions 파일 하단에 단계별 안내가 있다. 공통 사용법: 만들고 나서 첫 대화에서 "온보딩"이라고 하면 직군 인터뷰로 프로필을 만들어 준다 — 그 프로필.md를 지식/프로젝트에 넣어두면 끝.

`knowledge/`는 `skills/resume-writing/`의 사본이다. 원본이 바뀌면 여기도 다시 복사한다.
