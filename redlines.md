# Obligations: red lines and process (SEO Conformance)

> Division of labor: **the checklist owns "what to check"** (the C set structural checks, machine-run); **this file owns "what's forbidden"** (red lines,
> guarded by humans). Process-type rules (e.g. new URLs go through review) are for each adopter to define — not part of this package. IDs share one numbering scheme, never reordered.

## Red lines R1-R8 (prohibitions)

| ID | Red line | Basis |
|---|---|---|
| R1 | Agents never change production directly; every change goes through PR + human review |  |
| R2 | YMYL content (insurance/medical/finance) must not be published without **review by the company's specialist department**; bylines must be truthful (the review process belongs to the content management team) | YMYL/E-E-A-T |
| R3 | Mass-generated pages with no real data behind them (thin content) | scaled content abuse |
| R4 | The same content published on multiple domains with no canonical attribution |  |
| R5 | Fake structured data (fake ratings/fake FAQ), buying reviews / fabricating scores | manual action |
| R6 | Buying links, link farms, any link scheme participation | Penguin / manual action |
| R7 | Cloaking: serving crawlers and users different content (a cached public shell + client-side personalization doesn't count; UA-targeted content does); hidden text and keyword stuffing belong in the same bucket | Google spam policies, delisting-level |
| R8 | User-level data (PII) entering the store, the harness, prompts, or any third-party API (including LLM calls) | privacy; GA4 aggregates only |

## Authoritative references (official docs, R set)

> The C set's authoritative references live with the checklist at [checklist/checklist.md](checklist/checklist.md).

| Rule | Reference |
|---|---|
| R3 (scaled content) / R6 (link spam) / R7 (cloaking, hidden text, stuffing) | [Google Spam Policies](https://developers.google.com/search/docs/essentials/spam-policies) — every red line has explicit text here |
| R5 (fake structured data, bought reviews) | [Google Structured Data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) |
| The YMYL/E-E-A-T behind R2 | [Google Search Quality Rater Guidelines](https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf) (the rater handbook; the original definitions of E-E-A-T and YMYL) |

Maintenance convention: dead links or policy updates are a harness change — update this table after human review; R/C IDs are permanent, extend only, never reorder.
