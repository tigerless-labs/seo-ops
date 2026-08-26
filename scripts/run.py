#!/usr/bin/env python3
"""checker — a manually run check script. Usage and verdict semantics live in SKILL.md at the skill root.

Item definitions live in references/checklist/checklist.md (**the single source of truth**);
this script implements its machine items C1-C20, C23-C26; C21/C22 are human-review items,
listed in the report but never judged.
The two are aligned by verify_checklist_sync() on every start — check logic can't be
auto-generated (each one is hand-written), but "which items exist, what priority, which
section" must match; on mismatch it shouts on stdout.

  python3 scripts/run.py                       # config.TARGET empty → run every site in sites.yaml
  python3 scripts/run.py --site example-com    # run just one site from sites.yaml
  python3 scripts/run.py --target http://localhost:3000   # single-site override (local mode auto-detected)

Writes nothing inside the package (this checker gets copied into the skill; a skill
update = whole-package overwrite). Two external directories:
  <config-dir> default ~/.config/seo-ops     — config (what you feed the tool)
    ├── sites.yaml                        — site roster (multi-site only)
    └── .env                              — API keys (already-exported env vars win)
  <state-dir>  default ~/Documents/seo-ops   — outputs (what the tool emits), for humans
    └── out/report-<site>-<date>.md       — a form isomorphic to the checklist (three sections; result + evidence)
        out/checks.db                     — checks snapshots (SQLite, schema in SKILL.md)
  The boundary is config vs output; also, Documents is often cloud-synced, so keys must not live there.

Three invariants:
  1. **Three-state verdicts** pass / fail / N.A.(reason) — "not tested" and "nothing wrong"
     must never blur into one green.
  2. **Purely deterministic, zero LLM** — fetch → regex/json parsing → threshold comparison →
     markdown assembly. Two runs on the same site and config must be byte-identical; that is
     what lets it serve as acceptance evidence and be argued over with contractors.
  3. **Crawler's viewpoint** — no cookies stored, no Accept-Language sent. The checker must
     see what Googlebot sees, not what "a user who already browsed around" sees (see references/C26.md).

Reads only the live HTTP/HTML output, stack-agnostic; real browser UA (Cloudflare blocks
fake crawler UAs). Sequential by default (config.FETCH_CONCURRENCY = 1); concurrency is a
reserved seam — redo the concurrency output-diff before enabling it.
"""
import argparse, collections, json, re, sqlite3, sys, threading, time, traceback, unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.cookiejar import DefaultCookiePolicy
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests, yaml

# Once installed as a skill this directory may be read-only, and "zero writes" is a promise
# we made to users — yet import writes __pycache__ next door as a side effect. Verified:
# installing into ~/.claude/skills/ did produce it. Bytecode caching has no perceptible
# benefit for this network-I/O-bound script; turn it off and the promise holds.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as CFG

def _resolve_paths():
    """Locate the data root — i.e. **the directory that contains checklist/checklist.md**;
    `ai-crawlers.yaml` and `sites.example.yaml` live under it too.

    Why probe instead of hard-coding: this script has lived through three layouts
    (tools/check inside the monorepo, a standalone repo root, and now the skill spec's
    scripts/ + references/), and the relative position of script vs data changed every
    time. Hard-code one path and every move means editing code — miss one spot and it is
    a runtime crash.
      skill spec     :  scripts/run.py       +  references/checklist/checklist.md
      standalone repo:  checker/run.py       +  checklist/checklist.md
      monorepo       :  tools/check/run.py   +  docs/checklist/checklist.md
    """
    here = Path(__file__).resolve()
    cands = (here.parents[1] / "references",      # skill spec (current)
             here.parents[1],                     # standalone repo root
             here.parents[2] / "docs",            # monorepo
             here.parents[2])
    for root in cands:
        md = root / "checklist" / "checklist.md"
        if md.exists():
            return root, md
    return cands[0], cands[0] / "checklist" / "checklist.md"

ROOT, CHECKLIST_MD = _resolve_paths()
NOW = datetime.now(timezone.utc)

# ───────────────────────── fetch layer ─────────────────────────

class Fetcher:
    """Concurrent fetcher.

    **Sequential by default (config.FETCH_CONCURRENCY = 1)** — `map()` then runs a plain
    list comprehension, no threads. Concurrency is only a reserved seam for future
    thousand-page sites; before enabling it, redo the concurrency output-diff.

    Three guarantees that keep output byte-reproducible once the seam opens (the checker
    is an acceptance tool — two runs must yield the same report):
      1. `map()` returns in input order — concurrency changes fetch timing, never result order;
      2. only one thread fetches a given URL, the rest wait for its result (per-key lock) —
         never "two different snapshots of the same page";
      3. one Session per thread (requests.Session is not thread-safe).
    Throttle semantics: `sleep` is the interval between two requests of **a single worker**;
    overall QPS ≈ workers / sleep.
    """
    def __init__(self, sleep, workers):
        self.local = threading.local()
        self.sleep = sleep
        self.workers = max(1, workers)
        self.cache = {}
        self.throttled = 0        # requests rejected with 429/503; >0 = this run is discounted, the report header must say so
        self._extra = 0.0         # adaptive extra interval: multiplicative backoff on throttle, additive recovery on streaks (AIMD)
        self._ok = 0              # recovery counter
        self._lock = threading.Lock()
        self._keylocks = {}

    def _session(self):
        s = getattr(self.local, "s", None)
        if s is None:
            s = requests.Session()
            s.headers["User-Agent"] = CFG.UA
            # Never store cookies: a crawler is a **stateless first visit** every time; it
            # never carries the previous page's state. Reusing cookies makes the checker
            # behave like a user — 2026-08-25, measured on the pilot site:
            # cookieless first visit to /home hops twice to /cn (Chinese, Set-Cookie records
            # the language); with cookies it hops once to / (English). Session reuse means
            # "whichever page got fetched first" decides the whole report, and the result
            # drifts with concurrency scheduling.
            s.cookies.set_policy(DefaultCookiePolicy(allowed_domains=[]))
            # Explicitly do not send Accept-Language (None in requests = drop the header).
            # The default already omits it, but that is "right by accident" — pin it down,
            # so that someone adding a default header later can't silently switch the
            # viewpoint: Googlebot crawls with "no language preference"; adding this header
            # turns it into a user's viewpoint (C26 measures exactly that difference).
            s.headers["Accept-Language"] = None
            self.local.s = s
        return s

    def _fetch(self, url, redirects, headers=None, attempt=0):
        with self._lock:
            extra = self._extra
        time.sleep(self.sleep + extra)
        try:
            r = self._session().get(url, timeout=CFG.REQUEST_TIMEOUT,
                                    allow_redirects=redirects, headers=headers)
            out = {"status": r.status_code, "text": r.text, "headers": dict(r.headers),
                   "final_url": r.url, "hops": len(r.history), "err": None}
        except Exception as e:
            return {"status": None, "text": "", "headers": {}, "final_url": url,
                    "hops": 0, "err": str(e)[:120]}
        if out["status"] not in CFG.THROTTLE_STATUSES:
            with self._lock:                      # the "additive recovery" half of AIMD
                if self._extra:
                    self._ok += 1
                    if self._ok >= CFG.THROTTLE_RECOVER_AFTER:
                        self._ok = 0
                        self._extra = max(0.0, self._extra - CFG.THROTTLE_BACKOFF / 2)
        else:
            with self._lock:
                self.throttled += 1
                self._ok = 0
                self._extra = min(self._extra * 2 + 0.5, CFG.THROTTLE_MAX_SLEEP)   # multiplicative backoff
            if attempt < CFG.THROTTLE_RETRIES:
                ra = out["headers"].get("Retry-After") or out["headers"].get("retry-after")
                try:
                    wait = float(ra)
                except (TypeError, ValueError):
                    wait = CFG.THROTTLE_BACKOFF * (2 ** attempt)
                time.sleep(min(wait, 30))
                return self._fetch(url, redirects, headers, attempt + 1)
        return out

    def get(self, url, redirects=True, force=False, headers=None):
        """Returns dict(status, text, headers, final_url, hops, err); cached.
        force=True (C10's double fetch) bypasses the cache and does not write back —
        that call's whole point is "fetch again and see if it changed"."""
        if force:
            return self._fetch(url, redirects, headers)
        key = (url, redirects, tuple(sorted((headers or {}).items())))
        with self._lock:
            if key in self.cache:
                return self.cache[key]
            kl = self._keylocks.setdefault(key, threading.Lock())
        with kl:
            with self._lock:
                if key in self.cache:            # someone finished it while we waited for the lock
                    return self.cache[key]
            out = self._fetch(url, redirects, headers)
            with self._lock:
                self.cache[key] = out
            return out

    def map(self, fn, items):
        """Run fn(item) concurrently, **returning in the original order of items**;
        degrades to sequential when workers<=1 (for debugging)."""
        items = list(items)
        if self.workers <= 1 or len(items) <= 1:
            return [fn(i) for i in items]
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            return list(ex.map(fn, items))

# ───────────────────────── HTML parsing helpers ─────────────────────────

def strip_text(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>",
               "", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def metas(html):
    """meta name/property → content (lower-cased keys; first wins on duplicates)."""
    out = {}
    for m in re.finditer(r'<meta\s+[^>]*>', html, flags=re.I):
        tag = m.group(0)
        k = re.search(r'(?:name|property)\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
        v = re.search(r'content\s*=\s*["\']([^"\']*)["\']', tag, flags=re.I)
        if k and v:
            out.setdefault(k.group(1).strip().lower(), v.group(1).strip())
    return out

def ld_blocks(html):
    """[(parsed_or_None, raw)]; parsed is the json.loads result."""
    out = []
    for b in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        html, flags=re.S | re.I):
        try:
            out.append((json.loads(b.strip()), b))
        except Exception:
            out.append((None, b))
    return out

def ld_types(parsed):
    types = []
    def walk(n):
        if isinstance(n, dict):
            t = n.get("@type")
            if isinstance(t, str): types.append(t)
            elif isinstance(t, list): types.extend(x for x in t if isinstance(x, str))
            for v in n.values(): walk(v)
        elif isinstance(n, list):
            for v in n: walk(v)
    walk(parsed)
    return types

def canonical_href(html):
    m = re.search(r'<link\s+[^>]*rel=["\']canonical["\'][^>]*>', html, flags=re.I)
    if not m:
        m2 = re.search(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']',
                       html, flags=re.I)
        return m2.group(1) if m2 else None
    h = re.search(r'href=["\']([^"\']+)["\']', m.group(0), flags=re.I)
    return h.group(1) if h else None

def header_canonical(headers):
    """The HTTP-channel canonical: `Link: <url>; rel="canonical"`.
    When it coexists with HTML's <link rel=canonical> and disagrees, the engine picks
    one on its own — and control is lost (C8)."""
    v = headers.get("Link") or headers.get("link") or ""
    for part in v.split(","):
        if re.search(r'rel\s*=\s*"?canonical"?', part, flags=re.I):
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1).strip()
    return None

def norm_url(u):
    """Normalization for comparison: drop the fragment, strip the path's trailing slash (except root)."""
    p = urlparse(u)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return f"{p.scheme}://{p.netloc}{path}" + (f"?{p.query}" if p.query else "")

def headings(html):
    return [int(m.group(1)) for m in re.finditer(r"<h([1-6])[\s>]", html, flags=re.I)]

def throttled(r):
    """429/503 = we fetched too fast, not a broken page — no verdict may ever count it as fail."""
    return r["status"] in CFG.THROTTLE_STATUSES

def is_local(host):
    if host in ("localhost",) or host.endswith(".local"):
        return True
    return bool(re.match(r"^(\d{1,3}\.){3}\d{1,3}$|^127\.|^\[?::1\]?$", host))

# ───────────────────────── result collection ─────────────────────────

PASS, FAIL, NA, HUMAN = "pass", "fail", "N.A.", "human review"

def as_items(ev):
    """Evidence is always list[str], one item per finding, **never split within an item**.

    The old version flattened evidence internally with `";".join(...)` and then guessed
    the structure back with `split(";")` when rendering the appendix — but evidence text
    itself contains semicolons ("15/15 pages pass (heuristic; the 90% ratio verdict awaits
    headless)", "/ (81/81 imgs missing dimensions; 7/81 imgs missing the alt attribute)"),
    so lines got split mid-parenthesis, leaving brackets unclosed.
    That is an in-band delimiter: the separator shares a channel with the data, and the
    moment the data contains the same character they are indistinguishable — picking a
    rarer separator only shrinks the collision odds, it doesn't fix anything.
    The only real fix is to skip that round-trip: carry structure the whole way and
    **join only at the final render step**.
    """
    if ev is None or ev == "":
        return []
    return [ev] if isinstance(ev, str) else [x for x in ev if x]


class Result:
    def __init__(self):
        self.rows = {}          # cid → (status, list[str])
        self.page_rows = []     # (url, cid, status, list[str])

    def set(self, cid, status, evidence=""):
        self.rows[cid] = (status, as_items(evidence))

    def page(self, url, cid, status, evidence=""):
        self.page_rows.append((url, cid, status, as_items(evidence)))

def agg_pages(result, cid, pages_status):
    """Aggregate per-page results into an item result: any fail → fail (evidence lists
    up to 5 violating pages); an empty set = N.A., never pass."""
    if not pages_status:
        result.set(cid, NA, "no-pages (page sample empty or every fetch failed)")
        return
    fails = [(u, as_items(ev)) for u, st, ev in pages_status if st == FAIL]
    if fails:
        # **One page = one item.** A page's multiple problems get joined inside the same
        # item (in parentheses), never a new item — in the appendix one line is one page,
        # so a reader sees at a glance which pages are broken.
        items = [f"{u}({'; '.join(evs)})" if evs else u for u, evs in fails[:5]]
        if len(fails) > 5:
            items.append(f"…{len(fails)} pages total")
        result.set(cid, FAIL, items)
    else:
        oks = [1 for _, st, _ in pages_status if st == PASS]
        result.set(cid, PASS, f"{len(oks)}/{len(pages_status)} pages pass")
    for u, st, ev in pages_status:
        result.page(u, cid, st, ev)

# ───────────────────────── the checks ─────────────────────────

def check_site(site, f, args):
    """site: dict(id, origin, declared_host, rendering, samples[{url,ymyl,locale,pair}], sitemap)"""
    R = Result()
    origin = site["origin"].rstrip("/")
    host = urlparse(origin).netloc
    local = is_local(host.split(":")[0])
    mode = "local mode" if local else "domain mode"

    # ---------- precondition: is the site root reachable ----------
    # No connection, no report. A mistyped domain would otherwise degrade into "a few
    # reds + a pile of N.A." — which looks like a health check but tested nothing.
    # **A half-true report is worse than no report.** Only connection-layer failures
    # count here (status is None: DNS/timeout/refused); a 500 means "alive but broken"
    # and should be tested as usual.
    root = f.get(origin + "/")
    if root["status"] is None:
        raise RuntimeError(f"site root unreachable ({origin}/): {root['err']}")

    # ---------- page sample set: sites.yaml samples + sitemap sampling ----------
    sitemap_entries, sitemap_err, sitemap_shards = collect_sitemap(site, f, local, origin)
    sitemap_urls = [u for u, _ in sitemap_entries]
    limit = args.page_sample if args.page_sample > 0 else None   # 0 = full (every page the sitemap registers)
    sample_pages = [{**s, "url": origin + s["url"]} for s in site.get("samples", [])]
    seen = {norm_url(p["url"]) for p in sample_pages}
    for u in sitemap_urls:
        if limit is not None and len(sample_pages) >= limit: break
        u2 = map_host(u, site, local, origin)
        if norm_url(u2) not in seen:
            sample_pages.append({"url": u2})
            seen.add(norm_url(u2))
    def fetch_page(p):                       # the biggest fetch volume: in full mode = every page the sitemap registers
        r = f.get(p["url"])
        if r["err"] or not r["status"]:
            return {**p, "fetch": r, "html": "", "text": ""}
        return {**p, "fetch": r, "html": r["text"], "text": strip_text(r["text"])}
    pages = f.map(fetch_page, sample_pages[:limit] if limit else sample_pages)
    ok_pages = [p for p in pages if p["fetch"]["status"] == 200 and p["html"]]
    thr_pages = [p for p in pages if throttled(p["fetch"])]
    R.fetch_fails = [f"{p['url']} → {p['fetch']['status'] or p['fetch']['err']}"
                     for p in pages if p["fetch"]["status"] != 200 and not throttled(p["fetch"])]
    R.thr_pages = len(thr_pages)

    # ---------- C1 robots.txt × ai-crawlers.yaml ----------
    crawlers = yaml.safe_load((ROOT / "ai-crawlers.yaml").read_text())["crawlers"]
    all_uas = [ua for group in crawlers.values() for ua in group]
    r = f.get(origin + "/robots.txt")
    if r["status"] is None:
        # A connection-layer failure ≠ 404. Couldn't fetch it = didn't test it; never
        # report green on the "no file = allow all by default" rule.
        R.set("C1", NA, f"unreachable (robots.txt fetch failed: {r['err']})")
    elif r["status"] != 200:
        R.set("C1", PASS, f"robots.txt {r['status']} (no file = allow all by default; "
                          f"but the spec expects a template-generated robots.txt — add one)")
    else:
        blocked = [ua for ua in all_uas if robots_blocks(r["text"], ua)]
        if blocked:
            R.set("C1", FAIL, f"blocked UAs: {', '.join(blocked)}")
        else:
            R.set("C1", PASS, f"all {len(all_uas)} UAs allowed")

    # ---------- C2 sitemap ----------
    if sitemap_err:
        R.set("C2", FAIL, sitemap_err)
    elif not sitemap_urls:
        R.set("C2", FAIL, "sitemap has no entries")
    else:
        problems = []
        problems += lastmod_problems(sitemap_entries)
        over = [(s, n) for s, n in sitemap_shards if n > CFG.SITEMAP_MAX_URLS_PER_FILE]
        if over:
            problems.append("shard over the protocol cap (must move to index shards): " +
                            "; ".join(f"{s} {n} entries > {CFG.SITEMAP_MAX_URLS_PER_FILE}"
                                      for s, n in over[:3]))
        def probe(u):
            # Do not follow redirects: the sitemap's semantics is "these URLs ARE the
            # canonical addresses" — the **starting point** must be 200. Following would
            # mean judging only the destination — an entry that 302s elsewhere would
            # count as reachable (the old implementation's hole).
            rr = f.get(map_host(u, site, local, origin), redirects=False)
            if throttled(rr):
                return None                       # throttling never counts as a broken entry
            if rr["status"] == 200:
                return None
            if rr["status"] and 300 <= rr["status"] < 400:
                return f"{u} → {rr['status']} redirects to {rr['headers'].get('Location', '?')} (entries should themselves be canonical)"
            return f"{u} → {rr['status'] or rr['err']}"
        bad = [x for x in f.map(probe, sitemap_urls[:args.sitemap_sample]) if x]
        if bad:
            problems += [f"sample problem: {b}" for b in bad[:5]]
        R.set("C2", FAIL if problems else PASS,
              problems or
              f"{len(sitemap_urls)} entries; {min(len(sitemap_urls), args.sitemap_sample)} sampled reachable")

    # ---------- C3 canonicalization 301 ----------
    if local:
        R.set("C3", NA, "need-domain (local mode)")
    else:
        bare = host[4:] if host.startswith("www.") else host
        variants = [f"http://{bare}/", f"http://www.{bare}/",
                    f"https://{bare}/", f"https://www.{bare}/"]
        finals, errs = set(), []
        for v, rr in zip(variants, f.map(f.get, variants)):
            if rr["err"]:
                errs.append(f"{v} → {rr['err']}")
            else:
                finals.add(norm_url(rr["final_url"]))
        if errs:
            R.set("C3", FAIL, errs[:3])
        elif len(finals) == 1:
            R.set("C3", PASS, f"all four variants converge → {finals.pop()}")
        else:
            R.set("C3", FAIL, f"divergent destinations: {sorted(finals)}")

    # ---------- C4 CWV ----------
    if local:
        R.set("C4", NA, "need-domain (local mode)")
    elif not CFG.CRUX_API_KEY:
        R.set("C4", NA, "need-crux-key (no CrUX API key in config)")
    else:
        R.set("C4", *crux_check(site, f))

    # ---------- C5 IndexNow key ----------
    key = CFG.INDEXNOW_KEYS.get(site["id"])
    if not key:
        R.set("C5", NA, "need-key-declaration (not registered in config.INDEXNOW_KEYS)")
    else:
        rr = f.get(f"{origin}/{key}.txt")
        ok = rr["status"] == 200 and key in rr["text"]
        R.set("C5", PASS if ok else FAIL, f"/{key}.txt → {rr['status']}")

    # ---------- C6 internal outlinks free of 4xx/5xx (the part outside the sitemap) ----------
    # Division of labor with C2: **C2 judges "are the URLs declared for indexing reachable"
    # (inside the sitemap); C6 judges "are the links actually present on pages reachable"
    # (the link graph).** They overlap on in-sitemap URLs, so here targets that hit the
    # sitemap get dropped, keeping only what C2 structurally cannot see —
    # stale links left in hubs, mistyped hrefs, inbound links never cleaned after retirement.
    #
    # 2026-08-25 also removed the orphan verdict: it concludes from "not seen", while
    # incomplete crawls are the norm (throttling / caps / login state / language clusters)
    # — measured on the pilot site it reported 138 orphans, root cause being C26 locking
    # the crawler into the /cn cluster; adding internal links cures nothing. Dead links
    # are the opposite: only what was **seen** gets reported.
    crawled, _disc, capped, dead_links, crawl_thr = crawl_links(f, origin, args.max_pages)
    smset = {norm_url(map_host(u, site, local, origin)) for u in sitemap_urls} if sitemap_urls else set()
    outside = [d for d in dead_links if norm_url(d[0]) not in smset]
    dead_ev = bad_link_evidence(outside)
    partial = []
    if crawl_thr:
        partial.append(f"throttled ({crawl_thr} crawled pages throttled, their outlinks unparsed; "
                       f"rerun with fewer --workers or a larger --sleep)")
    if capped:
        partial.append(f"crawl-capped (crawled {crawled} pages, hit the {args.max_pages} cap)")
    if outside:
        # Found dead links are conclusive; incomplete coverage doesn't weaken that —
        # there may just be more not yet crawled
        R.set("C6", FAIL, dead_ev + partial)
    elif partial:
        R.set("C6", NA, partial + ["coverage incomplete, not enough to declare internal outlinks clean"])
    else:
        n = len(dead_links) - len(outside)
        R.set("C6", PASS, f"crawled {crawled} pages, internal outlinks outside the sitemap free of 4xx/5xx"
                          + (f" (plus {n} bad links whose targets are in the sitemap — C2's business)" if n else ""))

    # ---------- C7 llms.txt ----------
    rr = f.get(origin + "/llms.txt")
    if rr["status"] != 200:
        R.set("C7", FAIL, f"/llms.txt → {rr['status'] or rr['err']}")
    elif rr["text"].strip().startswith("<") or len(rr["text"].strip()) < 50:
        R.set("C7", FAIL, "exists but not valid markdown, or near-empty")
    else:
        R.set("C7", PASS, f"{len(rr['text'])} chars; key-page coverage and summaries → human review (against T2)")

    # ---------- C26 no auto language redirects (site-level, sampled) ----------
    probes = [{"Accept-Language": lang} for lang in CFG.LANG_REDIRECT_PROBES]
    targets = [p["url"] for p in ok_pages[:CFG.LANG_REDIRECT_SAMPLE_SIZE]]
    if not targets:
        R.set("C26", NA, "no-pages (no testable pages)")
    else:
        div = []
        for u in targets:
            rs = [f.get(u, headers=h) for h in probes]
            if len({norm_url(r["final_url"]) for r in rs}) > 1:
                # no language header = the crawler's viewpoint (already fetched during page
                # sampling, so this hits the cache — zero extra requests)
                bot = f.get(u)
                langs = [l.split(",")[0] for l in CFG.LANG_REDIRECT_PROBES]
                div.append(
                    f"**{u}** final URL varies with Accept-Language (one URL, two behaviors — not 'two languages, two URLs'): "
                    + " / ".join(f"{l}→{r['final_url']} (hop {r['hops']})" for l, r in zip(langs, rs))
                    + f"; crawlers send no Accept-Language → they get {bot['final_url']} (hop {bot['hops']})"
                      f", the other version has no crawler-reachable URL")
        R.set("C26", FAIL if div else PASS,
              div[:3] or
              f"sampled {len(targets)} page(s), same final URL under every Accept-Language"
              f" (language differences live entirely in URLs — compliant)")

    # ---------- page-level: C8-C20 ----------
    declared_hosts = [urlparse(canonical_href(p["html"]) or "").netloc
                      for p in ok_pages if canonical_href(p["html"])]
    # sorted() is not optional: on a tie, max(set(...)) picks a winner by set iteration
    # order → string hashing → randomized per Python process, so the same input could
    # give a different majority_host on two runs. Nothing to do with concurrency —
    # single-threaded drifts too.
    majority_host = max(sorted(set(declared_hosts)), key=declared_hosts.count) if declared_hosts else None

    # C8 canonical (both channels: HTML + HTTP header)
    st = []
    for p in ok_pages:
        href = canonical_href(p["html"])
        hdr = header_canonical(p["fetch"]["headers"])
        fu = norm_url(p["fetch"]["final_url"])
        probs = []
        if href and hdr and norm_url(urljoin(fu, href)) != norm_url(urljoin(fu, hdr)):
            probs.append(f"channels conflict: HTML={href} / header={hdr}")
        src = href or hdr
        if not src:
            st.append((p["url"], FAIL, "no canonical (neither the HTML nor the HTTP header channel)")); continue
        cu = norm_url(urljoin(fu, src))
        if local:
            okc = (majority_host and urlparse(cu).netloc == majority_host
                   and urlparse(cu).path == urlparse(fu).path)
            if not okc:
                probs.append(f"canonical={cu} (self-consistency check, declared host={majority_host})")
        elif cu != fu:
            probs.append(f"canonical={cu} ≠ {fu}")
        st.append((p["url"], FAIL if probs else PASS, probs))
    agg_pages(R, "C8", st)

    # C9 server-side rendering (v1 heuristic)
    st = [(p["url"],
           PASS if len(p["text"]) >= CFG.SSR_MIN_TEXT_CHARS else FAIL,
           f"{len(p['text'])} chars" + ("" if len(p["text"]) >= CFG.SSR_MIN_TEXT_CHARS
                                       else f" < {CFG.SSR_MIN_TEXT_CHARS}, likely CSR shell / thin content"))
          for p in ok_pages]
    agg_pages(R, "C9", st)
    if R.rows.get("C9") and R.rows["C9"][0] == PASS:
        R.set("C9", PASS, R.rows["C9"][1] + ["heuristic; the 90% ratio verdict awaits headless"])

    # C10 cached public version (double-fetch diff, sampled)
    st = []
    dbl = ok_pages[:CFG.CACHE_DIFF_SAMPLE_SIZE]
    for p, r2 in zip(dbl, f.map(lambda q: f.get(q["url"], force=True), dbl)):
        if r2["status"] != 200:
            st.append((p["url"], NA, f"second fetch {r2['status']}")); continue
        same = r2["text"] == p["html"]
        st.append((p["url"], PASS if same else FAIL,
                   "" if same else f"two fetches diff non-empty (len {len(p['html'])} vs {len(r2['text'])})"))
    agg_pages(R, "C10", st)

    # C23 indexed pages carry no noindex (self-evidencing: being in the sitemap = declared
    # for indexing, so also carrying noindex is a self-contradiction)
    st = []
    for p in ok_pages:
        mm = metas(p["html"])
        hits = []
        for name in CFG.NOINDEX_META_NAMES:
            val = mm.get(name, "").lower()
            hits += [f'meta[{name}]="{val}"' for tok in CFG.NOINDEX_TOKENS
                     if re.search(rf"\b{tok}\b", val)][:1]
        xr = (p["fetch"]["headers"].get("X-Robots-Tag")
              or p["fetch"]["headers"].get("x-robots-tag") or "").lower()
        hits += [f'X-Robots-Tag="{xr}"' for tok in CFG.NOINDEX_TOKENS
                 if re.search(rf"\b{tok}\b", xr)][:1]
        st.append((p["url"], FAIL if hits else PASS, hits))
    agg_pages(R, "C23", st)

    # C11 title/description
    st, titles, descs = [], {}, {}
    for p in ok_pages:
        m = re.search(r"<title[^>]*>(.*?)</title>", p["html"], flags=re.S | re.I)
        t = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        d = metas(p["html"]).get("description", "")
        probs = []
        if not t: probs.append("no title")
        elif len(t) > CFG.TITLE_MAX_CHARS: probs.append(f"title {len(t)} chars > {CFG.TITLE_MAX_CHARS}")
        if not d: probs.append("no description")
        elif len(d) > CFG.DESC_MAX_CHARS: probs.append(f"desc {len(d)} chars > {CFG.DESC_MAX_CHARS}")
        if t: titles.setdefault(t, []).append(p["url"])
        if d: descs.setdefault(d, []).append(p["url"])
        st.append((p["url"], FAIL if probs else PASS, probs))
    def dup_ev(kind, groups):
        """Duplicate evidence. The old version only wrote "title duplicated x3" — without
        saying which text is duplicated a reader has nothing to act on, and it packed a
        whole group into one item, so a 149-page site produced 3000+ characters and blew
        up the report table.
        Now: give the duplicated text itself + one example URL, truncated by the report-wide
        [:N] + "…N total" convention."""
        items = sorted(((txt, urls) for txt, urls in groups.items() if len(urls) > 1),
                       key=lambda x: -len(x[1]))
        out = [f'{kind} duplicated ×{len(urls)} "{txt[:40]}{"…" if len(txt) > 40 else ""}" e.g. {urls[0]}'
               for txt, urls in items[:3]]
        return out + ([f"…{len(items)} duplicated {kind} groups total"] if len(items) > 3 else [])

    dup = dup_ev("title", titles) + dup_ev("desc", descs)
    agg_pages(R, "C11", st)
    if dup:
        prev = R.rows["C11"]
        R.set("C11", FAIL, prev[1] + dup)

    # C12 JSON-LD basics (types + base-group required fields) + negative scan
    def typed_nodes(blocks):
        nodes = []
        def walk(n):
            if isinstance(n, dict):
                if n.get("@type"): nodes.append(n)
                for v in n.values(): walk(v)
            elif isinstance(n, list):
                for v in n: walk(v)
        for parsed, _ in blocks:
            if parsed is not None: walk(parsed)
        return nodes

    def base_group_probs(nodes):
        """Base-group required fields: any one Organization node with name/url/logo/sameAs
        complete, and any one WebSite node with name/url complete, satisfies it
        (accommodates the @id split-block reference style)."""
        orgs = [n for n in nodes if str(n.get("@type")) in CFG.ORG_TYPES
                or (isinstance(n.get("@type"), list) and set(n["@type"]) & CFG.ORG_TYPES)]
        wss = [n for n in nodes if n.get("@type") == "WebSite"]
        probs = []
        if orgs:
            best = min((tuple(f for f in ("name", "url", "logo", "sameAs") if not n.get(f))
                        for n in orgs), key=len)
            if best: probs.append("Organization missing fields: " + ",".join(best))
        if wss:
            best = min((tuple(f for f in ("name", "url") if not n.get(f))
                        for n in wss), key=len)
            if best: probs.append("WebSite missing fields: " + ",".join(best))
        return probs

    st, rejected_hit = [], {}          # rejected type → pages hit (negative scan, red on sight)
    for p in ok_pages:
        blocks = ld_blocks(p["html"])
        if not blocks:
            st.append((p["url"], FAIL, "no ld+json")); continue
        parse_err = any(b[0] is None for b in blocks)
        types = [t for b in blocks if b[0] for t in ld_types(b[0])]
        has_org = any(t in CFG.ORG_TYPES for t in types)
        has_ws = "WebSite" in types
        for t in set(types) & set(CFG.LD_REJECTED_TYPES):
            rejected_hit.setdefault(t, []).append(p["url"])
        probs = []
        if parse_err: probs.append("unparseable block")
        if not has_org: probs.append("missing Organization (subtypes count)")
        if not has_ws: probs.append("missing WebSite")
        if not probs:
            nodes = typed_nodes(blocks)
            probs += base_group_probs(nodes)
            for n in nodes:                       # checked on sight: a declared type must have its fields complete
                ts = n["@type"] if isinstance(n["@type"], list) else [n["@type"]]
                for t in ts:
                    req = CFG.TYPE_REQUIRED.get(t)
                    if req:
                        missing = [fld for fld in req if not n.get(fld)]
                        if missing:
                            probs.append(f"{t} missing fields: {','.join(missing)}")
        st.append((p["url"], FAIL if probs else PASS, sorted(set(probs))))
    agg_pages(R, "C12", st)
    if rejected_hit:
        prev = R.rows["C12"]
        ev = [f"rejected type {t} ({CFG.LD_REJECTED_TYPES[t]}) on {len(us)} pages: {us[0]}"
              for t, us in sorted(rejected_hit.items())]
        R.set("C12", FAIL, prev[1] + ev)

    # C13 empty-shell 200
    st = [(p["url"],
           FAIL if len(p["text"]) < CFG.MIN_CONTENT_CHARS else PASS,
           f"{len(p['text'])} chars" + ("" if len(p["text"]) >= CFG.MIN_CONTENT_CHARS else " < threshold"))
          for p in ok_pages]
    agg_pages(R, "C13", st)
    prev = R.rows["C13"]
    R.set("C13", prev[0], prev[1] + ["retired sampling not wired (need-topic-queue)"])

    # C14 body-hide scripts
    st = []
    for p in ok_pages:
        hits = [pat for pat in CFG.BODY_HIDE_PATTERNS if re.search(pat, p["html"], flags=re.I)]
        st.append((p["url"], FAIL if hits else PASS, hits))
    agg_pages(R, "C14", st)

    # C15 render cost × declaration
    rendering = site.get("rendering")
    if not rendering:
        R.set("C15", NA, "need-declaration (no rendering strategy declared in sites.yaml)")
    elif rendering in ("ssg", "isr"):
        R.set("C15", PASS, f"declared {rendering}, exempt from the cache-header requirement")
    else:
        st = []
        for p in ok_pages:
            cc = p["fetch"]["headers"].get("Cache-Control", "")
            ok = "s-maxage" in cc
            st.append((p["url"], PASS if ok else FAIL,
                       f"Cache-Control: {cc or '(none)'}"))
        agg_pages(R, "C15", st)

    # C16 snippet meta
    st = []
    for p in ok_pages:
        robots = metas(p["html"]).get("robots", "")
        ok = "max-snippet:-1" in robots.replace(" ", "") and "max-image-preview:large" in robots.replace(" ", "")
        st.append((p["url"], PASS if ok else FAIL, f"robots meta: {robots or '(none)'}"))
    agg_pages(R, "C16", st)

    # C24 viewport meta
    st = []
    for p in ok_pages:
        vp = metas(p["html"]).get("viewport", "")
        ok = CFG.VIEWPORT_REQUIRED_TOKEN in vp.replace(" ", "")
        st.append((p["url"], PASS if ok else FAIL,
                   "" if ok else f"viewport: {vp or '(none)'}"))
    agg_pages(R, "C24", st)

    # C17 heading hierarchy
    st = []
    for p in ok_pages:
        hs = headings(p["html"])
        h1n = hs.count(1)
        probs = []
        if h1n != 1: probs.append(f"h1×{h1n}")
        prev_l = None
        for l in hs:
            if prev_l is not None and l > prev_l + 1:
                probs.append(f"skips h{prev_l}→h{l}"); break
            prev_l = l
        st.append((p["url"], FAIL if probs else PASS, probs))
    agg_pages(R, "C17", st)

    # C18 img attributes complete (width/height + alt)
    st = []
    for p in ok_pages:
        imgs = re.findall(r"<img\s[^>]*>", p["html"], flags=re.I)
        no_size = [i for i in imgs
                   if not (re.search(r"\bwidth\s*=", i, flags=re.I) and re.search(r"\bheight\s*=", i, flags=re.I))]
        # Judge "is the attribute present", not "is the value empty": alt="" is the correct
        # form for decorative images; a missing attribute is what leaves machines guessing
        no_alt = [i for i in imgs if not re.search(r"\balt\s*=", i, flags=re.I)]
        probs = []
        if no_size: probs.append(f"{len(no_size)}/{len(imgs)} imgs missing dimensions")
        if no_alt: probs.append(f"{len(no_alt)}/{len(imgs)} imgs missing the alt attribute")
        st.append((p["url"], FAIL if probs else PASS,
                   probs or f"{len(imgs)} imgs have dimensions+alt"))
    agg_pages(R, "C18", st)

    # C19 full OG set
    need = ["og:title", "og:description", "og:type", "og:url", "og:image"]
    st = []
    for p in ok_pages:
        mm = metas(p["html"])
        missing = [k for k in need if k not in mm]
        if "twitter:card" not in mm: missing.append("twitter:card")
        probs = ["missing " + ",".join(missing)] if missing else []
        w, h = mm.get("og:image:width"), mm.get("og:image:height")
        if w and h and (w, h) != (str(CFG.OG_IMAGE_WIDTH), str(CFG.OG_IMAGE_HEIGHT)):
            probs.append(f"og:image declares {w}×{h} ≠ {CFG.OG_IMAGE_WIDTH}×{CFG.OG_IMAGE_HEIGHT}")
        img = mm.get("og:image", "")
        if img and not img.lower().startswith(("http://", "https://")):
            probs.append(f"og:image not an absolute URL: {img}")
        # og:type value: valid vocabulary + self-evidencing trigger (the page's JSON-LD
        # calls itself an article → must be article, not website)
        ogt = mm.get("og:type", "").lower()
        if ogt and ogt not in CFG.OG_VALID_TYPES:
            probs.append(f"og:type invalid value: {ogt}")
        page_ld = {t for b in ld_blocks(p["html"]) if b[0] for t in ld_types(b[0])}
        if ogt and (page_ld & CFG.ARTICLE_LD_TYPES) and ogt != "article":
            probs.append(f"og:type={ogt}, but the page's JSON-LD calls itself "
                         f"{','.join(sorted(page_ld & CFG.ARTICLE_LD_TYPES))} → should be article")
        st.append((p["url"], FAIL if probs else PASS, probs))
    agg_pages(R, "C19", st)

    # C20 redirect chains (only pages fetched successfully)
    st = []
    for p in pages:
        if p["fetch"]["status"] is None or throttled(p["fetch"]):
            continue
        hops = p["fetch"]["hops"]
        st.append((p["url"], PASS if hops <= CFG.MAX_REDIRECT_HOPS else FAIL,
                   f"{hops} hop"))
    agg_pages(R, "C20", st)

    # C25 mixed content (subresources only; <a> is a navigation outlink, never blocked, not judged)
    sub_re = re.compile(r"<(?:%s)\s[^>]*\bsrc\s*=\s*[\"']http://([^\"']+)"
                        % "|".join(CFG.SUBRESOURCE_TAGS), flags=re.I)
    link_re = re.compile(r"<link\s[^>]*\bhref\s*=\s*[\"']http://([^\"']+)", flags=re.I)
    st = []
    for p in ok_pages:
        if not p["fetch"]["final_url"].lower().startswith("https://"):
            st.append((p["url"], NA, "http page, no mixed content to speak of")); continue
        hits = sub_re.findall(p["html"]) + link_re.findall(p["html"])
        st.append((p["url"], FAIL if hits else PASS,
                   [f"{len(hits)} http:// subresources"] + ["http://" + h for h in hits[:3]]
                   if hits else ""))
    agg_pages(R, "C25", st)

    # C21/C22 human review
    R.set("C21", HUMAN, "before launch, walk C21's YMYL trust-block checklist (see references/checklist/references/C21.md) (trigger: ymyl=true)")
    R.set("C22", HUMAN, "manually verify each language pair points both ways + x-default (trigger: site has a multi-language config)")

    R.throttled_total = f.throttled
    return R, mode, len(ok_pages), len(pages)

# ───────────────────────── subroutines ─────────────────────────

def robots_blocks(txt, ua):
    """Simplified robots parsing: in the group effective for this UA, Disallow:/ with no Allow:/ → blocked."""
    groups, cur_uas, cur_rules = [], [], []
    for line in txt.splitlines():
        line = line.split("#")[0].strip()
        if not line: continue
        m = re.match(r"(?i)user-agent\s*:\s*(.+)", line)
        if m:
            if cur_rules:
                groups.append((cur_uas, cur_rules)); cur_uas, cur_rules = [], []
            cur_uas.append(m.group(1).strip().lower()); continue
        m = re.match(r"(?i)(allow|disallow)\s*:\s*(.*)", line)
        if m and cur_uas:
            cur_rules.append((m.group(1).lower(), m.group(2).strip()))
    if cur_uas:
        groups.append((cur_uas, cur_rules))
    ua_l = ua.lower()
    best = None
    for uas, rules in groups:
        for g in uas:
            if g != "*" and (g in ua_l or ua_l in g):
                best = rules
    if best is None:
        for uas, rules in groups:
            if "*" in uas:
                best = rules
    if not best:
        return False
    dis_root = any(k == "disallow" and v == "/" for k, v in best)
    allow_root = any(k == "allow" and v == "/" for k, v in best)
    return dis_root and not allow_root

def lastmod_problems(entries):
    """C2's three lastmod verdicts: coverage / freshness / truthfulness.

    The old implementation only did "is one present" + "is the newest one fresh enough" —
    measuring **the best single entry**, so: 1 of 271 entries carrying lastmod counted as
    "present"; 270 entries rotting since 2021 with 1 dated today counted as "fresh"; and a
    site stamping build time equals "today" site-wide forever, i.e. a permanent green.
    Three holes, one shape.
    """
    total = len(entries)
    dated = [(u, s) for u, s in entries if s]
    probs = []
    if not dated:
        return ["no entry carries lastmod"]
    if len(dated) < total:
        probs.append(f"lastmod covers {len(dated)}/{total} entries (should be all)")

    days = []
    for _, s in dated:
        try:
            days.append(datetime.fromisoformat(s[:10]).date())
        except Exception:
            pass
    if days:
        age = (NOW.date() - max(days)).days
        if age > CFG.SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS:
            probs.append(f"newest lastmod {max(days)} ({age} days ago) "
                         f"> {CFG.SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS} days, likely unmaintained")

    # date-only: the protocol allows it, but dropping time-of-day and timezone means
    # several edits in one day become indistinguishable
    dateonly = [s for _, s in dated if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)]
    if dateonly:
        probs.append(f"{len(dateonly)}/{len(dated)} entries are date-only (full W3C datetime with timezone recommended)")

    # Truthfulness: largest single-day cluster + is that day today → a build timestamp hits
    # every day, a real bulk edit self-heals the next day
    if days:
        top_day, top_n = collections.Counter(days).most_common(1)[0]
        ratio = top_n / len(days)
        if ratio >= CFG.SITEMAP_LASTMOD_CLUSTER_RATIO and top_day >= NOW.date():
            probs.append(f"suspected build timestamp: {top_n}/{len(days)} entries ({ratio:.0%}) lastmod = {top_day}"
                         f" (the run date); a real bulk edit turns green by itself tomorrow")
    return probs

def collect_sitemap(site, f, local, origin):
    """Returns (entries, err, shards). entries = [(loc, lastmod_str | None)] — **paired per
    entry**, not two independent regex lists: coverage (how many entries carry lastmod) is
    only computable after pairing.
    shards = [(sitemap_url, entry count)], for the per-shard size verdict (protocol hard cap: 50k)."""
    sm = site.get("sitemap") or origin + "/sitemap.xml"
    sm = map_host(sm, site, local, origin)
    r = f.get(sm)
    if r["status"] != 200:
        return [], f"sitemap {sm} → {r['status'] or r['err']}", []
    entries, shards = [], []
    def parse(xml, src, depth=0):
        if "<sitemapindex" in xml and depth == 0:
            for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml)[:10]:
                rr = f.get(map_host(loc, site, local, origin))
                if rr["status"] == 200:
                    parse(rr["text"], loc, 1)
            return
        n = 0
        for block in re.findall(r"<url>(.*?)</url>", xml, flags=re.S):
            loc = re.search(r"<loc>\s*(.*?)\s*</loc>", block, flags=re.S)
            lm = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block, flags=re.S)
            if loc:
                entries.append((loc.group(1).strip(), lm.group(1).strip() if lm else None))
                n += 1
        shards.append((src, n))
    parse(r["text"], sm)
    return entries, None, shards

def map_host(url, site, local, origin):
    """Local mode: map the declared (production) host onto the TARGET host."""
    if not local:
        return url
    prod = urlparse(site.get("production") or "")
    u = urlparse(url)
    if prod.netloc and u.netloc == prod.netloc:
        o = urlparse(origin)
        return u._replace(scheme=o.scheme, netloc=o.netloc).geturl()
    return url

def crux_check(site, f):
    host = urlparse(site["origin"]).netloc
    try:
        r = requests.post(
            f"https://chromeuxreport.googleapis.com/v1/records:queryRecord?key={CFG.CRUX_API_KEY}",
            json={"origin": f"https://{host}"}, timeout=CFG.REQUEST_TIMEOUT)
        if r.status_code == 404:
            return NA, "need-crux-data (CrUX has no data for this site)"
        d = r.json().get("record", {}).get("metrics", {})
        def p75(k): return d.get(k, {}).get("percentiles", {}).get("p75")
        lcp, inp, cls = p75("largest_contentful_paint"), p75("interaction_to_next_paint"), p75("cumulative_layout_shift")
        probs = []
        if lcp and float(lcp) > CFG.CWV_LCP_MS: probs.append(f"LCP {lcp}ms")
        if inp and float(inp) > CFG.CWV_INP_MS: probs.append(f"INP {inp}ms")
        if cls and float(cls) > CFG.CWV_CLS: probs.append(f"CLS {cls}")
        return (FAIL if probs else PASS,
                probs or f"LCP {lcp} / INP {inp} / CLS {cls}")
    except Exception as e:
        return NA, f"CrUX error: {str(e)[:80]}"

# ───────────────────────── report output ─────────────────────────

CHECKS = [
    ("1. Site-level (once per site)", [
        ("C1", "P0", "robots.txt allows all AI crawler UAs"),
        ("C2", "P0", "sitemap reachable, no 4xx/5xx entries, truthful lastmod, <=50k URLs per file"),
        ("C3", "P0", "URL canonicalization: www/apex, http/https, trailing slash all 301 to one canonical host"),
        ("C26", "P0", "no Accept-Language redirects: every language version has its own fixed URL, no auto-jump"),
        ("C4", "P1", "Core Web Vitals pass: LCP<2.5s / INP<200ms / CLS<0.1"),
        ("C5", "P1", "IndexNow key file reachable at the site root"),
        ("C6", "P1", "internal outlinks free of 4xx/5xx: links on pages don't point at broken pages"),
        ("C7", "P2", "llms.txt exists: a site directory for AI engines at the root"),
    ]),
    ("2. Per indexed page", [
        ("C8", "P0", "self-referencing canonical: every page names its own canonical URL, HTML and header agree"),
        ("C9", "P0", "full body served server-side: readable without executing JS (no CSR shell)"),
        ("C10", "P0", "cached HTML is a public non-personalized version: nothing user-specific in it"),
        ("C23", "P0", "indexed pages carry no noindex: neither meta robots nor X-Robots-Tag blocks"),
        ("C11", "P1", "title / description unique per page and within limits (<=60 / <=150)"),
        ("C12", "P1", "JSON-LD: blocks parse, required fields present, no rejected types"),
        ("C13", "P1", "no soft 404s: never a 200 serving an empty or error page (retire via 301/410)"),
        ("C14", "P1", "no anti-flicker script hiding the whole page (crawlers may get a blank)"),
        ("C16", "P1", "snippet controls: max-snippet:-1 + max-image-preview:large"),
        ("C24", "P1", "viewport meta includes width=device-width"),
        ("C17", "P2", "heading hierarchy: exactly one h1, h2->h3 with no skipped levels"),
        ("C18", "P2", "every img has explicit width/height + alt"),
        ("C19", "P2", "full Open Graph set + twitter:card: social preview cards complete and correct"),
        ("C20", "P2", "redirect hops <=1: no chained redirects"),
        ("C15", "P2", "render cost not per-request: SSR needs CDN caching (s-maxage + SWR), SSG exempt"),
        ("C25", "P2", "no mixed content: no http:// subresources on HTTPS pages"),
    ]),
    ("3. Conditional (human review; flag / site-config triggered)", [
        ("C21", "P0", "YMYL trust block: author, review attribution, authoritative citations"),
        ("C22", "P1", "hreflang reciprocal pairs + x-default"),
    ]),
]

ICON = {PASS: "✅ pass", FAIL: "🔴 fail", NA: "⚪ N.A.", HUMAN: "👤 human review"}

def verify_checklist_sync():
    """Drift guard: CHECKS (the report skeleton) must match the items in
    references/checklist/checklist.md.
    Check logic can't be auto-generated (each one is hand-written), but "which items
    exist, what priority, which section, what name" must line up; on mismatch it shouts,
    so the report never quietly lies.

    Returns the list of drift messages (empty = in sync) — printing is for humans, the
    return value is for CI."""
    md = CHECKLIST_MD
    if not md.exists():
        print("⚠️  checklist.md not found, skipping the sync check", flush=True); return []
    doc, sec = [], -1
    for line in md.read_text().splitlines():
        if line.startswith("## ") and re.match(r"## [123]\. ", line):
            sec += 1
        m = re.match(r"\|\s*(C\d+)\s*\|\s*(P\d)\s*\|\s*([^|]*?)\s*\|", line)
        if m and sec >= 0:
            doc.append((sec, m.group(1), m.group(2), m.group(3)))
    code = [(i, cid, prio, name) for i, (_, items) in enumerate(CHECKS) for cid, prio, name in items]
    if doc == code:
        return []
    msgs = []
    d, c = {x[1]: x for x in doc}, {x[1]: x for x in code}
    for cid in sorted(set(d) - set(c), key=lambda s: int(s[1:])):
        msgs.append(f"⚠️  drift: checklist has {cid} (priority {d[cid][2]}), not implemented in the script")
    for cid in sorted(set(c) - set(d), key=lambda s: int(s[1:])):
        msgs.append(f"⚠️  drift: script has {cid}, no longer an item in the checklist")
    for cid in sorted(set(d) & set(c), key=lambda s: int(s[1:])):
        if d[cid][2] != c[cid][2]:
            msgs.append(f"⚠️  drift: {cid} priority checklist={d[cid][2]} / script={c[cid][2]}")
        elif d[cid][0] != c[cid][0]:
            msgs.append(f"⚠️  drift: {cid} section checklist=section {d[cid][0]+1} / script=section {c[cid][0]+1}")
        elif d[cid][3] != c[cid][3]:
            # Names must line up too: the report prints the script's name, the checklist
            # prints its own copy — the two have been edited separately twice already,
            # each time reconciled by hand. It doesn't affect verdicts, but it makes the
            # same check go by different names in two documents, and readers think they
            # are two checks.
            msgs.append(f"⚠️  drift: {cid} names differ\n"
                        f"      checklist: {d[cid][3]}\n"
                        f"      script   : {c[cid][3]}")
    for m in msgs:
        print(m, flush=True)
    return msgs

def verify_config_example():
    """Drift guard two: references/config.example.yaml must match config.py's defaults.

    The template is a generated artifact. **A template stating stale defaults is worse
    than no template** — a config.yaml built from it would lock long-since-changed
    thresholds back to old values, and nothing anywhere would raise an alarm.
    """
    f = ROOT / "config.example.yaml"
    if not f.exists():
        msg = "⚠️  drift: references/config.example.yaml missing, run `python3 scripts/config.py --write-example`"
        print(msg, flush=True); return [msg]
    if f.read_text() == CFG.render_example():
        return []
    msg = ("⚠️  drift: references/config.example.yaml disagrees with config.py's defaults, "
           "run `python3 scripts/config.py --write-example` to regenerate")
    print(msg, flush=True); return [msg]

def verify_wrapper_sync():
    """Drift guard three: the plugin adapter (skills/seo-ops/SKILL.md) must carry the same
    frontmatter description as the canonical root SKILL.md.

    Plugin skill discovery (Claude Code and Codex alike) demands the skills/<name>/SKILL.md
    layout, so the adapter duplicates the routing metadata — the one piece that must never
    drift, because the description is what makes the skill trigger at all. The body is not
    compared: the adapter's body is deliberately just a pointer at the root file.
    """
    repo = Path(__file__).resolve().parents[1]
    root_md, wrap_md = repo / "SKILL.md", repo / "skills" / "seo-ops" / "SKILL.md"
    if not root_md.exists():
        return []                          # unusual layout; nothing to anchor the comparison to
    if not wrap_md.exists():
        msg = "⚠️  drift: skills/seo-ops/SKILL.md (plugin adapter) is missing"
        print(msg, flush=True); return [msg]
    def desc(f):
        return next((ln for ln in f.read_text().splitlines()
                     if ln.startswith("description:")), "")
    if desc(root_md) == desc(wrap_md):
        return []
    msg = ("⚠️  drift: skills/seo-ops/SKILL.md's description differs from SKILL.md's — "
           "copy the root frontmatter description into the adapter")
    print(msg, flush=True); return [msg]

def bad_link_evidence(bad):
    """C6's bad-outlink evidence: grouped by 4xx semantics. The verdict is unchanged (all
    red — crawlers follow the link into a wall and burn crawl budget), but **the name must
    be right**: 401/403 means "the page is alive, it just won't show anonymous visitors",
    which is a different thing from "the content is gone". Calling both "dead links" sends
    people hunting for a broken page that doesn't exist, and the two fixes are entirely
    different:
      • 404/410/5xx → content gone → clean up inbound links (a retirement transaction missed a step, see C13)
      • 401/403     → the page is alive, we just weren't shown it — **the cause is not
        unique, never conclude on its behalf**

    401/403 has at least five causes the checker cannot tell apart, so it states the facts
    + lists the branches for a human to judge:
      login/permission gate • WAF anti-bot challenge (blocking the checker, not crawlers) •
      geo blocking • misconfigured permissions • paywall
    Lesson measured 2026-08-25: the pilot site's /login and /user/Plan 403 bodies were
    "Just a moment..." = a Cloudflare challenge page, **not a login gate at all** — my
    first version labeled them "login-gated entrances", generalizing from one case. Wrong.
    """
    def fmt(rows):
        return [f"{u} → {st} (source {src})" for u, st, src in rows[:5]]
    restricted = [r for r in bad if r[1] in (401, 403)]
    broken = [r for r in bad if r[1] not in (401, 403)]
    parts = []
    if broken:
        parts.append(f"{len(broken)} dead internal links: {fmt(broken)}")
    if restricted:
        parts.append(f"{len(restricted)} access-restricted links (401/403, the page exists but returned no content; "
                     f"cause needs a human — login gate / WAF challenge / geo blocking / misconfigured permissions. "
                     f"The fix: don't emit the link when logged out, or rel=nofollow + robots.txt Disallow + keep it out of the sitemap; "
                     f"if WAF, check the rules allow verified crawlers): {fmt(restricted)}")
    return parts

def crawl_links(f, origin, max_pages):
    """BFS over internal links; returns (pages crawled, discovered in-site URL set (norm),
    hit-the-cap flag, dead links [(url, status, source page)]).

    Dead links and orphans come from this same crawl: orphans ask "does this edge exist in
    the graph", dead links ask "does this edge lead anywhere". Only internal links are
    covered — external outlinks would hit third-party sites every run, slow and easily
    false-flagged by 429/403; they belong to generation-side self-checks + human review (C6.md).

    Level-wise concurrency: pages within one level are independent (new discoveries only
    enter **the next level**), so a whole level can be fetched concurrently and merged
    back **in within-level input order** — identical discovered/parent/dead to page-by-page
    BFS, reproducible output.
    """
    o = urlparse(origin)
    start = norm_url(origin + "/")
    frontier, seen_fetch, discovered = [start], set(), {start}
    parent, dead, thr = {}, [], 0
    while frontier and len(seen_fetch) < max_pages:
        level = frontier[:max_pages - len(seen_fetch)]   # same truncation point as the sequential version
        frontier = frontier[len(level):]
        for u, r in zip(level, f.map(f.get, level)):
            seen_fetch.add(u)
            if throttled(r):
                thr += 1                 # throttled page: not a dead link, but its outlinks went unparsed → the orphan verdict is skewed too
                continue
            if r["status"] is None or r["status"] >= 400:
                dead.append((u, r["status"] or r["err"], parent.get(u, "(start)")))
                continue
            if r["status"] != 200 or "<html" not in r["text"][:2000].lower():
                continue
            for href in re.findall(r'<a\s[^>]*href=["\']([^"\'#]+)["\']', r["text"], flags=re.I):
                absu = urljoin(r["final_url"], href)
                p = urlparse(absu)
                if p.netloc != o.netloc or p.scheme not in ("http", "https"):
                    continue
                if re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|webp|zip|mp4|css|js)$", p.path, flags=re.I):
                    continue
                n = norm_url(absu.split("#")[0])
                if n not in discovered:
                    discovered.add(n)
                    parent[n] = u
                    frontier.append(n)
    return len(seen_fetch), discovered, bool(frontier), dead, thr

# ── the safe exit for markdown tables ───────────────────────────
# Tables are the most fragile structure in markdown: one bare | splits an extra column,
# one newline breaks a row in two, one long token with no spaces blows past the column
# width and stacks onto the next row. Evidence comes from the site under test (titles,
# script fragments, regexes) — all three can carry any of those.
# So **every piece of text that enters a cell goes through md_cell**, and long evidence
# never enters a cell at all (see render_report).

def disp_width(t):
    """Display width: CJK and full-width punctuation count as 2 — truncating by character
    count is meaningless in tables that carry CJK text.
    Zero-width spaces are break points we inserted ourselves, zero width; strip them
    before measuring."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
               for c in t.replace("\u200b", ""))


def md_cell(t, width=None, soft_break=True):
    """Turn arbitrary text into cell content that **cannot break the table**.

    Four steps, in a deliberate order:
      1. fold newlines into spaces — a bare newline splits one table row into two, the
         hardest corruption to trace
      2. escape `|` — otherwise an extra column splits and the whole row misaligns
      3. insert zero-width spaces into long tokens — renderers only wrap at spaces/CJK,
         so `/a/b?c=d&e=f` is one unbreakable word to them; inserting U+200B provides
         break points (invisible in copied text)
      4. hard-truncate by display width — truncation goes last, since the true width is
         only known after the first three steps
    """
    t = re.sub(r"[\r\n]+", " ", str(t)).strip()
    t = t.replace("|", "\\|")
    if soft_break:            # fixed vocabulary (e.g. check names) skips this — those wrap fine already, and inserting would only dirty copied text
        t = re.sub(r"([/=&_,;:?-])(?=[^\s])", "\\1\u200b", t)
    if width:
        out, w = [], 0
        for c in t:
            # U+200B is a break point we inserted ourselves, zero display width — same
            # yardstick as disp_width
            cw = 0 if c == "\u200b" else (2 if unicodedata.east_asian_width(c) in "WF" else 1)
            if w + cw > width:
                s = "".join(out)
                # Back the cut off to the nearest break point (a space / our own U+200B /
                # a CJK boundary): a summary chopped mid-token like
                # "need-key-declaration(config.INDEXNOW_…" leaves the reader staring at
                # half a word. If backing off loses more than half the width, give up
                # and keep the hard cut.
                for i in range(len(s) - 1, -1, -1):
                    wide = unicodedata.east_asian_width(s[i]) in "WF"
                    if s[i] in " \u200b" or wide:
                        cand = s[:i + 1] if wide else s[:i]
                        if disp_width(cand) >= width // 2:
                            s = cand
                        break
                return s.rstrip("\u200b ") + "…"
            out.append(c); w += cw
    return t


def assert_table_sane(lines):
    """Post-generation self-check: every table row must have **the same column count**, and
    no unbreakable token wide enough to blow the column.

    This exists on top of md_cell because md_cell relies on being remembered — one new
    column, one new concatenation can bypass it. The self-check makes "forgot to call it"
    explode at generation time instead of when someone reads a garbled report.
    """
    UNBREAKABLE_MAX = 40          # display-width cap for a single unbreakable token (CJK wraps on its own, doesn't count)
    run, start = [], 0
    def check(block, first):
        if len(block) < 2:
            return
        ncol = [len(re.split(r"(?<!\\)\|", ln)) for ln in block]
        if len(set(ncol)) != 1:
            bad = block[ncol.index(next(n for n in ncol if n != ncol[0]))]
            raise RuntimeError(f"report table column counts differ (from line {first}): {bad[:120]}")
        for ln in block:
            # Link targets take no page space (only the link text renders), so strip them
            # before measuring width — otherwise one GitHub URL turns this guard into
            # daily false-alarm noise.
            ln = re.sub(r"\]\([^)]*\)", "]", ln)
            for cell in re.split(r"(?<!\\)\|", ln):
                for tok in re.split(r"[\s\u200b]+", cell):
                    seg = re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", " ", tok)
                    longest = max((len(x) for x in seg.split()), default=0)
                    if longest > UNBREAKABLE_MAX:
                        raise RuntimeError(f"report table has a column-busting long token ({longest} wide): {tok[:80]}")
    for i, ln in enumerate(lines):
        if ln.startswith("|"):
            if not run: start = i + 1
            run.append(ln)
        else:
            check(run, start); run = []
    check(run, start)


def render_report(site, R, mode, ok_n, total_n, args):
    lines = [f"# checker report: {site['id']}",
             "",
             f"- Target: {site['origin']} ({mode})",
             f"- Time: {NOW.strftime('%Y-%m-%d %H:%M UTC')} • pages {ok_n}/{total_n}"
             f" ({'full' if args.page_sample == 0 else f'sample cap {args.page_sample}'})"
             f" • sitemap sample {args.sitemap_sample} • crawl cap {args.max_pages}"
             f" • {args.workers} worker(s) × {args.sleep}s interval",
             f"- Parameters: scripts/config.py; definitions: references/checklist/checklist.md", ""]
    if getattr(R, "throttled_total", 0):
        lines += [f"- 🚦 **throttled by the target {R.throttled_total} times (429/503), "
                  f"{getattr(R, 'thr_pages', 0)} of the page samples** — affected verdicts recorded"
                  f" as N.A., not fail (throttling means we fetched too fast, not that the site is"
                  f" broken). For a complete verdict: rerun with "
                  f"`--workers {max(1, args.workers // 2)}` or a larger `--sleep`.", ""]
    if getattr(R, "fetch_fails", None):
        lines.append("- ⚠️ sample fetches failed (not throttling): " + ";".join(R.fetch_fails[:6]) +
                     (f" …{len(R.fetch_fails)} total" if len(R.fetch_fails) > 6 else ""))
        lines.append("")
    counts = {"fail_p0": 0, "fail": 0, "pass": 0, "na": 0}
    details = []            # (cid, name, full evidence as lines) — the evidence zone outside the table
    for sec, items in CHECKS:
        lines += [f"## {sec}", "",
                  "| ID | Priority | Check | Result | Evidence | Docs |", "|---|---|---|---|---|---|"]
        for cid, prio, name in items:
            status, ev = R.rows.get(cid, (NA, "not implemented"))
            if status == FAIL:
                counts["fail"] += 1
                if prio == "P0": counts["fail_p0"] += 1
            elif status == PASS: counts["pass"] += 1
            elif status == NA: counts["na"] += 1
            # Strip the origin prefix: the report header already names the target site;
            # repeating it on every line is pure noise.
            # (The database still stores absolute URLs — the machine-read copy is untouched.)
            parts = [x.replace(site["origin"], "").strip() for x in ev]
            parts = [x for x in parts if x]
            # **The join happens only here**, and after joining it is never split back —
            # evidence stays list[str] the whole way; the appendix iterates it into lines,
            # the table summary joins the first few items. The old version joined
            # internally and guessed back with split(";") at render time, and semicolons
            # inside evidence text split lines mid-parenthesis.
            flat = "; ".join(parts)
            # The table holds only a summary; full evidence lands in the evidence zone at
            # the end. Not a shortcut — a structural necessity: a cell with variable-length
            # text leaves row height and wrapping to the renderer, beyond our control —
            # the old version capped at 300 chars and still failed (300 chars in a narrow
            # column is a dozen lines, one stretch and it stacks into the next row).
            # A code block has no column width and no table parsing: any length, any
            # characters, no corruption.
            summary = md_cell(flat, CFG.EVIDENCE_SUMMARY_WIDTH)
            if disp_width(md_cell(flat)) > CFG.EVIDENCE_SUMMARY_WIDTH:
                summary += f" [full \u2193](#{cid.lower()})"
                details.append((cid, name, parts))
            # Docs column: points at the item's canonical write-up — verdict criteria,
            # common mistakes, authority sources, and how to fix all live there.
            # The report carries the link, never the prose: a report must be byte-identical
            # across two runs, and any explanation written in here would have to track the
            # canonical text and eventually diverge; a link always points at the current
            # canonical version.
            doc = f"{CFG.DOC_BASE_URL}/{cid}.md"
            lines.append(f"| {cid} | {prio} | {md_cell(name, soft_break=False)} | {ICON[status]} | {summary} "
                         f"| [{cid} docs]({doc}) |")
        lines.append("")
    if details:
        lines += ["## Evidence (complete, untruncated)", "",
                  "The table holds summaries; this is the full set, one line per item. Full evidence also lands in checks.db.", ""]
        for cid, name, parts in details:
            # Anchor via a **heading**, not <a id="…">: GitHub's HTML sanitizer strips
            # user-written id attributes (keeping only the anchors it generates for
            # headings itself), so the link would go dead.
            # The heading text is just the cid — that keeps the slug predictable (CJK
            # heading slugs differ across renderers).
            # The heading carries only the ID (predictable anchor slug); the item name and
            # evidence each get an explicit label — unlabeled, "an ID + one bold line"
            # reads like "a number + an evidence summary", and readers mistake the check's
            # name for the conclusion.
            lines += [f"### {cid}", "", f"**Check**: {name}", "", "**Evidence** (complete, untruncated):", "", "```"]
            lines += parts or ["(none)"]
            lines += ["```", ""]
    lines.insert(5, f"**Verdict: 🔴 {counts['fail']} (P0: {counts['fail_p0']}) • "
                    f"✅ {counts['pass']} • ⚪ N.A. {counts['na']} • 👤 human review 2**")
    if details:
        # Text-level pointer, not just the anchor: some viewers can't make in-page
        # anchors jump — the words alone must tell the reader where the full
        # evidence lives.
        lines.insert(5, "- Evidence cells are one-line summaries; **full \u2193** jumps to"
                        " \"Evidence (complete, untruncated)\" at the end of this file"
                        " — if the link doesn't jump in your viewer, scroll there")
    assert_table_sane(lines)          # a forgotten md_cell call explodes here, not when someone reads the report
    return "\n".join(lines)

COLS = ("site", "url", "rule_id", "status", "evidence", "checked_at")

def save_db(db_path, site_id, R):
    """Persist the checks snapshot. 2026-08-25 dropped the page_type column (page types retired) —
    old databases migrate automatically: surviving fields are carried over by column name,
    historical snapshots survive, diffs keep working."""
    conn = sqlite3.connect(db_path)
    old = [r[1] for r in conn.execute("PRAGMA table_info(checks)")]
    if old and old != list(COLS):
        conn.execute("ALTER TABLE checks RENAME TO checks_old")
        conn.execute(f"CREATE TABLE checks({','.join(c + ' TEXT' for c in COLS)},"
                     f" PRIMARY KEY(site, url, rule_id))")
        keep = [c for c in COLS if c in old]          # carry by column name, not position
        conn.execute(f"INSERT INTO checks({','.join(keep)}) SELECT {','.join(keep)} FROM checks_old")
        conn.execute("DROP TABLE checks_old")
    else:
        conn.execute(f"CREATE TABLE IF NOT EXISTS checks({','.join(c + ' TEXT' for c in COLS)},"
                     f" PRIMARY KEY(site, url, rule_id))")
    ts, ph = NOW.isoformat(), ",".join("?" * len(COLS))
    # One item per line. Evidence is list[str] with single-line items, so newline is a
    # separator that **cannot collide with the data** — a semicolon would, evidence text
    # is full of semicolons. To restore the list: evidence.split("\n").
    for cid, (status, ev) in R.rows.items():
        conn.execute(f"REPLACE INTO checks VALUES({ph})",
                     (site_id, "@site", cid, status, "\n".join(ev), ts))
    for url, cid, status, ev in R.page_rows:
        conn.execute(f"REPLACE INTO checks VALUES({ph})",
                     (site_id, url, cid, status, "\n".join(ev), ts))
    conn.commit(); conn.close()

# ───────────────────────── main ─────────────────────────

def sites_file(override=None):
    """Find the site roster. <config_dir>/sites.yaml is canonical — it is **config**, it
    lives with .env; <state_dir>/ and in-package are compatibility fallbacks for old layouts.

    When nothing is found, do not silently run empty — exit and spell out where to create
    it and what to copy. "Missing config" is the user's problem, not something the script
    should guess at.
    """
    cd, sd = CFG.config_dir(), CFG.state_dir(override)
    for f in (cd / "sites.yaml", sd / "sites.yaml", ROOT / "sites.yaml"):
        if f.exists():
            if f != cd / "sites.yaml":
                print(f"⚠️  using {f} — the roster is config, move it to {cd / 'sites.yaml'}", flush=True)
            return f
    sys.exit(
        f"sites.yaml not found. Multi-site runs need a site roster first:\n"
        f"  mkdir -p {cd}\n"
        f"  cp {ROOT / 'sites.example.yaml'} {cd / 'sites.yaml'}\n"
        f"then edit it per its comments for your own sites. A single-site run doesn't need this file: --target https://example.com"
    )


def load_sites(args):
    if args.target or CFG.TARGET:
        t = (args.target or CFG.TARGET).rstrip("/")
        p = urlparse(t)
        if not p.scheme or not p.netloc or p.path not in ("", "/") or p.query or p.fragment:
            sys.exit(f"TARGET must be a root URL (origin), got: {t}")
        return [{"id": p.netloc.replace(":", "_"), "origin": t,
                 "production": t, "rendering": None, "samples": [{"url": "/"}],
                 "sitemap": None}]
    data = yaml.safe_load(sites_file(args.state_dir).read_text())["sites"]
    sites = []
    for s in data:
        if args.site and s["id"] != args.site: continue
        sites.append({"id": s["id"], "origin": s["production"].rstrip("/"),
                      "production": s["production"], "rendering": s.get("rendering"),
                      "samples": s.get("samples", []), "sitemap": s.get("sitemap")})
    if not sites:
        sys.exit("no matching site in sites.yaml")
    return sites

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site")
    ap.add_argument("--target")
    ap.add_argument("--page-sample", type=int, default=CFG.PAGE_SAMPLE_SIZE)
    ap.add_argument("--sitemap-sample", type=int, default=CFG.SITEMAP_URL_SAMPLE_SIZE)
    ap.add_argument("--max-pages", type=int, default=CFG.CRAWL_MAX_PAGES)
    ap.add_argument("--sleep", type=float, default=CFG.FETCH_SLEEP)
    ap.add_argument("--workers", type=int, default=CFG.FETCH_CONCURRENCY,
                    help="concurrent fetch threads; 1 = sequential (for output diffing)")
    ap.add_argument("--state-dir", default=None,
                    help="output directory; default ~/Documents/seo-ops, or set $SEO_OPS_DIR")
    ap.add_argument("--out", default=None, help="where the report and checks.db land; default <state-dir>/out")
    ap.add_argument("--verify-only", action="store_true",
                    help="run only the drift guards (checklist vs script), no network; exit 1 on drift. For CI")
    args = ap.parse_args()

    if args.verify_only:
        drift = verify_checklist_sync() + verify_config_example() + verify_wrapper_sync()
        print("✅ checklist and script in sync" if not drift else f"🔴 {len(drift)} drifts", flush=True)
        sys.exit(1 if drift else 0)

    # state_dir is only known after argparse, but .env was already read once at
    # import-config time — read it again.
    sd = CFG.state_dir(args.state_dir)
    CFG.load_env(sd); CFG.refresh_secrets()

    verify_checklist_sync()
    out_dir = Path(args.out) if args.out else sd / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    sites = load_sites(args)
    failed = []
    for site in sites:
        # Per-site isolation: site A crashing must not make site B wait for nothing.
        # Table stakes for a multi-site tool.
        print(f"== {site['id']} ({site['origin']}) ==", flush=True)
        try:
            f = Fetcher(args.sleep, args.workers)
            R, mode, ok_n, total_n = check_site(site, f, args)
            report = render_report(site, R, mode, ok_n, total_n, args)
            path = out_dir / f"report-{site['id']}-{NOW.strftime('%Y%m%d')}.md"
            path.write_text(report)
            save_db(out_dir / "checks.db", site["id"], R)
            print(report.split("\n**Verdict")[1].split("\n")[0].replace("**", "").lstrip(": "), flush=True)
            print(f"→ {path}", flush=True)
        except Exception:
            failed.append(site["id"])
            print(f"🔴 {site['id']} check aborted, no result for this site:", flush=True)
            traceback.print_exc()
            print("(remaining sites continue)", flush=True)

    # Exit code: **silent success is the one failure mode an acceptance tool cannot afford**.
    # The script crashing must be louder than the reds it reports — otherwise in cron,
    # "it died" looks like "all fine".
    # Note: piping through `| tee` and friends eats the exit code; callers need `set -o pipefail`.
    if failed:
        print(f"\n🔴 {len(failed)}/{len(sites)} site checks aborted: {', '.join(failed)}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
