#!/usr/bin/env python3
"""채점자 결과의 `판정: <문서> = 충,부,비,한,...` 줄을 모아 채움률·일치율·편차를 계산한다.

사용: python3 집계.py <채점자1 result.md> <채점자2 result.md> ...
판정 기호: 충=충분함(1) 부=부족함(0.5) 비=비어 있음(0) 한=한계 명시(분모 제외)
"""
import re
import sys
from collections import Counter

SCORE = {"충": 1.0, "부": 0.5, "비": 0.0}
LINE = re.compile(r"^판정:\s*(\S+)\s*=\s*([충부비한](?:\s*,\s*[충부비한]){6})\s*$")


def rate(cells):
    scored = [SCORE[c] for c in cells if c != "한"]
    return sum(scored), len(scored)


def parse(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = LINE.match(line.strip())
        if m:
            out[m.group(1)] = [c.strip() for c in m.group(2).split(",")]
    return out


def majority(column):
    top, n = Counter(column).most_common(1)[0]
    return top if n >= 2 else None


def main(paths):
    raters = [parse(p) for p in paths]
    docs = sorted(set().union(*raters))
    full = maj = total = 0
    for d in docs:
        rows = [r[d] for r in raters if d in r]
        if len(rows) != len(raters):
            print(f"{d}: 판정 줄이 없는 채점자가 있다 — 건너뜀")
            continue
        cols = list(zip(*rows))
        m = [majority(c) for c in cols]
        full += sum(len(set(c)) == 1 for c in cols)
        maj += sum(x is not None for x in m)
        total += 7
        pct = []
        for i, r in enumerate(rows, 1):
            s, n = rate(r)
            pct.append(s / n * 100)
            print(f"{d} 채점자{i}: {','.join(r)}  {s}/{n} = {s/n*100:.1f}%")
        if None not in m:
            s, n = rate(m)
            print(f"{d} 다수결 : {','.join(m)}  {s}/{n} = {s/n*100:.1f}%  편차 {max(pct)-min(pct):.1f}%p")
        diff = [f"C{i+1}" for i, c in enumerate(cols) if len(set(c)) > 1]
        print(f"{d} 불일치 칸: {', '.join(diff) or '없음'}\n")
    print(f"전원 일치 {full}/{total}, 다수결 {maj}/{total}")


def demo():
    # 07에서 손으로 틀렸던 세 값을 고정 검사한다
    assert rate(list("부부충부충충충")) == (5.5, 7)
    assert rate(list("충부충충부충충")) == (6.0, 7)
    assert rate(list("충부충부한충부")) == (4.5, 6)
    assert rate(list("충부부부한충부")) == (4.0, 6)
    assert majority(("부", "비", "비")) == "비" and majority(("충", "부", "비")) is None
    assert LINE.match("판정: d3 = 충,부,부,부,한,충,부")


if __name__ == "__main__":
    demo()
    main(sys.argv[1:]) if sys.argv[1:] else print("self-check OK")
