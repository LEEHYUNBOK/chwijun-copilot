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
# 재채점 다수결: 결과 3개 중 2개가 C2 충분함이면 충분함, 하나라도 식별자가 새면 거부
mk "주문 상세 테이블 언급" "직접 한 일은?"; cp "$W/r.md" "$W/r1.md"
sed -e 's/충,부,충,부,비,충,충/충,충,충,부,비,충,충/' -e 's/| C2 | 부족함 | 「주의」 | 주문 상세 테이블 언급 | 직접 한 일은? |/| C2 | 충분함 | 「주의」 | - | - |/' "$W/r1.md" > "$W/r2.md"; cp "$W/r2.md" "$W/r3.md"
out=$(python3 status.py record "$W" doc.md "$W/r1.md" "$W/r2.md" "$W/r3.md" 2>&1) \
  && python3 -c "import json,sys; d=json.load(open('$W/.status/scores.json'))['docs']['doc.md']; sys.exit(0 if d['cells'][1]=='충' and d['raters']==3 else 1)" \
  || { echo "FAIL: 재채점 다수결: $out"; fail=1; }
mk "order_item 테이블 언급" "직접 한 일은?"
err=$(python3 status.py record "$W" doc.md "$W/r2.md" "$W/r.md" "$W/r3.md" 2>&1); rc=$?
[ $rc -eq 2 ] && echo "$err" | grep -q order_item || { echo "FAIL: 다수결 중 식별자 유출 미검출 rc=$rc"; fail=1; }
echo x > "$W/other.md"; mk "주문 상세 테이블 언급" "직접 한 일은?"
err=$(python3 status.py record "$W" other.md "$W/r.md" 2>&1); rc=$?
[ $rc -eq 2 ] && echo "$err" | grep -q '문서 이름' || { echo "FAIL: 다른 문서 결과가 기록됨 rc=$rc: $err"; fail=1; }
echo x > "$W/a b.md"; sed 's/doc =/a b =/' "$W/r.md" > "$W/sp.md"
out=$(python3 status.py record "$W" "a b.md" "$W/sp.md" 2>&1) || { echo "FAIL: 공백 문서명 기록: $out"; fail=1; }
printf '## toc\n유형: toc = 제외\n제외 이유: 목차 문서\n' > "$W/ex.md"; echo "# 목차" > "$W/toc.md"
python3 status.py record "$W" toc.md "$W/ex.md" >/dev/null 2>&1 \
  && python3 -c "import json,sys; sys.exit(0 if json.load(open('$W/.status/scores.json'))['docs']['toc.md']['type']=='제외' else 1)" \
  || { echo "FAIL: record 제외 유형"; fail=1; }
rm -rf "$W"

# status render: 채움률 표기·수정됨 배지·삭제 문서·이스케이프·빈 상태
W=/tmp/st_ren_$$; rm -rf "$W"; mkdir -p "$W"
python3 status.py render "$W" >/dev/null && grep -q '아직 채점한 문서가 없어요' "$W/.status/index.html" \
  || { echo "FAIL: render 빈 상태"; fail=1; }
grep -q '내 서류' "$W/.status/index.html" && { echo "FAIL: docs.json 없는데 서류 절이 나옴"; fail=1; }
# 서류 카드: docs.json의 상대 경로는 위키 기준, 없는 파일은 안내 문구
echo r > "$W/이력서.html"
printf '[{"group":"이력서","label":"공통 이력서","path":"이력서.html"},{"group":"포트폴리오","label":"<b>포폴</b>","path":"없음.pdf"}]' > "$W/.status/docs.json"
python3 status.py render "$W" >/dev/null; H="$W/.status/index.html"
grep -q '공통 이력서' "$H" && grep -qF "$(python3 -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().joinpath('이력서.html').as_uri())" "$W")" "$H" \
  || { echo "FAIL: 서류 카드 링크"; fail=1; }
grep -q '파일을 찾을 수 없어요' "$H" || { echo "FAIL: 없는 서류 안내"; fail=1; }
grep -q '<b>포폴' "$H" && { echo "FAIL: 서류 라벨 이스케이프"; fail=1; }
printf '{bad' > "$W/.status/docs.json"
python3 status.py render "$W" >/dev/null 2>&1 && grep -q 'docs.json을 읽을 수 없어요' "$H" || { echo "FAIL: 깨진 docs.json"; fail=1; }
rm "$W/.status/docs.json" "$W/이력서.html"
for d in a b c; do echo "$d" > "$W/$d.md"; python3 -c "import status; print(status.SAMPLE_OK.replace('doc =','$d =').replace('충,부,충,부,비,충,충','충,부,충,부,부,부,부').replace('| C5 | 비어 있음','| C5 | 부족함').replace('| C6 | 충분함 | 「배경」 | - | - |','| C6 | 부족함 | 「배경」 | 규모 없음 | 규모는? |').replace('| C7 | 충분함 | 「표현 기준」 | - | - |','| C7 | 부족함 | 「표현 기준」 | 결정 없음 | 결정은? |'))" > "$W/r.md"; python3 status.py record "$W" $d.md "$W/r.md" >/dev/null || { echo "FAIL: render 준비 record $d"; fail=1; }; done
echo changed > "$W/a.md"; rm "$W/b.md"
python3 - "$W" <<'PY'
import json, pathlib, sys
f = pathlib.Path(sys.argv[1]) / ".status/scores.json"; d = json.loads(f.read_text())
d["docs"]["<img src=x onerror=alert(1)>.md"] = dict(d["docs"]["c.md"]); f.write_text(json.dumps(d, ensure_ascii=False))
PY
echo x > "$W/<img src=x onerror=alert(1)>.md"
python3 status.py render "$W" >/dev/null; H="$W/.status/index.html"
exp=$(python3 -c "import status; print(status.fill_text(list('충부충부부부부')))")
grep -qF "$exp" "$H" || { echo "FAIL: render 채움률 표기 ($exp)"; fail=1; }
grep -q 'class="badge">채점 후 수정됨' "$H" || { echo "FAIL: render 수정됨 배지"; fail=1; }
grep -q '>b.md<' "$H" && { echo "FAIL: render 삭제 문서가 남음"; fail=1; }
grep -q '<img src=x onerror' "$H" && { echo "FAIL: render 이스케이프"; fail=1; }
grep -qF '&lt;img src=x onerror=alert(1)&gt;.md' "$H" || { echo "FAIL: render 이스케이프된 문서명이 없음"; fail=1; }
grep -q '>c.md<' "$H" || { echo "FAIL: render 남은 문서 c.md가 없음"; fail=1; }
grep -q '/chwijun-copilot:status c.md C2' "$H" || { echo "FAIL: render 복사 명령"; fail=1; }
rm -rf "$W"

[ $fail -eq 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }
