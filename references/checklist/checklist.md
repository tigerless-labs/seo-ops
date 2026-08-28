# Checklist (C set, static structure checks)

> **Static structure checks** on the machine-readable surface of the final HTTP/HTML output — only "is the required structure present and correct". Who produced it doesn't matter; content quality and everything human-perceivable are out of scope (full boundary: [SKILL.md](../../SKILL.md) "Scope"; the human gates: [redlines.md](../../redlines.md)). **All green ≠ fully compliant.**
> The checker implements sections 1 and 2 (each item lands in the `checks` table); section 3 is human review (C22's target-URL status part is machine-run, the reciprocity judgment stays human).
> Grouping: **site-level** (once per site) / **per indexed page** / **conditional** (triggered by a flag or site config, never by page type).
> Each item's full write-up lives in [references/](references/) (introduction + implementation guidance); this table is the index and verdict overview.

## 1. Site-level (once per site)

| ID | Priority | Check | Verdict method | Layer |
|---|---|---|---|---|
| C1 | P0 | robots.txt allows all AI crawler UAs | fetch + per-UA comparison | checker |
| C2 | P0 | sitemap reachable, no 4xx/5xx entries, truthful lastmod, <=50k URLs per file | fetch + **no-redirect** sampling + lastmod coverage/dispersion/single-day cluster + per-shard entry count | checker |
| C3 | P0 | URL canonicalization: www/apex, http/https, trailing slash all 301 to one canonical host | four-variant curl (**needs a real domain; staging/no-domain runs record N.A.**) | checker |
| C26 | P0 | no Accept-Language redirects: every language version has its own fixed URL, no auto-jump | fetch sampled pages once each with en-US / zh-CN, compare final_url; divergence = auto-redirect by guessed language | checker |
| C4 | P1 | Core Web Vitals pass: LCP<2.5s / INP<200ms / CLS<0.1 | CrUX API (**needs a domain plus real post-launch traffic (about 28 days); N.A. before that**) | checker |
| C5 | P1 | IndexNow key file reachable at the site root | fetch the key file, 200 and content == key (**the site must register its key in config.INDEXNOW_KEYS; unregistered records N.A.**) | checker |
| C6 | P1 | outlinks free of 4xx/5xx: links on pages don't point at broken pages (external sampled, conclusive-only) | crawl the internal link graph; in-site links whose targets are outside the sitemap must return <400; external links sampled, only a conclusive 404/410 counts red; incomplete crawl records N.A. | checker |
| C7 | P2 | llms.txt exists: a site directory for AI engines at the root | fetch + format check | checker + human review |
| C28 | P2 | security response headers: HSTS + CSP + nosniff + frame protection + Referrer-Policy | check the site root's response headers (http/local origins record N.A.) | checker |
| C29 | P2 | URL hygiene: sitemap URLs lowercase, hyphen-separated, no raw non-ASCII, no query params | regex scan of the sitemap URL list (zero extra fetches) | checker |

## 2. Per indexed page

| ID | Priority | Check | Verdict method | Layer |
|---|---|---|---|---|
| C8 | P0 | self-referencing canonical: every page names its own canonical URL, HTML and header agree | fetch the page, compare `<link rel=canonical>` × the `Link: rel="canonical"` response header | checker |
| C9 | P0 | full body served server-side: readable without executing JS (no CSR shell) | no-JS fetch >= 90% of the rendered version | checker |
| C10 | P0 | cached HTML is a public non-personalized version: nothing user-specific in it | two anonymous fetches of the same URL diff empty (sampled) | checker |
| C23 | P0 | indexed pages carry no noindex: neither meta robots nor X-Robots-Tag blocks | fetch the page, check robots/googlebot meta + the `X-Robots-Tag` response header | checker |
| C27 | P0 | valid head: only head-legal elements inside head (an invalid element ends head parsing early) | parse the head region, flag elements outside title/meta/link/script/style/base/noscript/template | checker |
| C11 | P1 | title / description unique per page and within limits (<=60 / <=150) | sample-set comparison | checker |
| C12 | P1 | JSON-LD: blocks parse, required fields present, no rejected types | parse ld+json (presence / syntax / base group and per-type fields / negative scan) | checker + human review |
| C13 | P1 | no soft 404s: never a 200 serving an empty or error page (retire via 301/410) | content-length threshold + word-count threshold (thin content) + retired-entry sampling | checker |
| C14 | P1 | no anti-flicker script hiding the whole page (crawlers may get a blank) | grep known patterns + rendered first screen non-blank | checker |
| C16 | P1 | snippet controls: max-snippet:-1 + max-image-preview:large | fetch the page, check robots meta | checker |
| C24 | P1 | viewport meta includes width=device-width | fetch the page, check meta | checker |
| C17 | P2 | heading hierarchy: exactly one h1, h2->h3 with no skipped levels | parse the DOM heading sequence | checker |
| C18 | P2 | every img has explicit width/height + alt; sampled image files within the weight budget | DOM/template grep + sampled image HEAD Content-Length vs budget | site CI + checker |
| C19 | P2 | full Open Graph set + twitter:card: social preview cards complete and correct | fetch the page, check meta; image declared 1200×630; og:type × JSON-LD article types cross-checked | checker |
| C20 | P2 | redirect hops <=1: no chained redirects | count redirect chain length while fetching | checker |
| C15 | P2 | render cost not per-request: SSR needs CDN caching (s-maxage + SWR), SSG exempt | curl response headers × the declared rendering strategy | checker |
| C25 | P2 | no mixed content: no http:// subresources on HTTPS pages | scan the URL scheme of img/script/iframe/link etc. subresources | checker |
| C30 | P2 | link hygiene: every anchor has text (or img alt / aria-label); external target=_blank carries rel=noopener | DOM anchor scan | checker |

## 3. Conditional (flag / site-config triggered)

| ID | Priority | Check | Trigger | Verdict method | Layer |
|---|---|---|---|---|---|
| C21 | P0 | YMYL trust block: author, review attribution, authoritative citations | `ymyl=true` | before launch, walk C21's YMYL trust-block checklist (see references/checklist/references/C21.md) | human review |
| C22 | P1 | hreflang reciprocal pairs + x-default | site has a multi-language config | checker fetches every hreflang target URL found on sampled pages (must be 200, no redirect, no throttle); reciprocity closure + x-default remain manual | checker + human review |

> Numbering discipline: IDs are **permanent** (referenced by the `checks` table and waivers): only extend (next is C31), never recycle, never renumber.
> **Merge when you can**: a new check with the **same priority + same layer + the same fetch action** as an existing item folds into that item as an extended verdict, taking no new ID
> (the five 2026-08-25 cases on C2/C6/C8/C18/C19 did exactly this); a different verdict action or priority earns a new ID.
> Row order = priority groups (P0→P1→P2), semantically adjacent within a group;
> new items take the next ID and slot into their section's priority band.
> Priority scale: **P0 = existence/incident layer** (uncrawlable, unindexable, compliance or privacy risk — hurts the whole site);
> **P1 = performance layer** (ranking and citation discounted); **P2 = optimization**.
> Layer "checker" = the manually run check script (checker/); "site CI" = each repo's engineering side.

## Authority sources (official docs, C set)

| Rule | Source |
|---|---|
| C set overall | [Google Search Essentials](https://developers.google.com/search/docs/essentials) (formerly Webmaster Guidelines) |
| C12 structured data | [Google Structured Data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) + [schema.org](https://schema.org) |
| C8 canonical / C2 sitemap / robots | [Google Crawling & Indexing docs](https://developers.google.com/search/docs/crawling-indexing), [sitemaps.org](https://www.sitemaps.org) (the protocol itself) |
| C22 hreflang / C26 language redirects | [Google localized-versions guide](https://developers.google.com/search/docs/specialty/international/localized-versions) (explicit: don't auto-redirect by guessed language; declare with hreflang + let users choose) |
| C4 CWV | [web.dev/vitals](https://web.dev/articles/vitals) (Chrome team; the source of metric definitions and thresholds) |
| C1 AI crawler UAs | [OpenAI bots](https://platform.openai.com/docs/bots), [Perplexity crawlers](https://docs.perplexity.ai/guides/bots), Anthropic support's ClaudeBot page, [Google crawler list](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers) (Google-Extended) |
| C16 / C23 robots directives | [Google robots meta tag docs](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag) (`max-snippet`/`noindex` and `X-Robots-Tag` share one source) |
| C18 image alt | [Google image SEO best practices](https://developers.google.com/search/docs/appearance/google-images) |
| C24 viewport | [Google: mobile-friendly](https://developers.google.com/search/docs/appearance/mobile-friendly) |
| C25 mixed content | [MDN: Mixed content](https://developer.mozilla.org/docs/Web/Security/Mixed_content) (the normative description of browser blocking behavior) |
| C19 OG | [ogp.me](https://ogp.me) (The Open Graph protocol) + each social platform's card docs |
| C5 IndexNow (C2's companion) | [indexnow.org](https://www.indexnow.org) (the open protocol led by Microsoft/Bing) |
| C7 llms.txt | [llmstxt.org](https://llmstxt.org) (a community convention, not an official standard — the only item with no big-vendor backing) |
| C10/C20 | Search Essentials anti-cloaking / redirect guidance (under the C-set overall link) |
| C27 head validity | [Google: use valid HTML in the head](https://developers.google.com/search/docs/crawling-indexing/valid-page-metadata) (explicit: an invalid element ends head processing, everything after it is ignored) + [WHATWG HTML spec: the head element](https://html.spec.whatwg.org/multipage/semantics.html#the-head-element) |
| C28 security headers | [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/) + [MDN HTTP headers](https://developer.mozilla.org/docs/Web/HTTP/Headers) (per-header semantics) |
| C29 URL hygiene | [Google: URL structure best practices](https://developers.google.com/search/docs/crawling-indexing/url-structure) (hyphens over underscores, lowercase, percent-encode non-ASCII) |
| C30 link hygiene | [Google SEO Starter Guide: use good anchor text](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) + [MDN: rel=noopener](https://developer.mozilla.org/docs/Web/HTML/Attributes/rel/noopener) |

Dead links or policy updates count as harness changes; update this table after human review.
