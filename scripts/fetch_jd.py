#!/usr/bin/env python3
"""채용공고 본문 수집기 — job-fit/job-scan의 ATS별 curl 조합을 코드로 고정.

사용: python3 도구/fetch_jd.py <공고URL>
출력: 마크다운(메타 헤더 + 본문). 못 가져오면 retrieved=false와 이유를 출력하고 exit 1.

지원 ATS: 원티드 · 사람인(쿠키 절차 포함) · 자소설닷컴 · LG Careers ·
Greenhouse · Ashby · greetinghr · 그 외 Next.js(__NEXT_DATA__) · 일반 HTML
"""
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def http(url, data=None, headers=None, opener=None, timeout=20):
    h = {"User-Agent": UA, "Accept-Language": "ko,en"}
    h.update(headers or {})
    if data is not None and not isinstance(data, bytes):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=h)
    op = opener or urllib.request.build_opener()
    return op.open(req, timeout=timeout).read().decode("utf-8", "replace")


def get_json(url, **kw):
    kw["headers"] = {"Accept": "application/json", **kw.get("headers", {})}
    return json.loads(http(url, **kw))


def strip_html(s):
    s = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<(br|/p|/li|/div|/h[1-6]|/tr)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def next_data(page_html):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    return json.loads(m.group(1)) if m else None


def long_strings(obj, minlen=200, acc=None):
    """JSON 트리에서 본문일 법한 긴 문자열을 전부 수집(구조를 모르는 Next.js용)."""
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for v in obj.values():
            long_strings(v, minlen, acc)
    elif isinstance(obj, list):
        for v in obj:
            long_strings(v, minlen, acc)
    elif isinstance(obj, str) and len(obj) >= minlen:
        acc.append(obj)
    return acc


def out(title, company, body, url, source, status="", deadline="", note=""):
    lines = [f"# {title or '(제목 미상)'}" + (f" — {company}" if company else "")]
    lines.append(f"- source: {source}")
    lines.append(f"- url: {url}")
    if status:
        lines.append(f"- status: {status}")
    if deadline:
        lines.append(f"- deadline: {deadline}")
    if note:
        lines.append(f"- note: {note}")
    print("\n".join(lines) + "\n\n" + (body or "(본문 없음)"))


def fail(url, why):
    print(f"# retrieved=false\n- url: {url}\n- reason: {why}\n"
          "- 조치: 사용자에게 본문 붙여넣기를 요청한다. 창작 금지.")
    sys.exit(1)


def q(url, key):
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get(key, [None])[0]


# ---------- ATS별 핸들러 ----------

def wanted(url):
    jid = re.search(r"/wd/(\d+)", url).group(1)
    j = get_json(f"https://www.wanted.co.kr/api/v4/jobs/{jid}")["job"]
    status = j.get("status", "")
    if status != "active":
        status += " ⚠️ 유령공고 가능성 — 등록 금지"
    d = j.get("detail") or {}
    body = "\n\n".join(f"## {k}\n{d[k]}" for k in
                       ("intro", "main_tasks", "requirements", "preferred_points", "benefits")
                       if d.get(k))
    skills = ", ".join(t["title"] for t in j.get("skill_tags", []))
    if skills:
        body += f"\n\n## skill_tags\n{skills}"
    out(j.get("position"), (j.get("company") or {}).get("name"), body, url,
        "wanted-api", status, j.get("due_time") or "상시")


def saramin(url):
    rec = q(url, "rec_idx") or re.search(r"rec_idx=(\d+)", url).group(1)
    view = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec}"
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    page = http(view, opener=op)  # 쿠키 먼저 — 없이 detail 치면 남의 공고가 온다
    og = dict(re.findall(r'<meta property="og:(title|description)" content="([^"]*)"', page))
    if not og.get("title"):
        fail(url, "og:title 없음 — 공고 소멸/마감으로 판단")
    detail = http(f"https://www.saramin.co.kr/zf_user/jobs/relay/view-detail?rec_idx={rec}",
                  opener=op, headers={"Referer": view})
    body = strip_html(detail)
    # 회사명이 본문에 안 나오는 공고가 흔해 기계 판정은 오탐한다.
    # ponytail: 쿠키 플로우가 오배송(타 공고 서빙)의 근본 원인을 막고, 의미 대조는 호출자 몫.
    tokens = [t for t in re.findall(r"[가-힣A-Za-z0-9]{3,}", og["title"]) if t != "사람인"][:5]
    note = ("" if any(t in body for t in tokens)
            else "본문에 og:title 토큰 없음 — og:title 직무와 본문이 같은 공고인지 대조할 것")
    out(og["title"], "", (og.get("description", "") + "\n\n" + body).strip(), url,
        "saramin(cookie)", note=note)


def jasoseol(url):
    jid = re.search(r"/recruit/(\d+)", url).group(1)
    j = get_json(f"https://jasoseol.com/api/v1/employment_companies/{jid}")
    emp = "\n".join(f"- {e.get('field')} (duty={e.get('duty_group_ids')}, "
                    f"졸업={e.get('graduate_condition')}, 어학={e.get('english_score_requirement')})"
                    for e in j.get("employments", []))
    body = f"## 모집 직무\n{emp}\n\n원문(자격요건·근무지는 여기서 확인): {j.get('employment_page_url')}"
    out(j.get("title") or j.get("name"), j.get("name"), body, url, "jasoseol-api",
        deadline=str(j.get("end_time") or ""), note="상세 본문은 employment_page_url 원문 필요")


def lg(url):
    jid = int(q(url, "jobNoticeId"))
    hdr = {"Origin": "https://careers.lg.com", "Referer": "https://careers.lg.com/"}
    d = get_json("https://api.careers.lg.com/rmk/job/retrieveJobNoticesDetail",
                 data={"jobNoticeId": jid}, headers=hdr)["data"]["jobNoticesDetail"]
    # 제목·회사·마감은 목록 API에만 있다
    lst = get_json("https://api.careers.lg.com/rmk/job/retrieveJobNoticesList",
                   data={"lnbSearch": "", "hashTagText": "", "recDate": "CREATION_DATE",
                         "order": "DESC", "careerList": [], "companyCodeList": [],
                         "desireLocList": [], "jobGroupList": []},
                   headers=hdr)["data"]["jobNoticeList"]
    meta = next((x for x in lst if x.get("jobNoticeId") == jid), {})
    secs = []
    for r in d.get("recList", []):
        secs.append(f"## {r.get('jobGroupName') or ''} {r.get('jobCodeName') or ''} ({r.get('locationName') or ''})\n"
                    f"[담당] {strip_html(r.get('mainTask') or '')}\n"
                    f"[필수] {strip_html(r.get('requiredItem') or '')}\n"
                    f"[우대] {strip_html(r.get('preferredItem') or '')}\n"
                    f"{strip_html(r.get('detailContext') or '')}")
    prc = " → ".join(p.get("displayName", "") for p in d.get("prcList", []))
    body = "\n\n".join(secs) + (f"\n\n## 전형\n{prc}" if prc else "")
    out(meta.get("jobNoticeName"), meta.get("companyName"), body, url, "lg-careers-api",
        deadline=str(meta.get("recEndDateTime") or ""),
        note=meta.get("careerTypeName", ""))


def greenhouse(url):
    m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if m:
        org, jid = m.groups()
    else:
        jid = q(url, "gh_jid")
        org = urllib.parse.urlparse(url).hostname.split(".")[0]
    j = get_json(f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs/{jid}")
    out(j.get("title"), org, strip_html(html.unescape(j.get("content", ""))), url,
        "greenhouse-api", deadline="", note=(j.get("location") or {}).get("name", ""))


def ashby(url):
    org, uid = re.search(r"ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", url).groups()
    j = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true")
    job = next((x for x in j.get("jobs", []) if x.get("id") == uid), None)
    if not job:
        fail(url, "Ashby job-board에 해당 id 없음 — 마감 추정")
    out(job.get("title"), org, job.get("descriptionPlain") or strip_html(job.get("descriptionHtml", "")),
        url, "ashby-api", note=job.get("location", ""))


def greeting(url):
    nd = next_data(http(url))
    if not nd:
        fail(url, "__NEXT_DATA__ 없음")
    for qr in nd["props"]["pageProps"]["dehydratedState"]["queries"]:
        if "getOpeningById" in str(qr.get("queryKey", "")):
            o = qr["state"]["data"]["data"]["openingsInfo"]
            c = o.get("careerInfo") or {}
            out(o.get("title"), "", strip_html(o.get("detail", "")), url, "greetinghr",
                deadline=str(o.get("dueDate") or ""),
                note=f"요구 연차 {c.get('from')}~{c.get('to')}")
            return
    fail(url, "getOpeningById 쿼리 없음")


def page_title(page):
    m = (re.search(r'<meta property="og:title" content="([^"]+)"', page)
         or re.search(r"<title[^>]*>(.*?)</title>", page, re.S))
    return html.unescape(m.group(1)).strip() if m else ""


def generic(url):
    page = http(url)
    nd = next_data(page)
    if nd:
        chunks = long_strings(nd)
        if chunks:
            out(page_title(page), "", "\n\n---\n\n".join(strip_html(c) for c in chunks[:8]),
                url, "next-data(generic)", note="구조 미상 — 긴 텍스트 필드만 추출")
            return
    body = strip_html(page)
    if len(body) < 300:
        fail(url, f"본문이 비어 있음({len(body)}자) — JS 렌더링 페이지로 추정")
    out(page_title(page), "", body, url, "html(generic)")


ROUTES = [
    (r"wanted\.co\.kr/wd/", wanted),
    (r"saramin\.co\.kr/.*rec_idx=", saramin),
    (r"jasoseol\.com/recruit/", jasoseol),
    (r"careers\.lg\.com/.*jobNoticeId=", lg),
    (r"greenhouse\.io/[^/]+/jobs/\d+|[?&]gh_jid=", greenhouse),
    (r"jobs\.ashbyhq\.com/", ashby),
    (r"career\.greetinghr\.com/", greeting),
]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    url = sys.argv[1]
    fn = next((f for pat, f in ROUTES if re.search(pat, url)), generic)
    try:
        fn(url)
    except (urllib.error.URLError, KeyError, AttributeError, json.JSONDecodeError) as e:
        fail(url, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
