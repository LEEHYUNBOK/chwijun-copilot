#!/bin/bash
# D-2·D-4 회귀용 상태: config + 프로필 + 기존 섹션 있는 트래커
set -eu
mkdir -p "$HOME/.claude" wiki
printf '{"wiki_path": "%s/wiki", "tracker": "local", "notion_ds_id": ""}\n' "$PWD" > "$HOME/.claude/chwijun-copilot.json"
cat > wiki/프로필.md <<'EOF'
# 프로필
## 한 줄
백엔드 2년 10개월 (Spring, MySQL, Redis)
## 직군
개발 — 백엔드
## 연차
2년 10개월 (만 3년은 2026-12)
## 주력 스킬
Java/Spring 2년 10개월 실무, MySQL, Redis
## 공백
Kotlin 없음, MSA 전환 경험 없음
## 표기 규칙
- 연차를 3년으로 반올림하지 않는다
EOF
cat > wiki/지원현황.md <<'EOF'
# 지원 현황

> 한 공고 = `##` 섹션 하나. 새 공고는 이 안내 아래, 기존 섹션 위에 추가.
> 상태 어휘: 지원 전 · 지원완료 · 서류통과 · 코테 중 · 면접 · 탈락 · 최종합격 · 지원 실패

## 기존상사 — 백엔드 엔지니어
- 상태: 지원 전
- 링크: https://example.com/old/1
- 등록: 2026-09-30
EOF
