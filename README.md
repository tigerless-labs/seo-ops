<h1 align="center">seo-ops</h1>
<p align="center"><strong>SEO Foundation Checks as an Agent Skill</strong></p>

<p align="center">
  <img src="https://github.com/tigerless-labs/seo-ops/actions/workflows/ci.yml/badge.svg" alt="CI" /> <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="python" /> <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg" alt="platform" /> <img src="https://img.shields.io/badge/checks-26-brightgreen.svg" alt="checks" />
</p>

**seo-ops checks a site's SEO foundation — the machine-readable structure search engines and AI
retrieval need to fetch, read, index, and cite it.**

The only required input is a URL: the checker fetches the site like a crawler — no code access,
no framework integration — and produces a pass/fail [report](references/report.example.md) with evidence.

The whole repo is these three pieces:

| | What it is |
|---|---|
| [references/checklist/checklist.md](references/checklist/checklist.md) | The **C set** — 26 SEO/GEO structural checks, split into site-level / per indexed page / conditional. Each check has a detailed doc (criteria, common mistakes, authoritative references) at `references/checklist/references/C<N>.md` |
| [scripts/run.py](scripts/run.py) | The **checker script** — give it a URL and it fetches like a crawler and reports against the C set. **Zero LLM, no frontend-framework dependency**: it only reads the live HTTP/HTML output, so React / Vue / Next / WordPress / plain static all test the same |
| [references/content/content-checklist.md](references/content/content-checklist.md) | The **T set** — a supply checklist for the site's content design team: which inputs SEO needs content to provide (title/desc, H2 outline, image alt, ymyl judgment, OG copy, etc.), each annotated with the downstream C checks it feeds. Details at `references/content/references/T<N>.md` |

---

## Quick start

The whole repo is an Agent Skill — once installed, just say "check example.com's SEO" and
the agent confirms the target, runs the script, reads the report, and explains by P0/P1/P2 how to fix each red item.
Usage details live in [SKILL.md](SKILL.md).

**Let your agent install it** — copy the block below to your agent:

````
Install https://github.com/tigerless-labs/seo-ops as a skill.
````

**Or install as a plugin** — Claude Code (type in the input box):

```
/plugin marketplace add tigerless-labs/seo-ops
/plugin install seo-ops@seo-ops
```

Codex:

```bash
codex plugin marketplace add tigerless-labs/seo-ops
codex plugin add seo-ops@seo-ops
```

If the skill doesn't show up, start a new session. Update: `/plugin marketplace update seo-ops` (Claude Code) / `codex plugin marketplace upgrade` (Codex).

**Once installed**, type `/seo-ops` — or just describe the task; both trigger it:

```
/seo-ops check example.com
```

The agent introduces the checks, confirms live site vs code review, runs, and explains the red items.
