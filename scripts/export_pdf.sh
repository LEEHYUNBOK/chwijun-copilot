#!/bin/bash
# html → pdf 추출 (Chrome/Chromium headless). 사용: export_pdf.sh <html파일> [출력.pdf]
# 종료 코드: 0=성공(페이지 수 출력), 2=브라우저 없음(HTML 수동 인쇄 안내), 1=그 외 실패
set -u
SRC="${1:?사용법: export_pdf.sh <html파일> [출력.pdf]}"
DST="${2:-${SRC%.html}.pdf}"

find_chrome() {
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "/Applications/Chromium.app/Contents/MacOS/Chromium" \
           "$(command -v google-chrome 2>/dev/null)" \
           "$(command -v chromium 2>/dev/null)" \
           "$(command -v chromium-browser 2>/dev/null)"; do
    [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return 0; }
  done
  return 1
}

CH="$(find_chrome)" || {
  echo "Chrome/Chromium 없음 — PDF 자동 추출 불가." >&2
  echo "대안: ${SRC}를 브라우저로 열어 인쇄(⌘P/Ctrl+P) → 'PDF로 저장' (머리글·바닥글 끄기)." >&2
  exit 2
}

ABS="$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")"
"$CH" --headless --disable-gpu --no-pdf-header-footer \
      --print-to-pdf="$DST" "file://$ABS" 2>/dev/null || { echo "추출 실패" >&2; exit 1; }

PAGES=$(python3 -c "
import re,sys
d=open(sys.argv[1],'rb').read()
print(len(re.findall(rb'/Type\s*/Page[^s]', d)))" "$DST")
echo "$(basename "$DST") 생성 — ${PAGES}페이지"

# 플레이스홀더 잔존 검사: {{...}}가 PDF 텍스트에 남아 있으면 미완성
if command -v pdftotext >/dev/null 2>&1; then
  LEFT=$(pdftotext "$DST" - 2>/dev/null | grep -c "{{" || true)
  [ "$LEFT" -gt 0 ] && echo "경고: 플레이스홀더 {{}} ${LEFT}건 잔존 — 채우지 않은 칸이 있다" >&2
fi
exit 0
