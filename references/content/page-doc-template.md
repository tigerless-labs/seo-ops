# SEO appendix template (appended at the end of the page doc)

Ryan · 2026-08-26 · `accepted`

> This template holds **only the fields we ask content to supply** ([the T set](content-checklist.md)).
> **Delivery form: add an "Appendix · SEO" section at the end of the page doc** and paste the
> block below in whole — the original text above stays as is, wording and order untouched, and
> **the header gives up no room for us**.
> Each field's detailed page (why it exists, what qualifies, common mistakes) lives under [references/](references/).

## How to use

### Where it goes

```
page doc
  ├─ original text        ← your existing writing, untouched
  └─ Appendix · SEO       ← paste this template here in whole, one per page
```

- **At the end, not the top**: the top is the entry point for humans; SEO fields are input for
  machines and acceptance — two different audiences that shouldn't block each other. Start the
  original text on line one as always, and append this section when done
- **One contiguous block, not scattered**: don't split the fields into the body — item-by-item
  checks must see them all at once, and edits to the body must not brush against them
- The two site-level items are **one copy for the whole site**, delivered once, not in each
  page's appendix — see "1. Site-level"

### Filling rules

1. **Black text is the fields to fill; gray lines starting with `#` are notes** — notes explain
   the rules; keeping or deleting them doesn't affect acceptance, but **don't fill a note in as
   a field**.
2. **`{{ }}` marks a placeholder**; none should survive delivery — search for `{{` and you
   know what's left.
3. **What you can't fill, write "TBD · reason" — don't leave it blank, don't delete the line.**
   Delete the line and when the checker flags a red item there is no trail to who under-supplied;
   "TBD" at least says who is being waited on.
4. Conditional items that don't trigger: **keep the whole block, write `N.A.` as the value** — same reason.

---

## 1. Site-level (**one copy site-wide, delivered once**, not in each page's appendix)

T1 / T2 are not filled per page — but **they come first**: with no brand name settled, every
page's title and the entity in its JSON-LD go their own way. So deliver this copy first;
afterwards each page's appendix minds only its own page.

```yaml
# ---- T1 brand name + official accounts (data source for the Organization entity) ----
brand:
  legal_name: {{Acme Insurance Services, Inc.}}   # matches the business license / registration papers
  display_name: {{Acme}}                          # the one used on pages and in titles
  name_zh: {{Aikemei}}                               # if there is no Chinese name write "none" — don't invent one on the spot
  alias: {{AIS}}                                       # short name / alias; leave blank if none
  logo: {{https://www.example.com/logo.png}}
  # logo hard requirements: >=112×112 px, PNG/JPG (not SVG), square or near-square, opaque background

sameas:            # official accounts as full URLs, one per line, not handles; the three sites and the socials point at one entity
  - {{https://www.linkedin.com/company/acme}}
  - {{https://x.com/acme}}
  - {{https://www.youtube.com/@acme}}
  - {{https://www.crunchbase.com/organization/acme}}
# Only officially owned accounts; third-party write-ups and directory listings don't count — including them weakens the entity signal

# ---- T2 key-page list + one-line summaries (the value source for llms.txt) ----
key_pages:
  - group: {{Products}}
    pages:
      - url: {{/sort/f1}}
        summary: {{Health insurance options during the F1 student visa, with a school-requirement comparison}}
      - url: {{/sort/h1b}}
        summary: {{H1B work-visa insurance, focused on the gaps outside the employer plan}}
  - group: {{Guides}}
    pages:
      - url: {{/guide/f1-to-h1b}}
        summary: {{How insurance bridges the three status-transition (gap) scenarios}}
# summary <=30 chars: say what problem the page solves, no marketing copy
#   ✗ "This page introduces our excellent insurance products" — an AI reading it still doesn't know whether to click
#   ✓ "Health insurance options during the F1 student visa, with a school-requirement comparison"
# pSEO page sets are represented by their hub page, not listed one by one (stuff hundreds of scenario pages in and the point drowns)
# Which pages make the list is content's call (frontend generates the file)
```

**Maintenance cadence**: change T1 when it changes (rename, new logo, new official account);
add a line to T2 when a new key page ships. Neither repeats per page — but **say so when they
change**: they feed the JSON-LD of every page site-wide.

---

## 2. Per-page appendix (**required for every page**)

The block below is the full text of "Appendix · SEO" — copy it to the end of the page doc and change the values.

```yaml
# ============ Required per page ==============================================

# ---- T3 URL ----------------------------------------------------------------
url: {{/guide/f1-to-h1b}}
# all lowercase, hyphen-separated words, hierarchy reflects category, no dates or extensions; new URLs go through review (the one chance to change)

# ---- T4 YMYL verdict (the master switch for the conditional items) ----------
ymyl: {{true / false}}
# Content affecting the reader's health / finances / legal standing / physical safety → true. When unsure, mark true.
# A missed flag = all of C21 silently disabled, not an error

# ---- T5 title / description (finished copy, not an outline) -----------------
title: {{How to pick F1 student insurance | Acme}}
description: {{Walks the school waiver requirements one by one — what insurance to buy during F1, common denial scenarios, and when to switch plans.}}
# hard caps title <=60 / desc <=150 characters; Chinese pages in practice <=30 / <=75 chars by display width
# unique per page — no copy-pasting with two words changed

# ---- T6 H1 -----------------------------------------------------------------
h1: {{How to choose health insurance during your F1 student visa}}
# one per page, same topic as the title, wording may differ (the h1 reserves no room for the brand, so it can say more)

# ---- T8 language ------------------------------------------------------------
locales: {{[en, zh]}}
default_locale: {{en}}
locale_note: {{single-language pages write en only / zh only; bilingual pages delete this line}}
# "English only" and "the Chinese version isn't delivered yet" look identical in the data; unless it's written down, nobody knows whether to chase

# ---- T9 OG (defaults to title/desc + the body's lead image; fill only to differentiate) ----
og_title: {{blank = same as title}}
og_description: {{blank = same as description}}
og_image: {{blank = the body's lead image; designate one here when that image is an icon / wrong size / too long}}
# when designating: 1200×630 px, absolute URL, not blocked by robots

# ---- T10 dates (kept for GEO: AI citation clearly prefers recent content) ----
date_published: {{2026-03-12}}
date_modified: {{2026-08-26}}
# change only on substantive content updates (new content / numbers changed / process changed count; typo fixes, image swaps, layout tweaks don't)
# the visible "Updated ..." on the page and the JSON-LD dateModified share one source and one value; a mismatch is a C21 red

# ---- T7 outline (the h2/h3 hierarchy plus each section's conclusion) --------
outline:
  - h2: {{Do F1 students have to buy health insurance?}}
    lead: {{Most schools require it and the plan must satisfy the waiver terms; not mandated by federal law.}}
  - h2: {{What do school waiver requirements usually check?}}
    lead: {{Four things — annual limit, deductible, repatriation clause, coverage across the whole term.}}
    h3:
      - title: {{What deductible qualifies}}
        lead: {{Most schools require ≤$500...}}
      - title: {{Which number is the annual limit}}
        lead: {{...}}
  - h2: {{When can outside insurance replace the school plan?}}
    lead: {{Every waiver term met and proof filed before the waiver deadline.}}
# lead = the conclusion this section's first paragraph will state (one sentence of conclusion, not finished paragraph copy)
# an h3 must hang under some h2; no skipping levels (no h1 → h3, no h2 → h4)
# guide / FAQ content: h2 in the user's own words — the sentence someone would actually type into a search box
# FAQs go in standalone Q&A blocks (feeding FAQPage JSON-LD), question and answer written as a pair

# ---- T14 image alt (keyed by image filename, not "figure 1 / figure 2") -----
images:
  - file: {{gap-timeline.png}}
    alt: {{Timeline of the three F1-to-H1B status-gap scenarios and how insurance bridges each}}
  - file: {{claim-flow.png}}
    alt: {{The five claim steps — file documents, review, supplement, adjudicate, pay out}}
  - file: {{section-divider.svg}}
    alt: decorative              # mark pure decoration like this; frontend renders it as alt=""
# key by filename, not by number — images get added, removed, and moved in the body and every number shifts; filenames don't
# one sentence on what's in the image, not why it's here; typically 10-25 chars
# if the image carries key data / a process, write the key information into the alt —
#   AI can't read the image, only this line; only when this line is complete has the image's information truly made it onto the page

# ============ Conditional: fill when triggered; otherwise keep the block and write N.A. ====

# ---- T12 required when `ymyl: true` -----------------------------------------
author:
  name: {{Zhang Ming}}
  title: {{Licensed insurance advisor}}
  credential: {{California Insurance License #0M12345}}
  bio_url: {{/team/zhang-ming}}        # a dedicated author page is best; write "none" if there isn't one

reviewer:                              # delete the whole block if no real review happened; reason below
  name: {{Dr. Sarah Chen}}
  title: {{MD, Internal Medicine}}
  reviewed_on: {{2026-08-20}}

citations:
  - {{https://www.uscis.gov/…}}
  - {{https://www.healthcare.gov/…}}
# Author: real name + title + verifiable credential. "The Acme editorial team" is not an author
# The review must actually happen (R2 red line). Writing Dr. X when Dr. X never read the piece is fabricated credential endorsement —
#   better no reviewer than one who never reviewed
# citations use official sources: government sites, regulators, academic institutions, insurers' official policy pages

# ---- T13 required when the page shows a product with pricing ----------------
product:
  name: {{F1 Student Health Insurance · Standard Plan}}
  description: {{Covers outpatient, hospitalization, prescriptions, and repatriation; satisfies most university waiver requirements.}}
  price: {{89}}                        # no settled price → delete these two lines; don't write "negotiable"
  price_currency: {{USD}}
  price_period: {{month}}
  coverage_limit: {{500000}}           # annual limit
  deductible: {{250}}
  provider: {{Acme Insurance Services, Inc.}}
  valid_from: {{2026-01-01}}
  valid_through: {{2026-12-31}}
# one field per slot — don't write a paragraph for engineers to dig numbers out of; numbers carry no currency symbols or units
# every value must be visible on the page — $89 in the JSON-LD while the page says "from $79" is markup inconsistent with the visible page
# AggregateRating (user ratings) is banned site-wide; don't deliver it. Show testimonials if you like, but not in structured data
```

## 3. Extra notes for special page types (**parentheses are explanation, not fields to fill**)

> **(Note: page type is not a supply field.** Since 2026-08-25 content no longer declares page
> types per page — Google doesn't consume `WebPage` subtypes, and per-page upkeep fails silently
> when missed. So the table below **is not asking you to mark "this is a product page"** — it's
> a writing reference: what these pages tend to miss, glance at it. The real triggers remain the
> `ymyl` flag and "is that thing on the page".**)**

| Page type | Extra attention for this type | Which items |
|---|---|---|
| guide / article page | has a body, has an author → publish and modified dates **as a pair**; h2 in the reader's own words | T10 · T7 (· T12 if ymyl) |
| FAQ page / any page with an FAQ block | **Q&A written verbatim as pairs**, each pair its own block. (Note: answers go into FAQPage JSON-LD; feeding machines what humans can't see is a violation, so the same Q&A must be visible on the page) | T7 · C12 |
| product / plan page | uses the `product` field block, one field per slot. (Note: price, coverage limit, and deductible are the comparisons readers care most about; buried in a description they can't be cited) | T13 |
| pSEO bulk scenario pages | **treated exactly like human-written pages** — one appendix per page, unique title/desc, alt per image. (Note: represented in llms.txt by the hub page; hundreds of scenario pages are not listed one by one) | T5 · T14 · T2 |
| author / team page | each person: real name + title + verifiable credential, in **the same style** as article-page bylines | T12 |
| category / list / comparison page | list items must be visible and clickable on the page; don't ship just a comparison image. (Note: AI can't read what's in the image) | T14 · T7 |
| home page | brand-name spelling follows the site-level copy; no ad-hoc variants | T1 |
| about / brand-story page | usually `ymyl: false`, but **company credentials and license numbers must still match the certificates** | T4 |
| Chinese / bilingual pages | title <=30 chars, desc <=75 chars (display width); en/zh delivered together, no one-sided delivery | T5 · T8 |

---

> **Before delivering, walk through [content-checklist.md](content-checklist.md) item by item** —
> that checklist is the self-check sheet; each entry is tagged with the downstream C check it
> feeds. This template doesn't repeat it — **the same requirements written in two places will
> drift apart sooner or later**. The one thing said only here: before delivering, search for
> `{{` — you should find none.
>
> Acceptance path: after frontend lands the page, the checker runs the C set; red items trace
> back through the T set's "Downstream" column — so you know whether content under-supplied or
> frontend didn't land it. Hence **"TBD" beats blank, and blank beats a deleted line**.
