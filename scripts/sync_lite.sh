#!/bin/bash
# 라이트판(chatbot/) 동기화 — LLM 없이 실행되는 고정 절차
# 1) skills/resume-writing 정본 → chatbot/knowledge 복사
# 2) chwijun-copilot-lite.zip 재빌드
# 3) 공개 파일 전체에서 개인 흔적 검사 (발견 시 종료코드 1)
#
# 사용법: bash scripts/sync_lite.sh
set -euo pipefail
cd "$(dirname "$0")/.."

cp skills/resume-writing/rule.md chatbot/knowledge/rule.md
for f in ai-detection cover-letter interview-prep jd-tailoring kpi question-types; do
  cp "skills/resume-writing/references/$f.md" "chatbot/knowledge/$f.md"
done
echo "복사: rule.md + references 6종 → chatbot/knowledge/"

(cd chatbot && rm -f chwijun-copilot-lite.zip && zip -q chwijun-copilot-lite.zip SKILL.md README.md knowledge/*.md)
echo "zip 재빌드: chatbot/chwijun-copilot-lite.zip ($(unzip -l chatbot/chwijun-copilot-lite.zip | tail -1 | awk '{print $2}')개 파일)"

# 개인 흔적 검사 — 개인 스킬에서 이식할 때 일반화 누락을 잡는다
TRACES='이현복|이노아카|innoaca|면접왕|행복나래|youtube\.com|youtu\.be|hyunbok@'
if grep -rEn "$TRACES" skills chatbot/SKILL.md chatbot/knowledge README.md docs/index.html 2>/dev/null; then
  echo "✗ 개인 흔적 발견 — 위 줄을 일반화한 뒤 다시 실행" >&2
  exit 1
fi
echo "✓ 개인 흔적 없음"
