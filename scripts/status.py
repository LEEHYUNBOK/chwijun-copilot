#!/usr/bin/env python3
"""위키 상태 대시보드 — 채점 결과 검증·저장, 변경 감지, 채움률 계산, HTML 생성.

LLM(status 스킬)은 칸별 판정만 낸다. 퍼센트는 이 스크립트가 계산한다.
사용: status.py scan <wiki> | record <wiki> <문서> <result.md> | render <wiki> | --selftest
"""
import re
import sys

SCORE = {"충": 1.0, "부": 0.5, "비": 0.0}
CELLS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
TYPES = ("프로젝트", "장애", "조사", "제외")
WORD = {"충분함": "충", "부족함": "부", "비어 있음": "비", "한계 명시": "한"}
LINE = re.compile(r"^판정:\s*(\S+)\s*=\s*([충부비한](?:\s*,\s*[충부비한]){6})\s*$")
KIND = re.compile(r"^유형:\s*(\S+)\s*=\s*(\S+)\s*$")
ROW = re.compile(r"^\|\s*(C[1-7])\s*\|")


def rate(cells):
    scored = [SCORE[c] for c in cells if c != "한"]
    return sum(scored), len(scored)


def fill_text(cells):
    s, n = rate(cells)
    if n == 0:
        return "판정 불가 (전 칸 한계 명시)"
    return f"{s / n * 100:.1f}% (점수 합 {s} / 분모 {n}, 한계 명시 {7 - n}칸)"


def parse_result(text):
    lines = [l.strip() for l in text.splitlines()]
    kinds = [m.group(2) for m in map(KIND.match, lines) if m]
    if not kinds or kinds[0] not in TYPES:
        raise ValueError(f"유형 줄이 없거나 유형이 {'/'.join(TYPES)}가 아님")
    kind = kinds[0]
    if kind == "제외":
        reason = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("제외 이유:")), "")
        if not reason:
            raise ValueError("제외 유형인데 '제외 이유:' 줄이 없음")
        return {"type": kind, "cells": [], "rows": [], "reason": reason}
    verdicts = [l for l in lines if l.startswith("판정:")]
    if not verdicts:
        raise ValueError("판정 줄이 없음")
    m = LINE.match(verdicts[0])
    if not m:
        raise ValueError("판정 줄이 7칸(충·부·비·한)이 아님")
    cells = [c.strip() for c in m.group(2).split(",")]
    rows = {}
    for l in lines:
        if ROW.match(l):
            parts = [p.strip().strip("*").strip() for p in l.strip("|").split("|")]
            parts += [""] * (5 - len(parts))
            rows[parts[0]] = {"cell": parts[0], "verdict": parts[1], "where": parts[2],
                              "why": parts[3], "ask": parts[4]}
    out = []
    for cell, sym in zip(CELLS, cells):
        row = rows.get(cell)
        if row is None:
            raise ValueError(f"{cell}: 표에 행이 없음")
        if WORD.get(row["verdict"]) != sym:
            raise ValueError(f"{cell}: 표는 {row['verdict']}, 판정 줄은 {sym}")
        if sym in "부비" and (row["why"] in ("", "-") or row["ask"] in ("", "-")):
            raise ValueError(f"{cell}: {row['verdict']}인데 이유나 채우기 질문이 없음")
        out.append(row)
    return {"type": kind, "cells": cells, "rows": out}


SAMPLE_OK = """## doc
유형: doc = 조사
| 칸 | 판정 | 근거 위치 (절 이름) | 이유 | 채우기 질문 |
|---|---|---|---|---|
| C1 | 충분함 | 「배경」 | - | - |
| C2 | 부족함 | 「주의」 | 주어가 없다 | 직접 한 일은 무엇인가? |
| C3 | 충분함 | 「방법」 | - | - |
| C4 | 부족함 | 「규모」 | 조사 시점이 없다 | 언제 조사했나? |
| C5 | 비어 있음 | 문서 전체 | 전후 수치가 없다 | 결과가 어떻게 달라졌나? |
| C6 | 충분함 | 「배경」 | - | - |
| C7 | 충분함 | 「표현 기준」 | - | - |
판정: doc = 충,부,충,부,비,충,충
"""
SAMPLE_EXCLUDED = "## doc\n유형: doc = 제외\n제외 이유: 목차 문서\n"
SAMPLE_NO_VERDICT = SAMPLE_OK.replace("판정: doc = 충,부,충,부,비,충,충\n", "")
SAMPLE_SIX_CELLS = SAMPLE_OK.replace("충,부,충,부,비,충,충", "충,부,충,부,비,충")
SAMPLE_NO_QUESTION = SAMPLE_OK.replace("| 언제 조사했나? |", "| - |")
SAMPLE_BAD_TYPE = SAMPLE_OK.replace("유형: doc = 조사", "유형: doc = 기타")


def selftest():
    assert rate(list("부부충부충충충")) == (5.5, 7)
    assert rate(list("충부충부한충부")) == (4.5, 6)
    assert fill_text(list("충부부부부부부")) == "57.1% (점수 합 4.0 / 분모 7, 한계 명시 0칸)"
    assert fill_text(list("한한한한한한한")) == "판정 불가 (전 칸 한계 명시)"
    r = parse_result(SAMPLE_OK)
    assert r["type"] == "조사" and r["cells"] == list("충부충부비충충")
    assert [x["cell"] for x in r["rows"]] == list(CELLS)
    assert parse_result(SAMPLE_EXCLUDED) == {"type": "제외", "cells": [], "rows": [], "reason": "목차 문서"}
    for bad, word in [(SAMPLE_NO_VERDICT, "판정 줄"), (SAMPLE_SIX_CELLS, "7칸"),
                      (SAMPLE_NO_QUESTION, "C4"), (SAMPLE_BAD_TYPE, "유형")]:
        try:
            parse_result(bad)
            assert False, word
        except ValueError as e:
            assert word in str(e), (word, str(e))
    print("selftest OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
