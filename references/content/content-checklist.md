# content supply checklist (the T set — the content team's responsibility list)

> Mirrors the [checklist (C set)](../checklist/checklist.md): **the C set checks whether page
> output is right; the T set defines what content must supply** — each T is tagged with the
> downstream C check it feeds, so T under-supplied ⇒ the matching C goes red, and responsibility
> traces back.
> **Complement positioning**: page docs ship as before; what's already being delivered is not
> re-listed. This table only lists the **SEO supply items they don't cover**, delivered as an
> **"Appendix · SEO" at the end of the page doc** — one contiguous section, not scattered into
> the body, and the header gives up no room either. The fields are also registered in the
> content team's own registry — the appendix is the writing surface, the registry is the
> bookkeeping surface, and checker status echoes red/green on the registry.
> Each entry has its own detailed page under [references/](references/); when actually writing
> a page use [page-doc-template.md](page-doc-template.md) — **this table is the checklist, the
> template is the fill-in surface**.

## 1. Site-level (one-time supply + low-frequency maintenance)

| ID | Supply | Notes | Downstream |
|---|---|---|---|
| T1 | Canonical brand-name spelling + official social account list | Data source for Organization `sameAs`; the three sites point at one entity | C12 |
| T2 | Key-page list + one-line summary per page | Which pages go into llms.txt is the content team's call, one-line summary each (file generation belongs to frontend) | C7 |

## 2. Required per page (the "Appendix · SEO" at the end of the page doc)

| ID | Supply | Constraints | Downstream |
|---|---|---|---|
| T3 | URL | semantic path, hierarchy reflects category, no ambiguous words; new URLs go through review | |
| T4 | **`ymyl` verdict** | `true` if the content affects the reader's health / finances / legal standing / physical safety; **when unsure, mark `true`**. This is the only switch for the conditional items; a missed flag = all of C21 disabled | C21 |
| T5 | title / description | title ≤60, desc ≤150, site-level formula, unique per page — no copy-paste | C11 |
| T6 | one H1 line | one per page, same topic as the title (wording may differ) | C17 |
| T7 | H2/H3 outline | **delivered structured in the SEO appendix (`outline`), not mixed into the body**; levels never skip; guide / FAQ content: questions verbatim, conclusion first in each section | C17 · content-shape requirements of C7/C12 |
| T14 | image alt copy | **keyed by image filename** (`images[].file` + `alt`, not "figure 1 / figure 2" — images get added, removed, and moved in the body, and the numbering shifts); one descriptive sentence per content image (say what's in the image, don't stack keywords); pure decoration marked "decorative" (frontend renders it as `alt=""`) | C18 |
| T8 | language config and bilingual pairs | en/zh delivered together, no one-sided pages; single-language pages declare en only / zh only explicitly | C22 |
| T9 | OG share copy **+ share-image designation** | copy may share its source with title/desc; supply separately when differentiated; the share image **defaults to the body's lead image** — when that image doesn't work as a card (wrong size, an icon / decorative image), designate one here | C19 |
| T10 | date_modified upkeep | update in step with substantive content changes (feeds JSON-LD and the visible label, one source). **Kept for GEO**: AI answers clearly prefer recent content, above all for rates / policy / process pages | C21 |

## 3. Conditional (flag / content-condition triggered)

> The trigger is a **flag or whether that thing is on the page**, not page type — page-type
> conditions were retired wholesale on 2026-08-25 (Google doesn't consume `WebPage` subtypes,
> while page-type declarations need content to maintain per page and fail silently when missed;
> rationale at the top of [C12.md](../checklist/references/C12.md)).

| ID | Trigger | Supply | Downstream |
|---|---|---|---|
| T12 | `ymyl=true` ([T4](references/T4.md)) | author real name + title + credential; reviewer + review date (the review **actually happened**, R2); citations from official sources (domain ∈ allowlist) | C21 |
| T13 | the page shows a product with pricing | human-readable fields — product name / selling points / price etc. (registered structured, JSON-LD reads its values from here) | C12 |

> Numbering discipline matches the C set: T numbers are permanent, only append (next is T15),
> never reuse; row order expresses semantic adjacency.
> Acceptance: the checker runs the C set; trace red items back through the "Downstream" column
> to a T and you know whether content under-supplied or frontend didn't land it.

> **This table holds only the entries currently in force.** What was added or removed and why,
> and the C checks judged but given no T, all live in [decisions.md](../decisions.md) — the
> checklist answers "what to deliver now", the log answers "why these".
