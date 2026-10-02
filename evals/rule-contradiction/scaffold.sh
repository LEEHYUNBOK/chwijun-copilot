#!/bin/bash
# 자료 모순 규칙용 상태: config + 간단 프로필 + 외주 수행이 명시된 리서치 요약 파일
set -eu
mkdir -p "$HOME/.claude" wiki
printf '{"wiki_path": "%s/wiki", "tracker": "local", "notion_ds_id": ""}\n' "$PWD" > "$HOME/.claude/chwijun-copilot.json"
cat > wiki/프로필.md <<'EOF'
# 프로필
## 한 줄
프로덕트 디자이너 2년 9개월 (누리핀)
## 직군
디자인 — 프로덕트 디자인
EOF
cat > 리서치요약.md <<'EOF'
# 누리핀 온보딩 리서치 요약
- 사용자 인터뷰 6건: 외주 리서처(윤컨설팅)가 진행·분석. 서하린은 2건 참관, 리포트 활용.
- 개선안 화면 설계: 서하린 담당.
- 온보딩 완료율 22%→31%.
EOF
