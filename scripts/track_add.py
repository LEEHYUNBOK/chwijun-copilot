#!/usr/bin/env python3
"""지원현황 Notion DB에 행 추가 — tracker가 notion일 때 스킬이 호출한다.

사용:
  python3 scripts/track_add.py --ds <data_source_id> --title <직무명> --company <회사명> \
      --url <공고URL> [--deadline YYYY-MM-DD] [--status 지원전] [--body 본문.md] [--dry-run]

토큰: 환경변수 NOTION_TOKEN 또는 ~/.config/notion/token 파일.
  (발급: notion.so/my-integrations → 내부 통합 생성 → 지원현황 DB에 연결)

DB 필수 속성: 이름(title) · 회사(multi_select) · 상태(select 또는 status) ·
지원 링크(url 또는 rich_text) · 마감일(date).

회사 규칙(옵션 100개 상한): 기존 옵션에 있는 회사만 multi_select로 넣고,
없으면 속성은 비우고 제목을 "[회사명] 직무명"으로 만든다. 옵션을 새로 만들지 않는다.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.notion.com/v1"


def token():
    t = os.environ.get("NOTION_TOKEN")
    if not t:
        p = os.path.expanduser("~/.config/notion/token")
        if os.path.exists(p):
            t = open(p).read().strip()
    if not t:
        sys.exit("NOTION_TOKEN 없음. notion.so/my-integrations에서 내부 통합을 만들어 "
                 "지원 현황 DB에 연결한 뒤, 토큰을 ~/.config/notion/token에 저장하거나 "
                 "export NOTION_TOKEN=... 로 넘겨라.")
    return t


def call(method, path, payload=None):
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {token()}",
                 "Notion-Version": "2025-09-03",
                 "Content-Type": "application/json"},
        method=method)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=20).read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Notion API {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def require_props(schema):
    """DB 스키마에 필수 속성이 다 있는지 검사. 없으면 뭘 만들어야 하는지 말하고 종료."""
    missing = [k for k in ("회사", "상태", "지원 링크") if k not in schema]
    if missing:
        sys.exit(f"지원현황 DB에 필수 속성이 없다: {' · '.join(missing)}. "
                 f"필요: 이름(title) · 회사(multi_select) · 상태(select/status) · "
                 f"지원 링크(url/rich_text) · 마감일(date). "
                 f"현재 속성: {', '.join(schema) or '(없음)'}")


def rich(text):
    """**굵게**와 [텍스트](URL) 링크만 처리하는 최소 마크다운 인라인 파서."""
    parts = []
    for i, seg in enumerate(re.split(r"\*\*", text)):
        # split 결과: [일반, 링크텍스트, URL, 일반, ...]
        bits = re.split(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", seg)
        for j in range(0, len(bits), 3):
            if bits[j]:
                parts.append({"type": "text", "text": {"content": bits[j]},
                              "annotations": {"bold": i % 2 == 1}})
            if j + 2 < len(bits):
                parts.append({"type": "text",
                              "text": {"content": bits[j + 1], "link": {"url": bits[j + 2]}},
                              "annotations": {"bold": i % 2 == 1}})
    return parts or [{"type": "text", "text": {"content": ""}}]


def md_to_blocks(md):
    blocks = []
    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if s == "---":
            blocks.append({"type": "divider", "divider": {}})
        elif s.startswith("#### "):  # Notion은 h4가 없다 — job-fit 본문의 #### 는 h3로
            blocks.append({"type": "heading_3", "heading_3": {"rich_text": rich(s[5:])}})
        elif s.startswith("### "):
            blocks.append({"type": "heading_3", "heading_3": {"rich_text": rich(s[4:])}})
        elif s.startswith("## "):
            blocks.append({"type": "heading_2", "heading_2": {"rich_text": rich(s[3:])}})
        elif s.startswith("> "):
            blocks.append({"type": "quote", "quote": {"rich_text": rich(s[2:])}})
        elif s.startswith("- "):
            blocks.append({"type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": rich(s[2:])}})
        else:
            blocks.append({"type": "paragraph", "paragraph": {"rich_text": rich(s)}})
    return blocks


def page_to_record(page):
    """Notion 페이지 JSON → 트래커 레코드. 상태(select/status)·링크(url/rich_text) 양쪽 분기."""
    p = page["properties"]

    def first(prop, key):
        items = prop.get(key) or []
        return items[0] if items else None

    status_prop = p.get("상태", {})
    status = (status_prop.get(status_prop.get("type")) or {}).get("name", "") \
        if status_prop.get("type") in ("select", "status") else ""
    link_prop = p.get("지원 링크", {})
    if link_prop.get("type") == "url":
        link = link_prop.get("url") or ""
    else:
        rt = first(link_prop, "rich_text")
        link = rt["plain_text"] if rt else ""
    title_rt = first(p.get("이름", {}), "title")
    company = first(p.get("회사", {}), "multi_select")
    date = p.get("마감일", {}).get("date") or {}
    return {
        "제목": title_rt["plain_text"] if title_rt else "",
        "회사": company["name"] if company else "",
        "상태": status,
        "링크": link,
        "마감일": date.get("start", "") or "",
        "등록일": page.get("created_time", "")[:10],
        "노션": page.get("url", ""),
    }


def list_rows(ds):
    """DB 전수 조회 (페이지네이션) → 레코드 리스트."""
    records, cursor = [], None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        resp = call("POST", f"/data_sources/{ds}/query", payload)
        records += [page_to_record(pg) for pg in resp.get("results", [])]
        if not resp.get("has_more"):
            return records
        cursor = resp["next_cursor"]


def selftest():
    b = md_to_blocks("## 적합도 상\n#### 겹치는 강점\n**레벨** 경력\n---\n- 강점 하나\n> 출처: api")
    assert [x["type"] for x in b] == ["heading_2", "heading_3", "paragraph", "divider",
                                     "bulleted_list_item", "quote"]
    assert b[1]["heading_3"]["rich_text"][0]["text"]["content"] == "겹치는 강점"
    assert b[2]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True
    r = rich("[출처] [공고](https://a.com/o/1) · 메일")
    assert [x["text"]["content"] for x in r] == ["[출처] ", "공고", " · 메일"]
    assert r[1]["text"]["link"]["url"] == "https://a.com/o/1"
    print("md_to_blocks ok")
    # --list: 페이지 JSON → 레코드 (url/rich_text·select/status 양쪽 분기)
    page_url_select = {
        "url": "https://notion.so/p1", "created_time": "2026-10-01T09:00:00.000Z",
        "properties": {
            "이름": {"type": "title", "title": [{"plain_text": "[다라] 백엔드"}]},
            "회사": {"type": "multi_select", "multi_select": [{"name": "다라커머스"}]},
            "상태": {"type": "select", "select": {"name": "지원 전"}},
            "지원 링크": {"type": "url", "url": "https://a.com/o/1"},
            "마감일": {"type": "date", "date": {"start": "2026-10-15"}},
        }}
    page_rt_status = {
        "url": "https://notion.so/p2", "created_time": "2026-09-20T09:00:00.000Z",
        "properties": {
            "이름": {"type": "title", "title": []},
            "회사": {"type": "multi_select", "multi_select": []},
            "상태": {"type": "status", "status": None},
            "지원 링크": {"type": "rich_text",
                       "rich_text": [{"plain_text": "https://b.com/o/2"}]},
            "마감일": {"type": "date", "date": None},
        }}
    r1 = page_to_record(page_url_select)
    assert r1 == {"제목": "[다라] 백엔드", "회사": "다라커머스", "상태": "지원 전",
                  "링크": "https://a.com/o/1", "마감일": "2026-10-15",
                  "등록일": "2026-10-01", "노션": "https://notion.so/p1"}
    r2 = page_to_record(page_rt_status)
    assert r2["링크"] == "https://b.com/o/2" and r2["상태"] == "" and r2["마감일"] == ""
    print("page_to_record ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds", required=True, help="지원현황 DB의 data_source id")
    ap.add_argument("--list", action="store_true",
                    help="전수 조회만 하고 JSON 출력 (dedup·팔로업·패턴 분석용)")
    ap.add_argument("--title")
    ap.add_argument("--company")
    ap.add_argument("--url")
    ap.add_argument("--deadline")
    ap.add_argument("--status", default="지원 전")
    ap.add_argument("--body", help="본문 마크다운 파일 (job-fit 템플릿)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.list:
        print(json.dumps(list_rows(a.ds), ensure_ascii=False, indent=1))
        return
    if not (a.title and a.company and a.url):
        ap.error("--title/--company/--url은 행 추가에 필수 (조회만 하려면 --list)")

    schema = call("GET", f"/data_sources/{a.ds}")["properties"]
    require_props(schema)
    options = [o["name"] for o in schema["회사"]["multi_select"]["options"]]
    status_type = schema["상태"]["type"]  # select 또는 status — 스키마에서 읽는다
    link_type = schema["지원 링크"]["type"]  # url 또는 rich_text — 스키마에서 읽는다

    title = a.title if a.company in options else f"[{a.company}] {a.title}"
    link_val = ({"url": a.url} if link_type == "url"
                else {"rich_text": [{"type": "text",
                                     "text": {"content": a.url, "link": {"url": a.url}}}]})
    props = {
        "이름": {"title": [{"text": {"content": title}}]},
        "지원 링크": link_val,
        "상태": {status_type: {"name": a.status}},
    }
    if a.company in options:
        props["회사"] = {"multi_select": [{"name": a.company}]}
    if a.deadline:
        props["마감일"] = {"date": {"start": a.deadline}}

    payload = {"parent": {"type": "data_source_id", "data_source_id": a.ds},
               "properties": props}
    if a.body:
        payload["children"] = md_to_blocks(open(a.body, encoding="utf-8").read())

    if a.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return
    page = call("POST", "/pages", payload)
    print(f"행 추가됨: {page.get('url')}")
    if a.company not in options:
        print(f"참고: '{a.company}'는 회사 옵션에 없어 제목 접두로 넣음 (100개 상한 규칙)")


if __name__ == "__main__":
    main()
