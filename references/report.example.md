# checker report: www.example.com

- Target: https://www.example.com (domain mode)
- Time: 2026-08-26 19:47 UTC • pages 24/24 (full) • sitemap sample 20 • crawl cap 5000 • 1 worker(s) × 1.0s interval
- Parameters: scripts/config.py; definitions: references/checklist/checklist.md
**Verdict: 🔴 15 (P0: 5) • ✅ 7 • ⚪ N.A. 2 • 👤 human review 2**

## 1. Site-level (once per site)

| ID | Priority | Check | Result | Evidence | Docs |
|---|---|---|---|---|---|
| C1 | P0 | robots.txt allows all AI crawler UAs | ✅ pass | all 18 UAs allowed | [C1 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C1.md) |
| C2 | P0 | sitemap reachable, no 4xx/5xx entries, truthful lastmod, <=50k URLs per file | 🔴 fail | sitemap /​sitemap.xml… [full](#c2) | [C2 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C2.md) |
| C3 | P0 | URL canonicalization: www/apex, http/https, trailing slash all 301 to one canonical host | 🔴 fail | http:​/​/​www.frontend.ap… [full](#c3) | [C3 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C3.md) |
| C26 | P0 | no Accept-Language redirects: every language version has its own fixed URL, no auto-jump | ✅ pass | sampled 5 page(s),… [full](#c26) | [C26 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C26.md) |
| C4 | P1 | Core Web Vitals pass: LCP<2.5s / INP<200ms / CLS<0.1 | ⚪ N.A. | need-​crux-​data (CrUX… [full](#c4) | [C4 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C4.md) |
| C5 | P1 | IndexNow key file reachable at the site root | ⚪ N.A. | need-​key-​declaration… [full](#c5) | [C5 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C5.md) |
| C6 | P1 | internal outlinks free of 4xx/5xx: links on pages don't point at broken pages | 🔴 fail | 1 dead internal… [full](#c6) | [C6 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C6.md) |
| C7 | P2 | llms.txt exists: a site directory for AI engines at the root | 🔴 fail | /​llms.txt → 404 | [C7 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C7.md) |

## 2. Per indexed page

| ID | Priority | Check | Result | Evidence | Docs |
|---|---|---|---|---|---|
| C8 | P0 | self-referencing canonical: every page names its own canonical URL, HTML and header agree | 🔴 fail | /​(canonical=​https:​/​/… [full](#c8) | [C8 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C8.md) |
| C9 | P0 | full body served server-side: readable without executing JS (no CSR shell) | 🔴 fail | /​assessment/​weight-… [full](#c9) | [C9 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C9.md) |
| C10 | P0 | cached HTML is a public non-personalized version: nothing user-specific in it | 🔴 fail | /​(two fetches diff… [full](#c10) | [C10 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C10.md) |
| C23 | P0 | indexed pages carry no noindex: neither meta robots nor X-Robots-Tag blocks | ✅ pass | 24/​24 pages pass | [C23 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C23.md) |
| C11 | P1 | title / description unique per page and within limits (<=60 / <=150) | 🔴 fail | /​(title 75 chars >… [full](#c11) | [C11 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C11.md) |
| C12 | P1 | JSON-LD: blocks parse, required fields present, no rejected types | 🔴 fail | /​(missing WebSite); /… [full](#c12) | [C12 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C12.md) |
| C13 | P1 | no soft 404s: never a 200 serving an empty or error page (retire via 301/410) | 🔴 fail | /​assessment/​weight-… [full](#c13) | [C13 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C13.md) |
| C14 | P1 | no anti-flicker script hiding the whole page (crawlers may get a blank) | ✅ pass | 24/​24 pages pass | [C14 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C14.md) |
| C16 | P1 | snippet controls: max-snippet:-1 + max-image-preview:large | 🔴 fail | /​(robots meta: index,… [full](#c16) | [C16 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C16.md) |
| C24 | P1 | viewport meta includes width=device-width | ✅ pass | 24/​24 pages pass | [C24 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C24.md) |
| C17 | P2 | heading hierarchy: exactly one h1, h2->h3 with no skipped levels | 🔴 fail | /​(skips h1→h4); /… [full](#c17) | [C17 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C17.md) |
| C18 | P2 | every img has explicit width/height + alt | 🔴 fail | /​(3/​20 imgs missing… [full](#c18) | [C18 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C18.md) |
| C19 | P2 | full Open Graph set + twitter:card: social preview cards complete and correct | 🔴 fail | /​blog/​healthy-​evening-… [full](#c19) | [C19 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C19.md) |
| C20 | P2 | redirect hops <=1: no chained redirects | ✅ pass | 24/​24 pages pass | [C20 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C20.md) |
| C15 | P2 | render cost not per-request: SSR needs CDN caching (s-maxage + SWR), SSG exempt | 🔴 fail | /​(Cache-​Control: no-… [full](#c15) | [C15 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C15.md) |
| C25 | P2 | no mixed content: no http:// subresources on HTTPS pages | ✅ pass | 24/​24 pages pass | [C25 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C25.md) |

## 3. Conditional (human review; flag / site-config triggered)

| ID | Priority | Check | Result | Evidence | Docs |
|---|---|---|---|---|---|
| C21 | P0 | YMYL trust block: author, review attribution, authoritative citations | 👤 human review | before launch, walk… [full](#c21) | [C21 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C21.md) |
| C22 | P1 | hreflang reciprocal pairs + x-default | 👤 human review | manually verify each… [full](#c22) | [C22 docs](https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references/C22.md) |

## Evidence (complete, untruncated)

The table holds summaries; this is the full set, one line per item. Full evidence also lands in checks.db.

### C2

**Check**: sitemap reachable, no 4xx/5xx entries, truthful lastmod, <=50k URLs per file

**Evidence** (complete, untruncated):

```
sitemap /sitemap.xml → 404
```

### C3

**Check**: URL canonicalization: www/apex, http/https, trailing slash all 301 to one canonical host

**Evidence** (complete, untruncated):

```
http://www.example.com/ → HTTPConnectionPool(host='www.example.com', port=80): Max retries exceeded with url: / (Caused by NameResolut
https://www.example.com/ → HTTPSConnectionPool(host='www.example.com', port=443): Max retries exceeded with url: / (Caused by NameResol
```

### C26

**Check**: no Accept-Language redirects: every language version has its own fixed URL, no auto-jump

**Evidence** (complete, untruncated):

```
sampled 5 page(s), same final URL under every Accept-Language (language differences live entirely in URLs — compliant)
```

### C4

**Check**: Core Web Vitals pass: LCP<2.5s / INP<200ms / CLS<0.1

**Evidence** (complete, untruncated):

```
need-crux-data (CrUX has no data for this site)
```

### C5

**Check**: IndexNow key file reachable at the site root

**Evidence** (complete, untruncated):

```
need-key-declaration (not registered in config.INDEXNOW_KEYS)
```

### C6

**Check**: internal outlinks free of 4xx/5xx: links on pages don't point at broken pages

**Evidence** (complete, untruncated):

```
1 dead internal links: ['/cdn-cgi/l/email-protection → 404 (source /terms)']
```

### C8

**Check**: self-referencing canonical: every page names its own canonical URL, HTML and header agree

**Evidence** (complete, untruncated):

```
/(canonical=https://example.net/ ≠ /)
/about(canonical=https://example.net/ ≠ /about)
/weight-loss(canonical=https://example.net/ ≠ /weight-loss)
/birth-control(canonical=https://example.net/ ≠ /birth-control)
/sleep(canonical=https://example.net/ ≠ /sleep)
…24 pages total
```

### C9

**Check**: full body served server-side: readable without executing JS (no CSR shell)

**Evidence** (complete, untruncated):

```
/assessment/weight-loss(298 chars < 500, likely CSR shell / thin content)
/assessment/birth(298 chars < 500, likely CSR shell / thin content)
/assessment/sleep(298 chars < 500, likely CSR shell / thin content)
```

### C10

**Check**: cached HTML is a public non-personalized version: nothing user-specific in it

**Evidence** (complete, untruncated):

```
/(two fetches diff non-empty (len 213141 vs 213141))
/about(two fetches diff non-empty (len 153761 vs 153761))
/weight-loss(two fetches diff non-empty (len 138166 vs 138166))
/birth-control(two fetches diff non-empty (len 140940 vs 140940))
/sleep(two fetches diff non-empty (len 159282 vs 159282))
…10 pages total
```

### C11

**Check**: title / description unique per page and within limits (<=60 / <=150)

**Evidence** (complete, untruncated):

```
/(title 75 chars > 60; desc 169 chars > 150)
/about(title 75 chars > 60)
/weight-loss(title 75 chars > 60)
/birth-control(title 75 chars > 60)
/sleep(title 75 chars > 60)
…14 pages total
title duplicated ×9 "Acme — Insurance in Plain Words | Acm…" e.g. /about
title duplicated ×5 "Blog Not Found | Acme" e.g. /blog/multilingual-care
title duplicated ×3 "Login | Acme | Acme" e.g. /assessment/weight-loss
desc duplicated ×14 "US-licensed physicians provide weight lo…" e.g. /about
desc duplicated ×3 "Access your treatments and care center" e.g. /assessment/weight-loss
```

### C12

**Check**: JSON-LD: blocks parse, required fields present, no rejected types

**Evidence** (complete, untruncated):

```
/(missing WebSite)
/about(missing WebSite)
/weight-loss(missing WebSite)
/birth-control(missing WebSite)
/sleep(missing WebSite)
…24 pages total
```

### C13

**Check**: no soft 404s: never a 200 serving an empty or error page (retire via 301/410)

**Evidence** (complete, untruncated):

```
/assessment/weight-loss(298 chars < threshold)
/assessment/birth(298 chars < threshold)
/assessment/sleep(298 chars < threshold)
retired sampling not wired (need-topic-queue)
```

### C16

**Check**: snippet controls: max-snippet:-1 + max-image-preview:large

**Evidence** (complete, untruncated):

```
/(robots meta: index, follow)
/about(robots meta: index, follow)
/weight-loss(robots meta: index, follow)
/birth-control(robots meta: index, follow)
/sleep(robots meta: index, follow)
…24 pages total
```

### C17

**Check**: heading hierarchy: exactly one h1, h2->h3 with no skipped levels

**Evidence** (complete, untruncated):

```
/(skips h1→h4)
/about(h1×0; skips h2→h4)
/weight-loss(h1×0; skips h2→h4)
/birth-control(h1×0; skips h2→h4)
/sleep(h1×0; skips h2→h4)
…21 pages total
```

### C18

**Check**: every img has explicit width/height + alt

**Evidence** (complete, untruncated):

```
/(3/20 imgs missing dimensions)
/weight-loss(2/12 imgs missing dimensions)
/birth-control(2/12 imgs missing dimensions)
/sleep(5/13 imgs missing dimensions)
/assessment/weight-loss(1/1 imgs missing dimensions)
…13 pages total
```

### C19

**Check**: full Open Graph set + twitter:card: social preview cards complete and correct

**Evidence** (complete, untruncated):

```
/blog/healthy-evening-habits(missing og:type,og:url)
/blog/language-barriers-healthcare(missing og:type,og:url)
/blog/online-healthcare(missing og:type,og:url)
/blog/semaglutide-vs-tirzepatide(missing og:type,og:url)
/blog/understanding-glp1(missing og:type,og:url)
```

### C15

**Check**: render cost not per-request: SSR needs CDN caching (s-maxage + SWR), SSG exempt

**Evidence** (complete, untruncated):

```
/(Cache-Control: no-cache, must-revalidate)
/about(Cache-Control: no-cache, must-revalidate)
/weight-loss(Cache-Control: no-cache, must-revalidate)
/birth-control(Cache-Control: no-cache, must-revalidate)
/sleep(Cache-Control: no-cache, must-revalidate)
…24 pages total
```

### C21

**Check**: YMYL trust block: author, review attribution, authoritative citations

**Evidence** (complete, untruncated):

```
before launch, walk C21's YMYL trust-block checklist (see references/checklist/references/C21.md) (trigger: ymyl=true)
```

### C22

**Check**: hreflang reciprocal pairs + x-default

**Evidence** (complete, untruncated):

```
manually verify each language pair points both ways + x-default (trigger: site has a multi-language config)
```
