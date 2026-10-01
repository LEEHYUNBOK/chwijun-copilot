#!/bin/bash
# 스크립트 3종 스모크 테스트. 전부 통과하면 "ALL PASS".
set -u
cd "$(dirname "$0")"
fail=0

python3 -m py_compile fetch_jd.py track_add.py check_voice.py || fail=1

# check_voice: 위반 픽스처 → exit 1, 검출 3종
cat > /tmp/cv_bad.md <<'EOF'
또한, 데이터를 정제하고, 모델을 검증했다. 많은 것을 배웠다.
EOF
out=$(python3 check_voice.py /tmp/cv_bad.md); rc=$?
[ $rc -eq 1 ] || { echo "FAIL: bad fixture rc=$rc"; fail=1; }
echo "$out" | grep -q '접속사' || { echo "FAIL: 접속사 미검출"; fail=1; }
echo "$out" | grep -q '쉼표' || { echo "FAIL: 쉼표 미검출"; fail=1; }
echo "$out" | grep -q '감정문장' || { echo "FAIL: 감정문장 미검출"; fail=1; }

# check_voice: 깨끗한 픽스처 + 금지어 파일 없음 → exit 0
echo "데이터를 정제하고 모델을 검증했다." > /tmp/cv_ok.md
python3 check_voice.py --banned /tmp/없는파일.txt /tmp/cv_ok.md >/dev/null
[ $? -eq 0 ] || { echo "FAIL: clean fixture"; fail=1; }

# check_voice: --banned만 주고 파일 누락 → exit 2 (트레이스백 아님)
python3 check_voice.py --banned 2>/dev/null
[ $? -eq 2 ] || { echo "FAIL: --banned 단독이 exit 2가 아님"; fail=1; }

# check_voice: 대상 파일이 없음 → exit 2 (트레이스백 아님)
python3 check_voice.py /tmp/cv_없는파일_$$.md >/dev/null 2>&1
[ $? -eq 2 ] || { echo "FAIL: 없는 대상 파일이 exit 2가 아님"; fail=1; }

# track_add: --ds 누락 → exit 2
python3 track_add.py --title t --company c --url u >/dev/null 2>&1
[ $? -eq 2 ] || { echo "FAIL: track_add --ds 누락이 exit 2가 아님"; fail=1; }

# track_add: 필수 속성 빠진 스키마 → 어떤 속성이 없는지 말하고 SystemExit
python3 -c "
import sys, track_add
try:
    track_add.require_props({'이름': {}, '상태': {}})
except SystemExit as e:
    msg = str(e)
    sys.exit(0 if ('회사' in msg and '지원 링크' in msg) else 1)
sys.exit(1)" || { echo "FAIL: require_props가 누락 속성을 안내하지 않음"; fail=1; }

[ $fail -eq 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }
