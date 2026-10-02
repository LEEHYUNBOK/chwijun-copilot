#!/bin/bash
# D-8 회귀용 상태: config + 트래커(링크 1개) + 깨진 watchlist.json
set -eu
mkdir -p "$HOME/.claude" wiki
printf '{"wiki_path": "%s/wiki", "tracker": "local", "notion_ds_id": ""}\n' "$PWD" > "$HOME/.claude/chwijun-copilot.json"
cat > wiki/프로필.md <<'EOF'
# 프로필
## 한 줄
백엔드 2년 (Spring, MySQL)
## 직군
개발 — 백엔드
EOF
cat > wiki/지원현황.md <<'EOF'
# 지원 현황

> 한 공고 = `##` 섹션 하나.

## 기존상사 — 백엔드
- 상태: 지원 전
- 링크: https://example.com/old/1
EOF
cat > wiki/watchlist.json <<'EOF'
{
  "companies": [
    {"name": "당근", "ats": "greenhouse", "slug": "daangn"},
    {"name": "토스", "ats": "toss",
  ],
  "filters": {"include": ["백엔드"]}
EOF
