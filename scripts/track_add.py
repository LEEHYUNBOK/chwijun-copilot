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


def selftest():
    b = md_to_blocks("## 적합도 상\n**레벨** 경력\n---\n- 강점 하나\n> 출처: api")
    assert [x["type"] for x in b] == ["heading_2", "paragraph", "divider",
                                     "bulleted_list_item", "quote"]
    assert b[1]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True
    r = rich("[출처] [공고](https://a.com/o/1) · 메일")
    assert [x["text"]["content"] for x in r] == ["[출처] ", "공고", " · 메일"]
    assert r[1]["text"]["link"]["url"] == "https://a.com/o/1"
    print("md_to_blocks ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds", required=True, help="지원현황 DB의 data_source id")
    ap.add_argument("--title", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--deadline")
    ap.add_argument("--status", default="지원 전")
    ap.add_argument("--body", help="본문 마크다운 파일 (job-fit 템플릿)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    schema = call("GET", f"/data_sources/{a.ds}")["properties"]
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
