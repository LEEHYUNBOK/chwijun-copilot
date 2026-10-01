**Language:** [한국어](../../README.md) | English

# Chwijun Copilot (취준 코파일럿)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](../../LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-d97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins/create)
![Python](https://img.shields.io/badge/-Python%203%20(stdlib%20only)-3776AB?logo=python&logoColor=white)
![Skills](https://img.shields.io/badge/skills-6-brightgreen)
![Market](https://img.shields.io/badge/market-Korean%20job%20market-success)

**A job-hunting copilot for the Korean job market. Career-wiki onboarding, posting fit analysis, company watchlist scanning, resume/cover-letter rules, and application tracking — all in one Claude Code plugin install.**

This is a generalized version of the personal skill set I used daily while applying to dozens of companies during an actual job search. It is not a tool that flatters you into applying — it never invents experience that isn't in your profile, it calls a gap a gap, and when a posting is a bad fit it tells you not to apply. The goal is fewer failed applications.

> "Chwijun" (취준) is Korean shorthand for 취업 준비 — job hunting.

---

## Quick Start

```bash
# 1. Add the marketplace and install
/plugin marketplace add LEEHYUNBOK/chwijun-copilot
/plugin install chwijun-copilot

# 2. Onboard (once, required)
/chwijun-copilot:wiki-bootstrap
```

Onboarding asks your job family first (engineering / product·PM / design / marketing), then interviews you with questions tuned to that family and scaffolds your career wiki — profile, work documents, and an application tracker. After that, plain language works:

```
Look at this posting https://...   → fit analysis + tracker entry
Scan for new postings              → batch-scan your watchlist companies
Polish my cover letter answer      → loads the writing rules
Anyone gone quiet on me?           → follow-up check
Why do I keep getting rejected?    → funnel / rejection pattern analysis
```

For local testing: `claude --plugin-dir /path/to/chwijun-copilot`.

---

## What's Inside

| Component | Role |
|---|---|
| `agents/chwijun-copilot` | Entry-point router — no skill names to memorize |
| `skills/wiki-bootstrap` | Onboarding: job family → interview → career wiki scaffolding → config |
| `skills/job-fit` | Fit analysis for one posting URL (0–100 score, explicit gaps) + tracker entry |
| `skills/job-scan` | Batch scan of watchlist company ATSs and job boards, dedup, per-run cap |
| `skills/resume-writing` | Resume / career statement / cover-letter rules + AI-tone removal + mechanical style check |
| `skills/apply-followup` | Post-application silence check with Korean-convention cadence (14 days for documents, 7 between stages, one inquiry per company) |
| `skills/apply-patterns` | Funnel and rejection pattern analysis — refuses to name patterns under 5 samples |
| `scripts/` | fetch_jd.py (per-ATS posting collector) · track_add.py (Notion tracker) · check_voice.py (style checker) |
| `templates/` | Profile, wiki document, tracker, and watchlist templates |

---

## Why a Wiki

Every skill reads from **one career wiki** that onboarding creates. Your resume is never re-parsed per request.

```
career-wiki/
├── 프로필.md (profile)   ← the single matching baseline (includes a "gaps" section)
├── 개요.md (index)       ← entry point
├── 지원현황.md (tracker)  ← local tracker, one section per posting
└── 문서/ (documents)     ← work documents (problem → what I did → result)
```

The profile has a mandatory "gaps" section — fit analysis only works if missing experience isn't hidden. An inflated profile doesn't raise your pass rate; it raises your interview rejection rate.

---

## Korean-Market Trap Knowledge, Built In

Things generic job tools don't know, written into the skill bodies:

- **Wanted ghost postings** — listed but `status: close` means do not register
- **Saramin detail pages require cookies** — without them you get a *different posting's* body; fetch_jd.py handles the cookie dance
- **Saramin is an excerpt** — companies with their own ATS have the authoritative posting there
- **Per-ATS collection paths** — list/detail APIs for Greenhouse, Ashby, greetinghr (hosted/embedded), Toss, Saramin
- **One follow-up per company** — Korean convention; a second inquiry backfires

---

## Config

Onboarding writes `~/.claude/chwijun-copilot.json`:

```json
{ "wiki_path": "<absolute path to career wiki>", "tracker": "local", "notion_ds_id": "" }
```

- `tracker: "local"` (default) — applications accumulate in the wiki's tracker file; zero extra setup
- `tracker: "notion"` — set `notion_ds_id` + `NOTION_TOKEN` to append rows to a Notion database

## Data

Your profile, wiki, and application history stay in the wiki folder on your machine. The only outbound traffic is the Notion API when you explicitly enable the Notion tracker.

## Roadmap

- [ ] Natural-language routing verification on a clean machine
- [ ] `track_add.py --list` — Notion tracker reads (dedup, full scans)
- [ ] Full-funnel skills — interview practice · offer comparison · salary negotiation

## License

[MIT](../../LICENSE)
