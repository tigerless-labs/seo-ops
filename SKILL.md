---
name: seo-ops
description: Structural checklist and checker script for SEO foundation engineering. Use when reviewing or accepting a site/page for SEO/GEO structural compliance (robots, sitemap, canonical, 301 canonicalization, JSON-LD, OG, hreflang, CWV, AI crawler access, rendering strategy), when running the machine checks to produce a report, or when judging whether a frontend change will affect indexing and citation. Also for answering "what exactly does this check require" and "why does it exist".
compatibility: Requires Python 3.9+, requests, PyYAML, and network access to the target site
---

# seo-ops · SEO foundation engineering

Review a site's templates and output against the **C set** (30 structural checks), or run the checker to produce an acceptance report.

## How to work

When this skill triggers, **spend two or three sentences telling the user what they've got**, then start:

> This is a set of 30 SEO/GEO structural checks (the C set). They test whether crawlers can fetch, read, index, and cite a site
> — binary structural questions, not ranking quality.

Then ask which of the two paths they want — **as selectable options if your environment has an
option/question UI; otherwise as this list**:

1. **Run the checker on a site** — a live domain or a local deployment (`http://localhost:<port>`), both work; produces a report
2. **Review code/templates** — no script; go through the checks one by one

**Confirm intent before starting**, because "check the live site" and "check the code" are two different jobs — guessing wrong wastes a full run:

| The user gave | Path | Section to follow |
|---|---|---|
| a domain / URL (live or localhost) | run the checker, produce a report | "**Run the checker**" → then "**Read the report**" |
| code, templates, a PR, page files | no script; review the machine-readable output surface against the C set item by item | "**Scope**" sets the boundary; `references/checklist/checklist.md` lists the items — but judge each one by its canonical doc `references/checklist/references/C<N>.md`, not by the index row alone |

Once intent is confirmed, **do not keep asking for permission**. Everything else:
the user asks why a check exists / how to fix it → "**After the report**";
whether to create a config, and which one → "**Configuration**";
dependencies won't install → "**Environment**".

Both paths **treat [references/checklist/checklist.md](references/checklist/checklist.md) as authoritative** —
never judge from memory; if unsure about an item, read `references/checklist/references/C<N>.md`.
Cite items by ID (`C12`); IDs are permanent — never renumber or reorder.

### After the report

**The report itself is the conclusion — don't walk through it item by item unprompted.** Each row carries a **Docs** column: the GitHub link to that check's canonical doc
— that link is for **the person reading the report** (it opens wherever the report is sent). **What you yourself read is the local copy**:
`references/checklist/references/C<N>.md`.

**When the user asks about a check, read `references/checklist/references/C<N>.md` before answering**
(for C12, read `references/checklist/references/C12.md`): "why it's a problem" comes from `## Introduction`,
"how to fix it" from `## Implementation guidance`. **Never answer by inferring from the evidence** — evidence only says which pages failed;
it can't tell you why the check exists, what the correct fix is, or where the authoritative reference lives.

### Environment

```bash
python3 -c "import requests, yaml" || pip install -r scripts/requirements.txt
```

On `externally-managed-environment` (PEP 668, common on Debian/Ubuntu), use the system packages
`apt install python3-requests python3-yaml` or create a venv — **do not add `--break-system-packages`**;
that gambles the system Python for a two-line dependency.

## Scope

**SEO foundation engineering** = the machine-readable structure a site must have so that search engines and AI retrieval can **fetch, read, index, and cite** it.

**What it checks**: the machine-readable surface of the final HTTP/HTML output — regardless of who produced it (backend templates, frontend code,
third-party scripts); if a crawler can see it, it's covered. The boundary is "machine-readable surface / human-perceivable surface", not frontend/backend.

**What it doesn't check**: styling, interaction, UX, code quality; content truthfulness and quality; ranking and traffic; process.
**All green ≠ fully compliant.**

**The human gate is a separate set**: the R1-R8 prohibitions (buying links, cloaking, fake structured data, PII in prompts, etc.) live in
[redlines.md](redlines.md); the machine doesn't check them. Read them before touching content strategy, links, or structured data.

## What's here

| Path | What it is |
|---|---|
| [references/checklist/checklist.md](references/checklist/checklist.md) | The **C set** index: 30 checks, split into site-level / per indexed page / conditional |
| `references/checklist/references/C<N>.md` | Each C check's canonical doc: `## Introduction` (why) + `## Implementation guidance` (how to fix) + authoritative references |
| `references/content/` | The **T set**: for tracing a red C back to "who owes the input"; outside this skill's duties |
| `scripts/run.py` · `scripts/config.py` | Check logic / check parameters |
| `references/ai-crawlers.yaml` | The AI crawler UA roster for C1, read at runtime |
| `references/{sites,config}.example.yaml` · `references/.env.example` | Three config templates, see "**Configuration**" |

`<N>` maps one-to-one to the IDs in the checklist; C12's canonical doc is `references/checklist/references/C12.md`.
Gaps in the numbering are normal (retired IDs are never recycled).

**The skill directory is read-only — zero writes.** Updates overwrite the whole package; anything written inside will be lost.

## Run the checker

**Confirm the target is an origin → ask for all necessary config in one pass (see "Configuration") → run.**
Get it running first; don't stall on optional items — none of the three config files is required.

**One "site" = one origin** (scheme + host[:port], no path/query). Subdomains count as separate sites
(`blog.` / `docs.` are each one); the apex domain and www don't count as two — they should 301 to a single canonical host,
which is exactly what C3 checks, so only the one you pick counts.

### Single site: no config file needed

```bash
python3 scripts/run.py --target https://example.com      # live site
python3 scripts/run.py --target http://localhost:3000    # local deployment, auto-detected as local mode
```

`--target` must be an origin; a URL with path/query exits with an error immediately — no guessing.

**Public staging domains are not supported** — they'd be tested as production domains, and the canonicalization check (C3) would false-red for sure.
To test before launch, pick one: run a local deployment at `http://localhost:<port>`, or wait and run against the production domain after launch.

### Multi-site: run a batch in one go

"Multi-site" = you have several domains to accept at once (e.g. `example.com` + `example.org` + `blog.example.com`),
don't want to retype `--target` every time, and want each site to carry its own rendering strategy and must-test pages. After creating `sites.yaml` (see "Configuration"):

```bash
python3 scripts/run.py               # run every site in the roster
python3 scripts/run.py --site <id>   # run just one
```

Each entry takes: `id` (used for the report filename and the `checks` table's site column), `production` (origin, required),
`rendering` (ssr/ssg/isr; C15 branches on it), `sitemap` (defaults to `<production>/sitemap.xml`),
`samples` (must-test pages fetched in addition to the sitemap; mark `ymyl: true` to trigger the C21 human review).
If the roster can't be found, the script exits and prints where to create it — it never silently runs empty.

### Common flags

One-off overrides: `--page-sample N` `--sitemap-sample N` `--max-pages N` `--sleep S` `--workers N`.
Output overrides: `--state-dir <path>` / `--out <path>`.
`--verify-only`: run only the two drift guards, no network; exits 1 on drift (for CI).

Runtime: at the default single worker with a 1s interval, roughly `2 × sitemap entries` requests. A 271-page site takes about 7 minutes
(**tell the user roughly how long the wait is before running**); for speed, sample with `--page-sample 100` —
structural problems are template-level, so a sample and a full run see the same set.

## Read the report

Each run writes two outputs to `~/Documents/seo-ops/out/` (`--state-dir` / `--out` / `$SEO_OPS_DIR` to change):

| Output | For | What it is |
|---|---|---|
| `report-<site>-<date>.md` | humans | mirrors the checklist one-to-one; the same 30 rows every run |
| `checks.db` | machines | SQLite, `checks(site, url, rule_id, status, evidence, checked_at)`, primary key `(site,url,rule_id)`; accumulates across runs for diffing |

| Result | Meaning |
|---|---|
| ✅ pass | tested, passed |
| 🔴 fail | tested, failed — the Evidence column shows the violating pages and why |
| ⚪ N.A. | **not tested**; the reason code is in parentheses. **"Not tested" is not "fine"** |
| 👤 human review | the script doesn't judge; listed to remind a human to go through it |

Common N.A. reason codes: `need-domain` (local mode), `need-crux-key` / `need-crux-data` (C4),
`need-key-declaration` (C5), `need-declaration` (no rendering strategy declared), `no-pages`,
`crawl-capped` (crawl hit the cap), `throttled` (throttled by the target; rerun slower).

**Check the warning lines at the top of the report first** — if any are present, this run's verdict is incomplete:

- 🚦 **throttled by the target** (429/503) — we hit it too fast; the site is not at fault. Affected verdicts are recorded as N.A.,
  not fail (**a false red is more dangerous than a slow run**). For a complete verdict: halve `--workers` or raise `--sleep` and rerun.
- ⚠️ **sample fetches failed** (not throttling) — genuinely unreachable; these pages are excluded from the denominator.

Priorities: **P0 = existence/incident layer** (can't be fetched or indexed); **P1 = performance layer** (ranking and citation are discounted); **P2 = optimizations**.

## Configuration

**None of the three files is required.** They live in `~/.config/seo-ops/` (`$SEO_OPS_CONFIG_DIR` to change);
just copy from the templates — **do not edit `scripts/config.py`**; it's the skill body and gets overwritten wholesale on update.

```bash
mkdir -p ~/.config/seo-ops
```

| File | When you need it | Cost of not creating it | How to create |
|---|---|---|---|
| `sites.yaml` | multi-site, or to declare a rendering strategy / mark YMYL pages | single-site runs fine with `--target`; C15 records `need-declaration`, C21 has no human-review list | `cp references/sites.example.yaml ~/.config/seo-ops/sites.yaml` |
| `.env` | **only when the user wants a "complete verdict"** (CrUX / IndexNow key) | **not required**; C4 records `need-crux-key`, C5 records `need-key-declaration`, everything else runs | `cp references/.env.example ~/.config/seo-ops/.env` |
| `config.yaml` | only to change thresholds | none; all defaults apply | `cp references/config.example.yaml ~/.config/seo-ops/config.yaml` |

`.env` is a hidden file; `ls` without `-a` makes the directory look empty.
**Exported environment variables always beat `.env`** — a key injected by CI can't be overridden by someone's local file.
Legacy locations (`<state-dir>/sites.yaml`, `<state-dir>/.env`, `scripts/.env`) are still read,
but whenever a value is actually taken from one, a warning prompts you to move it — a silently misplaced config makes the same command give different verdicts.

### What config.yaml can tune

Every line in the template is the **current default**; keeping it as-is equals not configuring it. Change only the lines you need. Commonly tuned:

| Parameter | Effect |
|---|---|
| `FETCH_SLEEP` / `FETCH_CONCURRENCY` | fetch throttling; overall QPS ≈ workers / interval. Defaults 1 / 1 |
| `PAGE_SAMPLE_SIZE` | page-level check coverage: `0` = full, `>0` = sample cap |
| `CRAWL_MAX_PAGES` | internal crawl cap (C6) |
| `TITLE_MAX_CHARS` / `DESC_MAX_CHARS` | C11 length limits |
| `THROTTLE_*` | throttle backoff and recovery |
| `DOC_BASE_URL` | base URL for the report's Docs column links; switch it to a commit SHA to pin a version |

**Unregistered keys and type mismatches exit with an error**, never silently ignored — a typo'd key producing a report on defaults is more dangerous than an error.

**Three categories can't be tuned here**: **secrets** (live in `.env`); **constants** (the three CWV thresholds are Google's official "good" lines,
the sitemap 50k cap is a protocol hard limit, the viewport token is the spec value — change them and it's no longer the same check);
**structural judgments** (`TYPE_REQUIRED`, `LD_REJECTED_TYPES`, `BODY_HIDE_PATTERNS` —
changing them changes the check logic; that belongs in a human-reviewed PR, not hidden in someone's local yaml).
