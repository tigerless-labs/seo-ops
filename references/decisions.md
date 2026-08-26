# Decision log (judged but not landed as entries)

Ryan · 2026-08-26 · `accepted`

> The checklists (C set / T set) hold only **entries currently in force**: whether and how to
> deliver something now, read the checklist; **why an entry looks the way it does, and why
> there is no other entry**, read this.
> Settled conclusions live in this log so nobody re-raises them next time and argues from scratch.

## 1. T-set additions and removals (retired numbers are not reused; next is T15)

| Date | Change | Rationale |
|---|---|---|
| 2026-08-25 | **Add T14** image alt copy | Only someone who has seen the image can write that sentence; AI can't read the image, only the alt |
| 2026-08-25 | **T9 gains share-image designation** | Defaulting to the body's lead image is fine, but when that image is an icon / wrong size / too long, only a human can pick the replacement |
| 2026-08-25 | **Drop T11** status upkeep | Page lifecycle status lives in the content team's own registry, maintained by them via the repo team's API — not a supply item for this system |
| 2026-08-25 | **Page-type supply retired wholesale**; T4 narrowed from "page type + ymyl" to the single `ymyl` flag | Google doesn't consume `WebPage` subtypes; page type needs content to judge every page and fails silently when missed — an input that needs daily human feeding with no downstream consumer isn't worth keeping (see the top of [C12.md](checklist/references/C12.md)) |
| 2026-08-26 | **T10 deleted, reinstated the same day** | Kept for **GEO**: update time is a strong preference signal when AI cites; it is also a required field of C12 `Article` and the "declared ↔ visible" comparison item in the C21 human review — delete it and there is no value source |

## 2. C checks judged but given no T (2026-08-25)

One uniform criterion: whether a C check spawns a T depends on **whether its verdict inputs
contain something only a human can write**.
Alt copy does (only someone who has seen the image can write it) → [T14](content/content-checklist.md);
`og:type` doesn't (the template can decide from the body) → no T.

| C check | Why it doesn't land on content |
|---|---|
| C2 sitemap shards ≤50k | The sitemap is **derived** from the route/content tables; its size is a derived result, no human-suppliable field |
| C8 the two canonical paths (header vs HTML) don't conflict | The conflict source is CDN/reverse-proxy rules, pure infrastructure |
| C19's `og:type` value | The template decides from the page's own content (article body present → `article`), frontend derives it; nothing only a human could write |
| C23 indexed pages carry no noindex | Template and deployment config; content expresses "should this page be indexed" through **sitemap membership**, not by writing meta |
| C24 viewport meta | One line in the base template, unrelated to content |
| C25 no mixed content | Writers pasting `http://` external images into copy is indeed a common source, but **the real fix is frontend rewriting the protocol or re-hosting on our own CDN at ingest** (implementation guidance in [C25.md](checklist/references/C25.md)) — plug it once, better than asking every writer to remember every time. **Put the constraint where it can be solved once, not where a human must remember each time.** |
