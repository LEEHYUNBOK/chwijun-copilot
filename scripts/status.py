#!/usr/bin/env python3
"""위키 상태 대시보드 — 채점 결과 검증·저장, 변경 감지, 채움률 계산, HTML 생성.

LLM(status 스킬)은 칸별 판정만 낸다. 퍼센트는 이 스크립트가 계산한다.
사용: status.py scan <wiki> | record <wiki> <문서> <result.md>... | render <wiki> | --selftest
record에 결과 파일을 여러 개 주면 칸별 다수결로 저장한다(재채점용).
"""
import hashlib
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

SCORE = {"충": 1.0, "부": 0.5, "비": 0.0}
CELLS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
TYPES = ("프로젝트", "장애", "조사", "제외")
WORD = {"충분함": "충", "부족함": "부", "비어 있음": "비", "한계 명시": "한"}
LINE = re.compile(r"^판정:\s*(.+?)\s*=\s*([충부비한](?:\s*,\s*[충부비한]){6})\s*$")
KIND = re.compile(r"^유형:\s*(.+?)\s*=\s*(\S+)\s*$")
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


def doc_key(path, wiki):
    return unicodedata.normalize("NFC", path.relative_to(wiki).as_posix())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(wiki):
    f = wiki / ".status" / "scores.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"rubric": "v4", "docs": {}}


def save(wiki, data):
    d = wiki / ".status"
    d.mkdir(exist_ok=True)
    (d / "scores.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def wiki_docs(wiki):
    return {doc_key(p, wiki): p for p in wiki.rglob("*.md")
            if not any(part.startswith(".") for part in p.relative_to(wiki).parts)}


def scan(wiki):
    stored = load(wiki)["docs"]
    files = wiki_docs(wiki)
    changed = sorted(k for k, p in files.items() if stored.get(k, {}).get("sha256") != sha(p))
    return {"changed": changed,
            "unchanged": sorted(k for k in files if k not in changed),
            "removed": sorted(k for k in stored if k not in files)}


IDENT = re.compile(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+|[A-Z]{2,}-[0-9]+")
# \b는 한글 조사 앞에서 경계가 안 생긴다("OrderService는") — 영숫자 기준 lookaround로 끊는다
CODE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]+(?:Service|Controller|Mapper|Repository|Dao|Dto|Entity|Handler|Impl|Utils?|Config|Manager|Client|Job)|(?:[A-Z][a-z0-9]+){3,})(?![A-Za-z0-9])")
TICKED = re.compile(r"`([A-Za-z][A-Za-z0-9_.]+)`")
NAME = re.compile(r"(?:담당자?|팀장|PM)\s*[:：]?\s+([가-힣]{2,4})(?![가-힣])")
ALLOW = {"MySQL", "jMeter", "OpenTelemetry", "GitHub", "GitLab", "PostgreSQL", "MariaDB"}
NOT_NAME = ("팀원", "외주", "벤더", "업체", "인프라", "운영", "팀장", "담당")
PARTICLE = tuple("는를을의별들에도만로")


def leaks(source, output):
    names = {n for n in NAME.findall(source) if not n.startswith(NOT_NAME) and not n.endswith(PARTICLE)}
    tokens = (set(IDENT.findall(source)) | set(CODE.findall(source)) | set(TICKED.findall(source))) - ALLOW
    return sorted(t for t in tokens | names if t in output)


def majority(entries):
    """채점자 여럿의 판정을 칸별 다수결로 합친다. 다수가 없으면 가장 낮은 판정(비>부>충>한 순)을 쓴다."""
    if len(entries) == 1:
        return dict(entries[0], raters=1)
    kinds = [e["type"] for e in entries]
    kind = max(set(kinds), key=kinds.count)
    if kinds.count(kind) * 2 <= len(kinds):
        raise ValueError(f"채점자들의 유형이 갈림: {', '.join(kinds)}")
    same = [e for e in entries if e["type"] == kind]
    if kind == "제외":
        return dict(same[0], raters=len(entries))
    cells, rows = [], []
    for i in range(len(CELLS)):
        votes = [e["cells"][i] for e in same]
        top = max(set(votes), key=votes.count)
        # ponytail: 세 갈래면 보수적으로 가장 낮은 판정 — 13 재테스트에선 세 갈래가 0건이었다
        pick = top if votes.count(top) * 2 > len(votes) else next(v for v in "비부충한" if v in votes)
        cells.append(pick)
        rows.append(next(e["rows"][i] for e in same if e["cells"][i] == pick))
    return {"type": kind, "cells": cells, "rows": rows, "raters": len(entries)}


def record(wiki, doc, *result_paths):
    files = wiki_docs(wiki)
    key = unicodedata.normalize("NFC", doc)
    if key not in files:
        raise ValueError(f"위키에 없는 문서: {doc}")
    source = files[key].read_text(encoding="utf-8")
    entries = []
    for path in result_paths:
        text = Path(path).read_text(encoding="utf-8")
        entries.append(parse_result(text))
        # 서브에이전트 결과 파일이 뒤바뀌면 남의 점수가 저장된다 — 유형 줄 이름을 문서 키와 대조
        name = unicodedata.normalize("NFC", next(m.group(1) for m in map(KIND.match, map(str.strip, text.splitlines())) if m))
        if name not in (key, key.removesuffix(".md"), Path(key).stem):
            raise ValueError(f"결과 파일의 문서 이름 '{name}'이 {key}와 다름")
        found = leaks(source, text)
        if found:
            raise ValueError(f"출력에 원문 식별자: {', '.join(found)}")
    entry = majority(entries)
    entry.update(sha256=sha(files[key]), scored_at=date.today().isoformat())
    data = load(wiki)
    data["docs"][key] = entry
    save(wiki, data)
    return entry


CELL_NAMES = ("어떤 문제였나", "내가 한 일", "문제 해결 방식", "측정 방식 정의", "결과 KPI", "왜 대단한가", "데이터 문해력")
STATE = {"충": "ok", "부": "warn", "비": "bad", "한": "na"}

PAGE = """<!doctype html>
<html lang="ko" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>위키 채움 상태</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<style>
/* 토스(TDS) 문법: 회색 바닥 + 흰 카드, 테두리·그림자 없음, 파랑 하나 */
:root{--ground:#F2F4F6;--surface:#FFFFFF;--ink:#191F28;--muted:#6B7684;--faint:#8B95A1;
--fill:#F2F4F6;--fill2:#E5E8EB;--accent:#3182F6;--accent-soft:#E8F3FF;
--rec:#F04452;--rec-soft:#FDEDEE;--gold:#A66C00;--gold-soft:#FFF6DE}
:root[data-theme="dark"]{--ground:#111114;--surface:#1E1E23;--ink:#ECECEE;--muted:#9B9BA3;--faint:#6E6E76;
--fill:#2A2A31;--fill2:#37373F;--accent:#4593FC;--accent-soft:#1E3352;
--rec:#F2757F;--rec-soft:#3A2226;--gold:#E0A94E;--gold-soft:#2E2718}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);word-break:keep-all;
font:400 15px/1.65 'Pretendard Variable',Pretendard,-apple-system,'Apple SD Gothic Neo',system-ui,sans-serif}
main{max-width:880px;margin:0 auto;padding:32px 16px 64px;display:grid;gap:16px}
header{display:flex;justify-content:space-between;align-items:center;gap:8px}
h1{font-size:22px;font-weight:700;margin:0}
h2{font-size:17px;font-weight:700;margin:0 0 16px}
.card{background:var(--surface);border-radius:20px;padding:28px 24px}
button{font:inherit;font-size:13px;font-weight:600;border:none;border-radius:12px;padding:8px 16px;cursor:pointer;
background:var(--fill);color:var(--ink);transition:background 180ms ease-out,transform 120ms ease-out}
button:hover{background:var(--fill2)}button:active{transform:scale(.97)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.hero{display:flex;flex-wrap:wrap;align-items:flex-end;gap:8px 24px}
.big{font-size:32px;font-weight:700;line-height:1.2;color:var(--accent)}
.label{font-size:13px;color:var(--muted)}
.stats{display:flex;flex-wrap:wrap;gap:8px}
.pill{border-radius:100px;padding:4px 12px;font-size:13px;font-weight:600;background:var(--fill);color:var(--muted)}
.group{font-size:13px;font-weight:600;color:var(--muted);margin:16px 0 8px}.group:first-of-type{margin-top:0}
.docs{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}
a.doc{display:block;text-decoration:none;color:inherit;background:var(--fill);border-radius:14px;padding:16px;
transition:background 180ms ease-out,transform 120ms ease-out}
a.doc:hover{background:var(--fill2)}a.doc:active{transform:scale(.97)}
.doc b{display:block;font-size:15px;font-weight:600}
.doc span{display:block;font-size:13px;color:var(--muted);overflow-wrap:anywhere}
.doc.missing{background:var(--rec-soft)}.doc.missing span{color:var(--rec)}
.doc.skill{background:var(--fill);border-radius:14px;padding:16px}.doc.skill p{margin:6px 0 0;font-size:14px}
.doc.skill .chip{display:inline-block;margin-bottom:6px}
.sk-hero{margin:20px 0 8px}.skrow{display:grid;gap:6px;padding:10px 0}.skrow+.group{margin-top:24px}
.list{display:grid;gap:8px}
details{background:var(--surface);border-radius:20px}
summary{list-style:none;cursor:pointer;padding:20px 24px;display:grid;gap:8px;border-radius:20px}
summary::-webkit-details-marker{display:none}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:4px 12px}
.name{font-weight:600;flex:1 1 240px;overflow-wrap:anywhere}
.pct{font-weight:700}
.bar{height:8px;border-radius:100px;background:var(--fill2);overflow:hidden}
.bar i{display:block;height:100%;border-radius:100px;background:var(--accent)}
.meta{font-size:13px;color:var(--faint)}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.chip{border-radius:100px;padding:0 8px;font-size:13px;font-weight:600}
.ok{background:var(--accent-soft);color:var(--accent)}.warn{background:var(--gold-soft);color:var(--gold)}
.bad{background:var(--rec-soft);color:var(--rec)}.na{background:var(--fill);color:var(--faint)}
.badge{border-radius:100px;padding:0 8px;font-size:13px;font-weight:600;background:var(--gold-soft);color:var(--gold)}
.gaps{padding:0 24px 24px;display:grid;gap:8px}
.gap{background:var(--fill);border-radius:14px;padding:16px}
.gap p{margin:0}.gap .t{font-weight:600}.why{color:var(--muted);font-size:13px;margin:4px 0 8px!important}
.cmd{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
.cmd button{background:var(--accent);color:#FFFFFF}.cmd button:hover{background:var(--accent)}
code{background:var(--surface);border-radius:8px;padding:4px 8px;font-size:13px;overflow-wrap:anywhere}
.empty{color:var(--muted);margin:0}
.legend{font-size:13px;color:var(--muted);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.excl{color:var(--muted);font-size:13px;margin:0;padding-left:16px}
</style></head><body><main>
<header><h1>위키를 얼마나 채웠는지 볼게요</h1><button id="theme" type="button">다크 모드</button></header>
__BODY__
</main><script>
(function(){var root=document.documentElement,btn=document.getElementById('theme');
try{var s=localStorage.getItem('status-theme');if(s==='dark'||s==='light')root.setAttribute('data-theme',s);}catch(e){}
function label(){btn.textContent=root.getAttribute('data-theme')==='dark'?'라이트 모드':'다크 모드';}
label();btn.addEventListener('click',function(){var n=root.getAttribute('data-theme')==='dark'?'light':'dark';
root.setAttribute('data-theme',n);try{localStorage.setItem('status-theme',n);}catch(e){}label();});
document.querySelectorAll('button[data-cmd]').forEach(function(b){b.addEventListener('click',function(){
var c=b.getAttribute('data-cmd'),show=function(){b.nextElementSibling.hidden=false;};
if(navigator.clipboard){navigator.clipboard.writeText(c).then(function(){b.textContent='복사했어요';},show);}else{show();}});});})();
</script></body></html>
"""


def render_docs(wiki):
    """<wiki>/.status/docs.json의 서류 목록을 카드로. [{"group","label","path"}], 상대 경로는 위키 기준"""
    f = wiki / ".status" / "docs.json"
    if not f.exists():
        return ""
    try:
        return _docs_cards(wiki, json.loads(f.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError, AttributeError) as err:
        return (f'<section class="card"><h2>내 서류</h2><p class="empty">docs.json을 읽을 수 없어요: '
                f'{html.escape(repr(err))}. [{{"group", "label", "path"}}] 형식인지 확인해 주세요</p></section>')


def _docs_cards(wiki, items):
    esc, out, last = html.escape, ['<section class="card"><h2>내 서류</h2>'], None
    for d in items:
        if d.get("group") != last:
            if last is not None:
                out.append("</div>")
            last = d.get("group")
            out.append(f'<div class="group">{esc(last or "")}</div><div class="docs">')
        p = (wiki / d["path"]).resolve()
        if p.exists():
            out.append(f'<a class="doc" href="{esc(p.as_uri())}" target="_blank" rel="noopener">'
                       f'<b>{esc(d["label"])}</b><span>{esc(p.name)}</span></a>')
        else:
            out.append(f'<div class="doc missing"><b>{esc(d["label"])}</b><span>파일을 찾을 수 없어요 · {esc(d["path"])}</span></div>')
    return "".join(out) + "</div></section>" if len(out) > 1 else ""


SKILL_STATE = {"ok": "근거 확인", "warn": "본인 진술", "bad": "빈칸"}
CHECKS = ("기록", "수치", "주도", "완결")  # 근거 기록 있음 · 수치 있음 · 본인이 했다는 근거 · 빈 곳 없음


def render_skills(wiki):
    """<wiki>/.status/skills.json의 역량 카드. [{"group","axis","name","card","proof","state":ok|warn|bad,"gap"?,"path"?}]"""
    f = wiki / ".status" / "skills.json"
    if not f.exists():
        return ""
    esc = html.escape
    try:
        items = json.loads(f.read_text(encoding="utf-8"))
        n = {s: sum(d["state"] == s for d in items) for s in SKILL_STATE}
        out = [f'<section class="card"><h2>내 역량 {len(items)}개</h2><div class="chips">'
               + "".join(f'<span class="chip {s}">{SKILL_STATE[s]} {n[s]}</span>' for s in SKILL_STATE) + "</div>"]
        scored = [(d, sum(map(bool, d["checks"])) / len(CHECKS) * 100) for d in items if "checks" in d]
        if scored:
            avg = sum(p for _, p in scored) / len(scored)
            out.append(f'<div class="hero sk-hero"><div><div class="label">평균 근거 점수</div><div class="big">{avg:.0f}점</div></div>'
                       f'<p class="meta">카드마다 {" · ".join(CHECKS)} 4가지를 확인해 하나당 25점</p></div>')
            for d, p in scored:
                ticks = "".join(f'<span class="chip {"ok" if v else "na"}">{"✓" if v else "✗"} {c}</span>'
                                for c, v in zip(CHECKS, d["checks"]))
                tip = esc(", ".join(f"{c} {'있음' if v else '없음'}" for c, v in zip(CHECKS, d["checks"])))
                out.append(f'<div class="skrow" title="{tip}"><div class="row"><span class="name">{esc(d["axis"])} · {esc(d["name"])}</span>'
                           f'<span class="pct">{p:.0f}점</span></div><div class="bar"><i style="width:{p:.0f}%"></i></div>'
                           f'<div class="chips">{ticks}</div></div>')
        last = None
        for d in items:
            if d.get("group") != last:
                out.append(("</div>" if last is not None else "") + f'<div class="group">{esc(d.get("group") or "")}</div><div class="docs">')
                last = d.get("group")
            p = (wiki / d["path"]).resolve() if d.get("path") else None
            tag, href = ("a", f' href="{esc(p.as_uri())}" target="_blank" rel="noopener"') if p and p.exists() else ("div", "")
            gap = f'<p class="why">빈 곳: {esc(d["gap"])}</p>' if d.get("gap") else ""
            out.append(f'<{tag} class="doc skill"{href}><span class="chip {d["state"]}">{SKILL_STATE[d["state"]]}</span>'
                       f'<span>{esc(d["axis"])}</span><b>{esc(d["name"])}</b><p>{esc(d["card"])}</p>'
                       f'<p class="why">{esc(d["proof"])}</p>{gap}</{tag}>')
        return "".join(out) + "</div></section>"
    except (ValueError, KeyError, TypeError, AttributeError) as err:
        return (f'<section class="card"><h2>내 역량</h2><p class="empty">skills.json을 읽을 수 없어요: '
                f'{esc(repr(err))}. [{{"group","axis","name","card","proof","state"}}] 형식인지 확인해 주세요</p></section>')


def render(wiki):
    esc = html.escape
    files = wiki_docs(wiki)
    scored, excluded = [], []
    for key, e in load(wiki)["docs"].items():
        if key not in files:
            continue
        stale = sha(files[key]) != e.get("sha256")
        (excluded if e["type"] == "제외" else scored).append((key, e, stale))
    pct = lambda e: (lambda s, n: s / n * 100 if n else None)(*rate(e["cells"]))
    scored.sort(key=lambda t: (pct(t[1]) is None, pct(t[1]) or 0, t[0]))
    vals = [p for p in (pct(e) for _, e, _ in scored) if p is not None]
    out = []
    if not scored and not excluded:
        out.append('<section class="card"><p class="empty">아직 채점한 문서가 없어요. '
                   '/chwijun-copilot:status 를 실행해 주세요</p></section>')
    else:
        avg = f"{sum(vals) / len(vals):.1f}%" if vals else "—"
        stale_n = sum(s for *_, s in scored + excluded)
        out.append(f'<section class="card hero"><div><div class="label">평균 채움률</div><div class="big">{avg}</div></div>'
                   f'<div class="stats"><span class="pill">채점 문서 {len(scored)}개</span>'
                   f'<span class="pill">채점 후 수정됨 {stale_n}개</span><span class="pill">제외 {len(excluded)}개</span></div></section>')
    out.append(render_skills(wiki))
    out.append(render_docs(wiki))
    if scored:
        out.append('<section class="list"><div class="legend"><span>칸 판정</span><span class="chip ok">충분함</span>'
                   '<span class="chip warn">부족함</span><span class="chip bad">비어 있음</span>'
                   '<span class="chip na">한계 명시</span><span>· 낮은 순</span></div>')
    for key, e, stale in scored:
        chips = "".join(f'<span class="chip {STATE[c]}" title="{cell} {CELL_NAMES[i]}">{cell}</span>'
                        for i, (cell, c) in enumerate(zip(CELLS, e["cells"])))
        badge = '<span class="badge">채점 후 수정됨</span>' if stale else ""
        p = pct(e)
        gaps = []
        for i, r in enumerate(e["rows"]):
            if e["cells"][i] not in "부비":
                continue
            cmd = esc(f"/chwijun-copilot:status {key} {r['cell']}")
            gaps.append(f'<div class="gap"><p class="t">{r["cell"]} {CELL_NAMES[i]} · {esc(r["verdict"])}</p>'
                        f'<p class="why">{esc(r["why"])}</p><p>{esc(r["ask"])}</p>'
                        f'<div class="cmd"><button type="button" data-cmd="{cmd}">명령어 복사하기</button>'
                        f'<code hidden>{cmd}</code></div></div>')
        out.append(f'<details><summary><div class="row"><span class="name">{esc(key)}</span>{badge}'
                   f'<span class="pct">{"—" if p is None else f"{p:.0f}%"}</span></div>'
                   f'<div class="bar"><i style="width:{p or 0:.1f}%"></i></div>'
                   f'<div class="row"><span class="chips">{chips}</span>'
                   f'<span class="meta">{esc(e["type"])} · {esc(fill_text(e["cells"]))} · 채점 {esc(e.get("scored_at", ""))}</span></div>'
                   f'</summary><div class="gaps">{"".join(gaps) or "<p>부족한 칸이 없어요.</p>"}</div></details>')
    if scored:
        out.append("</section>")
    if excluded:
        out.append(f'<section class="card"><h2>채점에서 뺀 문서 {len(excluded)}개</h2><ul class="excl">'
                   + "".join(f'<li>{esc(k)} — {esc(e.get("reason", ""))}</li>' for k, e, _ in excluded) + "</ul></section>")
    path = wiki / ".status" / "index.html"
    path.parent.mkdir(exist_ok=True)
    path.write_text(PAGE.replace("__BODY__", "\n".join(out)), encoding="utf-8")
    return path


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
    assert leaks("백엔드를 담당한다", "개발을 한다") == []
    assert leaks("담당 홍길동 확인", "홍길동에게 물었나?") == ["홍길동"]
    assert leaks("담당 팀원B", "담당 팀원에게") == []
    assert leaks("담당 주체별로 나눴다. 담당 건수는 3건", "주체별 정리, 건수는 적다") == []
    assert leaks("AWS CodeDeploy와 CloudWatch로 배포", "CodeDeploy 배포 실패 시 CloudWatch 경보") == []
    assert leaks("원인은 `menuTree`와 OrderService", "menuTree를 고쳤나? OrderService는?") == ["OrderService", "menuTree"]
    assert leaks("CustomServletWrappingFilter와 EnbldEvlTimeList", "CustomServletWrappingFilter·EnbldEvlTimeList") == ["CustomServletWrappingFilter", "EnbldEvlTimeList"]
    assert leaks("OrderService는 느렸다", "OrderService") == ["OrderService"]
    assert leaks("담당자: 홍길동", "홍길동이 처리") == ["홍길동"]
    assert leaks("담당 팀장에게 보고", "팀장에게 물었다") == []
    assert rate(list("부부충부충충충")) == (5.5, 7)
    assert rate(list("충부충부한충부")) == (4.5, 6)
    assert fill_text(list("충부부부부부부")) == "57.1% (점수 합 4.0 / 분모 7, 한계 명시 0칸)"
    assert fill_text(list("한한한한한한한")) == "판정 불가 (전 칸 한계 명시)"
    r = parse_result(SAMPLE_OK)
    assert r["type"] == "조사" and r["cells"] == list("충부충부비충충")
    assert [x["cell"] for x in r["rows"]] == list(CELLS)
    assert parse_result(SAMPLE_EXCLUDED) == {"type": "제외", "cells": [], "rows": [], "reason": "목차 문서"}
    a, b = parse_result(SAMPLE_OK), parse_result(SAMPLE_OK.replace("충,부,충,부,비,충,충", "부,부,충,부,비,충,충")
                                                  .replace("| C1 | 충분함 | 「배경」 | - | - |", "| C1 | 부족함 | 「배경」 | 영향 없음 | 영향은? |"))
    c = parse_result(SAMPLE_OK.replace("충,부,충,부,비,충,충", "비,부,충,부,비,충,한")
                     .replace("| C1 | 충분함 | 「배경」 | - | - |", "| C1 | 비어 있음 | 「배경」 | 없음 | 무엇이 문제였나? |")
                     .replace("| C7 | 충분함 | 「표현 기준」 | - | - |", "| C7 | 한계 명시 | 「주의」 | - | - |"))
    m = majority([a, b, c])
    assert m["cells"] == list("비부충부비충충"), m["cells"]  # C1 세 갈래 → 가장 낮은 비, C7 2:1 → 충
    assert m["rows"][0]["ask"] == "무엇이 문제였나?" and m["raters"] == 3
    assert majority([a])["cells"] == a["cells"]
    for bad, word in [(SAMPLE_NO_VERDICT, "판정 줄"), (SAMPLE_SIX_CELLS, "7칸"),
                      (SAMPLE_NO_QUESTION, "C4"), (SAMPLE_BAD_TYPE, "유형")]:
        try:
            parse_result(bad)
            assert False, word
        except ValueError as e:
            assert word in str(e), (word, str(e))
    print("selftest OK")


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    if len(argv) == 2 and argv[0] == "scan":
        return print(json.dumps(scan(Path(argv[1])), ensure_ascii=False))
    if len(argv) >= 4 and argv[0] == "record":
        try:
            e = record(Path(argv[1]), argv[2], *argv[3:])
        except (ValueError, OSError) as err:
            print(f"기록 거부: {err}", file=sys.stderr)
            sys.exit(2)
        label = f"제외 — {e['reason']}" if e["type"] == "제외" else fill_text(e["cells"])
        return print(f"기록: {unicodedata.normalize('NFC', argv[2])} {label}")
    if len(argv) == 2 and argv[0] == "render":
        return print(render(Path(argv[1])))
    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
