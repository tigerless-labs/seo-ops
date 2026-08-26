# seo-ops

A checklist and checker for **SEO foundation engineering** — the machine-readable structure a site needs so search engines and AI retrieval can **fetch, read, index, and cite** it.
Give it a URL: it fetches like a crawler and produces a pass/fail report with evidence.

The whole repo is these three pieces:

| | What it is |
|---|---|
| [references/checklist/checklist.md](references/checklist/checklist.md) | The **C set** — 26 SEO/GEO structural checks, split into site-level / per indexed page / conditional. Each check has a detailed doc (criteria, common mistakes, authoritative references) at `references/checklist/references/C<N>.md` |
| [scripts/run.py](scripts/run.py) | The **checker script** — give it a URL and it fetches like a crawler and reports against the C set. **Zero LLM, no frontend-framework dependency**: it only reads the live HTTP/HTML output, so React / Vue / Next / WordPress / plain static all test the same |
| [references/content/content-checklist.md](references/content/content-checklist.md) | The **T set** — a supply checklist for the site's content design team: which inputs SEO needs content to provide (title/desc, H2 outline, image alt, ymyl judgment, OG copy, etc.), each annotated with the downstream C checks it feeds. Details at `references/content/references/T<N>.md` |

---

## Quick start

The whole repo is an Agent Skill — once installed, just say "check tigerless.com's SEO" and
the agent confirms the target, runs the script, reads the report, and explains by P0/P1/P2 how to fix each red item.
Usage details live in [SKILL.md](SKILL.md).

**Claude Code**

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.claude/skills/seo-ops
```

**Codex**

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.codex/skills/seo-ops
```

For a project-level install, replace `~/.claude` with `<your repo>/.claude` (same for Codex). Update: `git pull`.

**Or simply let your agent install it** — copy the whole block below to your agent:

````
Install https://github.com/tigerless-labs/seo-ops as a skill:

1. Clone it to wherever you load skills from, directory name seo-ops
   (Claude Code: ~/.claude/skills/ or <repo>/.claude/skills/; Codex: ~/.codex/skills/)
2. Install the whole repo, not just SKILL.md — scripts/ and references/ are runtime dependencies
3. Install dependencies: python3 -c "import requests, yaml" || pip install -r <skill>/scripts/requirements.txt
4. Smoke test: python3 <skill>/scripts/run.py --verify-only, it should print "✅ checklist and script in sync"
5. Read SKILL.md, then tell me what it checks and what it doesn't
````
