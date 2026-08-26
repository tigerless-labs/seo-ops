---
name: seo-ops
description: Structural checklist and checker script for SEO foundation engineering. Use when reviewing or accepting a site/page for SEO/GEO structural compliance (robots, sitemap, canonical, 301 canonicalization, JSON-LD, OG, hreflang, CWV, AI crawler access, rendering strategy), when running the machine checks to produce a report, or when judging whether a frontend change will affect indexing and citation. Also for answering "what exactly does this check require" and "why does it exist".
compatibility: Requires Python 3.9+, requests, PyYAML, and network access to the target site
---

# seo-ops (plugin adapter)

This file exists only because plugin skill discovery requires the `skills/<name>/SKILL.md`
layout. The canonical skill is the repo root, two directories up.

1. Read `../../SKILL.md` (resolve relative to this file) and follow it exactly.
2. Resolve every relative path it mentions against the **plugin root** (two directories
   above this file): `scripts/run.py` means `../../scripts/run.py`, `references/...`
   means `../../references/...`.
