# seo-ops

A checklist and checker for **SEO foundation engineering** — the machine-readable structure a site needs so search engines and AI retrieval can **fetch, read, index, and cite** it.

**The only required input is a URL.** No code access, no framework integration — the checker fetches the site like a crawler and produces a pass/fail report with evidence.

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

**Or install by hand** — Claude Code (`~/.claude/skills/` for all projects, `<repo>/.claude/skills/` for one project):

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.claude/skills/seo-ops
```

Codex (`~/.agents/skills/` for all projects, `<repo>/.agents/skills/` for one repo):

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.agents/skills/seo-ops
```

Update: `git pull`. New skills are discovered at session start — if it doesn't show up, start a new session.
