#!/usr/bin/env python3
"""문체 기계 검사 — 금지어·접속사·감정문장·연결어미 뒤 쉼표·대칭 대구.
사용법: python3 check_voice.py [--banned 금지어.txt] <md|html|txt>...
exit 0 = 전부 통과, 1 = 위반 있음."""
import re, sys

CONJ = re.compile(r'(또한|결론적으로|결과적으로|뿐만 아니라|나아가|이를 통해|따라서 |이러한 |마지막으로)')
EMO = re.compile(r'(많은 것을 배웠|값진 경험|책임감을 느꼈|최선을 다했|자신감을 얻었)')
COMMA = re.compile(r'[가-힣]+(하고|지만|면서|다면|아서|어서|라서|하며|이며|므로|는데|한데|더니|다가|려면|하면|니까),')
PARA = re.compile(r'(가 아니라|이 아니라)')

def load_banned(path):
    if not path:
        return []
    try:
        return [l.strip() for l in open(path, encoding='utf-8')
                if l.strip() and not l.startswith('#')]
    except FileNotFoundError:
        return []

def check(text, banned):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', text, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', text)
    probs = [f"금지어 '{b}'" for b in banned if b in body]
    probs += [f"접속사 '{m.group(1)}'" for m in CONJ.finditer(body)]
    probs += [f"감정문장 '{m.group(1)}…'" for m in EMO.finditer(body)]
    commas = COMMA.findall(body)
    if commas:
        probs.append(f"연결어미 뒤 쉼표 {len(commas)}건: {commas[:5]}")
    para = len(PARA.findall(body))
    if para > 2:
        probs.append(f"'~가 아니라' 대구 {para}회 (문서당 2회 상한)")
    return probs

def main(argv):
    banned_path = None
    if argv[:1] == ['--banned']:
        if len(argv) < 2:
            print(__doc__)
            return 2
        banned_path, argv = argv[1], argv[2:]
    if not argv:
        print(__doc__)
        return 2
    banned = load_banned(banned_path)
    fail = 0
    for p in argv:
        try:
            text = open(p, encoding='utf-8').read()
        except OSError as e:
            print(f"❌ {p}: 열 수 없음 ({e.strerror})")
            return 2
        probs = check(text, banned)
        print(('❌ ' if probs else '✅ ') + p.rsplit('/', 1)[-1])
        for x in probs:
            print('   - ' + x)
        fail += len(probs)
    return 1 if fail else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
