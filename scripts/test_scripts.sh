#!/bin/bash
# 스크립트 3종 스모크 테스트. 전부 통과하면 "ALL PASS".
set -u
cd "$(dirname "$0")"
fail=0

python3 -m py_compile fetch_jd.py track_add.py check_voice.py status.py || fail=1

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

# track_add: --list 아닌데 title/company/url 누락 → exit 2
python3 track_add.py --ds x --title t >/dev/null 2>&1
[ $? -eq 2 ] || { echo "FAIL: track_add 행 추가 필수 인자 누락이 exit 2가 아님"; fail=1; }

# track_add: 셀프테스트 (md_to_blocks + page_to_record)
python3 track_add.py --selftest >/dev/null || { echo "FAIL: track_add --selftest"; fail=1; }

# track_add: 필수 속성 빠진 스키마 → 어떤 속성이 없는지 말하고 SystemExit
python3 -c "
import sys, track_add
try:
    track_add.require_props({'이름': {}, '상태': {}})
except SystemExit as e:
    msg = str(e)
    sys.exit(0 if ('회사' in msg and '지원 링크' in msg) else 1)
sys.exit(1)" || { echo "FAIL: require_props가 누락 속성을 안내하지 않음"; fail=1; }

# status: 파서·채움률 셀프테스트
python3 status.py --selftest >/dev/null || { echo "FAIL: status --selftest"; fail=1; }

# status scan: 변경 감지·NFC 키·삭제 감지·숨김 폴더 제외
W=/tmp/st_wiki_$$; rm -rf "$W"; mkdir -p "$W/.status"
echo a > "$W/a.md"; echo b > "$W/b.md"; echo h > "$W/.status/x.md"
python3 -c "import unicodedata,pathlib; pathlib.Path('$W/'+unicodedata.normalize('NFD','문서.md')).write_text('x')"
out=$(python3 status.py scan "$W")
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d['changed']==['a.md','b.md','문서.md'] and d['removed']==[] else 1)" \
  || { echo "FAIL: scan 첫 실행 changed: $out"; fail=1; }
python3 - "$W" <<'PY'
import hashlib, json, pathlib, sys
w = pathlib.Path(sys.argv[1]); h = lambda s: hashlib.sha256(s.encode()).hexdigest()
docs = {"a.md": {"sha256": h("a\n")}, "문서.md": {"sha256": h("x")}, "gone.md": {"sha256": "0"}}
(w / ".status/scores.json").write_text(json.dumps({"rubric": "v4", "docs": docs}, ensure_ascii=False))
PY
out=$(python3 status.py scan "$W")
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d=={'changed':['b.md'],'unchanged':['a.md','문서.md'],'removed':['gone.md']} else 1)" \
  || { echo "FAIL: scan 해시 비교·NFC·removed: $out"; fail=1; }
rm -rf "$W"

# status record: 형식 검증·원문 식별자 유출 검사·저장
W=/tmp/st_rec_$$; rm -rf "$W"; mkdir -p "$W"
echo "원인은 order_item 테이블과 OrderService였다. ABC-12 참고. 담당 홍길동" > "$W/doc.md"
mk() { python3 -c "import status,sys; print(status.SAMPLE_OK.replace('주어가 없다', sys.argv[1]).replace('직접 한 일은 무엇인가?', sys.argv[2]))" "$1" "$2" > "$W/r.md"; }
mk "order_item 테이블 언급" "직접 한 일은?"
err=$(python3 status.py record "$W" doc.md "$W/r.md" 2>&1); rc=$?
[ $rc -eq 2 ] && echo "$err" | grep -q order_item || { echo "FAIL: record 식별자 유출 미검출 rc=$rc: $err"; fail=1; }
mk "주문 상세 테이블 언급" "홍길동과 무엇을 나눴나?"
err=$(python3 status.py record "$W" doc.md "$W/r.md" 2>&1); rc=$?
[ $rc -eq 2 ] && echo "$err" | grep -q 홍길동 || { echo "FAIL: record 이름 유출 미검출 rc=$rc: $err"; fail=1; }
mk "주문 상세 테이블 언급" "직접 한 일은?"
out=$(python3 status.py record "$W" doc.md "$W/r.md" 2>&1); rc=$?
[ $rc -eq 0 ] || { echo "FAIL: record 정상 입력 rc=$rc: $out"; fail=1; }
python3 -c "import json,sys,hashlib; d=json.load(open('$W/.status/scores.json'))['docs']['doc.md']; sys.exit(0 if d['cells']==list('충부충부비충충') and d['sha256']==hashlib.sha256(open('$W/doc.md','rb').read()).hexdigest() and d['type']=='조사' else 1)" \
  || { echo "FAIL: record 저장 내용"; fail=1; }
grep -v '^판정:' "$W/r.md" > "$W/bad.md"
err=$(python3 status.py record "$W" doc.md "$W/bad.md" 2>&1); rc=$?
[ $rc -eq 2 ] && ! echo "$err" | grep -q Traceback || { echo "FAIL: record 판정 줄 누락이 exit 2가 아님 rc=$rc"; fail=1; }
printf '## toc\n유형: toc = 제외\n제외 이유: 목차 문서\n' > "$W/ex.md"; echo "# 목차" > "$W/toc.md"
python3 status.py record "$W" toc.md "$W/ex.md" >/dev/null 2>&1 \
  && python3 -c "import json,sys; sys.exit(0 if json.load(open('$W/.status/scores.json'))['docs']['toc.md']['type']=='제외' else 1)" \
  || { echo "FAIL: record 제외 유형"; fail=1; }
rm -rf "$W"

[ $fail -eq 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }
