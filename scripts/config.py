"""checker parameter config — the single home of every tunable (defaults = the phase-one baseline).

Principle: verdict logic lives in run.py, verdict parameters live here; changing a
threshold/list touches only this file, merged after human review.
**No secrets in this file** — API keys and the like live in `<config_dir>/.env`
(default ~/.config/seo-ops/), template in `references/.env.example`.
C4 (CWV) with no data: the checker emits no-data (N.A.), never red — the thresholds
themselves are official Google constants.
C numbers map to references/checklist/checklist.md (after the 2026-08-24 reordering).
"""
import json, os
from pathlib import Path

def _documents_dir():
    """The user's Documents directory.

    On macOS with iCloud's "Desktop & Documents" sync on, ~/Documents is redirected to
    ~/Library/Mobile Documents/... — `Path.home()/"Documents"` follows the symlink and
    gets the right place. Reports may therefore get synced into iCloud, which is exactly
    why secrets live separately in config_dir.

    **Windows unsupported**: there, Documents may be redirected by OneDrive with the
    true value in the registry, and the path assembled here may be an empty husk. With
    no Windows environment to verify on, we don't write an untested branch — to really
    run on Windows, pass --state-dir explicitly or set $SEO_OPS_DIR.
    """
    return Path.home() / "Documents"


def _config_base():
    """The base for the secrets directory: $XDG_CONFIG_HOME or ~/.config (macOS / Linux alike)."""
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def state_dir(override=None):
    """Where **outputs** live (reports and checks.db). --state-dir > $SEO_OPS_DIR > <Documents>/seo-ops

    **Not inside the package**: this checker gets copied into the skill directory, and a
    skill update = whole-package overwrite, so writable state in the package is guaranteed
    to be lost on update (checks.db especially — it is designed to accumulate across runs
    for diffing).

    **Not in cwd or some project either**: checks.db is the history of **sites**; it
    belongs to "which sites you are responsible for", not "which code repo you happen to
    be in". Accepting the same sites from three repos should not yield three severed
    histories.

    Landing in ~/Documents is deliberate: reports are outputs **for humans to read and to
    settle accounts with contractors**; they belong where users can find them, not hidden
    in a dotfile (same convention as last30days' MEMORY_DIR).

    **Config is not here** — `sites.yaml` and `.env` both belong to config_dir(). The
    boundary is config vs output, not sensitive vs not: the roster is no secret, but it
    is something you **feed** the tool, which is a different thing from what the tool
    **emits**; mix them in one directory and sooner or later nobody knows what's safe to
    delete.

    Side benefit: no dependency on any agent-private variable, so Claude Code / Codex /
    a bare command line all behave the same.
    """
    if override:
        # Guard against unsubstituted placeholders. The default no longer depends on any
        # agent-private variable, but an old SKILL.md carried
        # `--state-dir ${CLAUDE_PROJECT_DIR}/.seo-ops` — a Claude Code private extension,
        # not in the Agent Skills spec, so other agents copying it won't substitute.
        # Two failure shapes:
        #   passed through verbatim → override still contains "${"
        #   eaten by the shell      → becomes "/.seo-ops", whose parent is the root
        # The latter, running as root in a container, **really creates it at the
        # filesystem root** — silently landing in the wrong place. Better to stop.
        if "${" in str(override) or "$(" in str(override):
            raise SystemExit(
                f"--state-dir contains an unsubstituted variable: {override}\n"
                f"Only Claude Code substitutes `${{CLAUDE_PROJECT_DIR}}`. **Just omit --state-dir**\n"
                f"(default ~/Documents/seo-ops), or pass a real path / set $SEO_OPS_DIR.")
        p = Path(override).expanduser().resolve()
        if p.parent == Path(p.anchor):
            raise SystemExit(
                f"--state-dir points right under the filesystem root: {p}\n"
                f"Most likely some variable expanded to an empty string. **Just omit --state-dir**\n"
                f"(default ~/Documents/seo-ops), or pass a real path / set $SEO_OPS_DIR.")
        return p
    if os.environ.get("SEO_OPS_DIR"):
        return Path(os.environ["SEO_OPS_DIR"]).expanduser().resolve()
    return _documents_dir() / "seo-ops"


def config_dir():
    """Where **config** lives (sites.yaml and .env). $SEO_OPS_CONFIG_DIR > ${XDG_CONFIG_HOME:-~/.config}/seo-ops

    **Separate from state_dir on purpose**, two reasons stacked:

    1. Config is **input**, reports are **output** — mix them in one directory and sooner
       or later nobody knows what's safe to delete.
    2. Outputs go to ~/Documents so people can find them, but Documents is routinely
       synced by iCloud / OneDrive / Dropbox, backed up, and shared out folder-wide —
       API keys must not ride along. ~/.config enters none of those channels.

    (Same as last30days: outputs go to Documents, keys go to ~/.config/last30days/.env.)
    """
    if os.environ.get("SEO_OPS_CONFIG_DIR"):
        return Path(os.environ["SEO_OPS_CONFIG_DIR"]).expanduser().resolve()
    return _config_base().expanduser().resolve() / "seo-ops"

def load_env(d=None):
    """Read .env files in order, first read wins:

      1. <config_dir>/.env      — the canonical spot (default ~/.config/seo-ops/.env)
      2. <state_dir>/.env       — legacy layout, warns
      3. in-package scripts/.env — even older layout, warns

    `setdefault`, not assignment: **already-exported environment variables always beat
    every file** — a key injected in CI must not be overridden by somebody's local .env.
    """
    def parse(f):
        kv = {}
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
        return kv

    canonical = config_dir() / ".env"
    sources = [(canonical, None),
               ((d or state_dir()) / ".env", "legacy layout (secrets shouldn't live with outputs; Documents is often cloud-synced)"),
               (Path(__file__).with_name(".env"), "legacy in-package layout (overwritten on every skill update)")]
    for f, why in sources:
        if not f.exists():
            continue
        kv = parse(f)
        fresh = [k for k in kv if k not in os.environ]
        for k, v in kv.items():
            os.environ.setdefault(k, v)
        # Shout only when the file **actually supplied a value** — shouting when a prior
        # file already won would be noise that fires every run.
        # But when it did supply one, shouting is mandatory: silently misplaced config
        # makes the same command give different conclusions on two machines
        # (measured on C4: one gave real numbers, the other recorded need-crux-key).
        if why and fresh:
            print(f"⚠️  {', '.join(fresh)} came from {f} — {why}. Move it to {canonical}", flush=True)

load_env()

# ── run target (one parameter, mode auto-detected) ────
# TARGET: the site's **root URL (origin)** = scheme + host[:port], no path/query/fragment
#   (valid: "http://localhost:3000", "https://www.example.com";
#    invalid: "…/blog", "…?x=1" — validated at startup, errors out, never guesses).
#   Every entry point derives from the root: /robots.txt, sitemap, llms.txt, the crawl start.
#   Empty = run every site in sites.yaml (live).
#   - host is localhost / 127.x / bare IP / *.local → **local mode**:
#     C3/C4 record N.A. (reason=need-domain); C2/C6/C8's absolute-URL comparisons degrade
#     to self-consistency checks (the declared host is inferred as the majority value from
#     the output, swapped for the TARGET host, then fetched and verified).
#   - otherwise → **domain mode**: full verdicts; C4 with no CrUX data records N.A.
#     (reason=need-crux-data).
# Public staging domains are unsupported (they'd be judged as the production domain, C3
# falsely red) — for testing, pick one: launch, or deploy locally.
TARGET = ""    # e.g. "http://localhost:3000" or "https://www.example.com"

# ── fetching ──────────────────────────────────────────
# Real browser UA: Cloudflare blocks fake crawler UAs (2026-08-21, measured 403 on the pilot site)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
REQUEST_TIMEOUT = 20          # seconds
FETCH_SLEEP = 1.0             # interval between two requests of **a single worker** (seconds); overall QPS ≈ FETCH_CONCURRENCY / FETCH_SLEEP
# Default 1 = sequential. 271 pages take about 7 minutes — painless for a daily scheduled
# run, and it removes a whole class of risk (thread safety, shared backoff state, throttle
# false positives, the verification burden of a concurrency output-diff).
# Measured: a sequential run against the pilot site got **zero throttling**; every 429 came
# from concurrency.
# `Fetcher.map()` with workers<=1 is a plain list comprehension, no threads — concurrency
# is a reserved seam, not the default path.
# When to open it: sites in the thousands of pages, single runs past 20 minutes. At that
# point **the concurrency output-diff must be redone** (see README).
FETCH_CONCURRENCY = 1
PAGE_SAMPLE_SIZE = 0          # page-level check coverage: 0 = every page the sitemap registers (default); >0 = sample cap (debugging)

# ── throttle adaptation (concurrency's seat belt) ─────
# A throttled request **never counts as a failed check** — it means we fetched too fast,
# not that the site is broken.
# 429/503 always: back off and retry → still failing, record N.A. (reason=throttled),
# slow down globally + warn at the top of the report.
# Lesson (measured 2026-08-25): 8 workers × 1s against the pilot site = 192 of 271 pages
# ate 429s, and "dead internal links" inflated from 2 to a false 106 — false reds are far
# more dangerous than running slow.
THROTTLE_STATUSES = (429, 503)
THROTTLE_RETRIES = 3          # retries per request on throttle (exponential backoff; obeys Retry-After when present)
THROTTLE_BACKOFF = 2.0        # first backoff in seconds, doubles afterwards
THROTTLE_MAX_SLEEP = 4.0      # cap on the adaptive extra added to each request interval (seconds)
THROTTLE_RECOVER_AFTER = 20   # consecutive successes before stepping down a notch (AIMD: multiplicative backoff on impact, additive recovery when smooth)
                              # without this half, backoff only ever grows — one early 429 permanently drags the whole run 5x slower

# ── C2 sitemap ───────────────────────────────────────
SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS = 30   # newest site-wide lastmod older than this = sitemap unmaintained
SITEMAP_URL_SAMPLE_SIZE = 20               # entries sampled for reachability (no 4xx/5xx)
SITEMAP_MAX_URLS_PER_FILE = 50000          # protocol hard cap (sitemaps.org): one shard over the cap invalidates the whole file, must move to index shards
# lastmod truthfulness: a build timestamp is by definition always the latest build. The
# checker runs daily, so it only needs "largest single-day cluster ratio >= threshold AND
# that day == the run date" — a build stamp hits every day, a real bulk edit false-alarms
# only on its own day and turns green tomorrow as the date recedes into the past.
# False positives self-heal; false negatives never would (see references/C2.md).
SITEMAP_LASTMOD_CLUSTER_RATIO = 0.20

# ── C26 auto language redirects (site-level, sampled) ──
# The same URL landing differently under different Accept-Language = auto-redirect by
# guessed language.
# Googlebot sends no Accept-Language → it only ever sees the default-language version;
# the other version might as well not exist to crawlers.
LANG_REDIRECT_SAMPLE_SIZE = 5
LANG_REDIRECT_PROBES = ("en-US,en;q=0.9", "zh-CN,zh;q=0.9")

# ── C4 CWV (official Google "good" thresholds, constants) ──
CWV_LCP_MS = 2500
CWV_INP_MS = 200
CWV_CLS = 0.1
CRUX_API_KEY = os.environ.get("CRUX_API_KEY", "")   # lives in <config_dir>/.env; empty = C4 records N.A. (need-crux-key)

# ── C5 IndexNow ──────────────────────────────────────
# Lives in <config_dir>/.env: INDEXNOW_KEYS=site_id:key,site_id:key (the key is both the
# filename and the content of {key}.txt at the site root)
INDEXNOW_KEYS = dict(                               # unregistered = N.A. (need-key-declaration)
    pair.split(":", 1) for pair in
    (p.strip() for p in os.environ.get("INDEXNOW_KEYS", "").split(",")) if ":" in pair
)

def refresh_secrets():
    """`--state-dir` is only known after argparse (it affects load_env's second candidate
    location), while the two constants above were fixed at import time. run.py calls this
    once after parsing args to re-read and refresh."""
    global CRUX_API_KEY, INDEXNOW_KEYS
    CRUX_API_KEY = os.environ.get("CRUX_API_KEY", "")
    INDEXNOW_KEYS = dict(
        pair.split(":", 1) for pair in
        (p.strip() for p in os.environ.get("INDEXNOW_KEYS", "").split(",")) if ":" in pair
    )

# ── C6 internal outlinks (link-graph crawl) ───────────
CRAWL_MAX_PAGES = 5000        # crawl cap (a runaway guard); hitting it = incomplete coverage, recorded N.A.

# ── C9 server-side rendering (v1 heuristic; ratio verdict awaits headless) ──
SSR_TEXT_RATIO = 0.90         # target verdict: no-JS text / rendered text lower bound (enabled once headless lands)
SSR_MIN_TEXT_CHARS = 500      # v1 heuristic: no-JS body text below this = likely CSR shell

# ── C10 cached public version ─────────────────────────
CACHE_DIFF_SAMPLE_SIZE = 10   # pages sampled for the same-URL double-fetch diff

# ── report rendering ─────────────────────────────────
# Base URL for the links in the report's Docs column. A GitHub URL so the report stays
# clickable wherever it gets posted (relative paths only work for people with the skill
# installed). **A private repo still means 404 for outsiders** — to show contractors,
# the repo must go public.
# To make an acceptance document cite the docs as of the moment the report was generated,
# swap main for that run's commit SHA.
DOC_BASE_URL = "https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references"
# The table carries only evidence summaries; full evidence lives in the report's closing
# Evidence section (a code block, unconstrained by column width and outside table parsing).
# Summaries truncate by **display width** (CJK characters count as 2) — truncating by
# character count is useless: 300 characters in a narrow column is a dozen lines, and one
# row-height stretch stacks it into the next row — exactly how old reports got garbled.
# The cap targets "fits on one line": some viewers size row height off the other columns,
# and a wrapped evidence cell stacks into the next row, covering inline links.
# 22 + ellipsis + the " more" link is about 28 wide, leaving margin at common column
# widths (about 30).
EVIDENCE_SUMMARY_WIDTH = 22   # display-width cap for the table's evidence summary (target: one line); full evidence never truncated

# ── C11 title / description ──────────────────────────
TITLE_MAX_CHARS = 60
DESC_MAX_CHARS = 150

# ── C12 JSON-LD basics ───────────────────────────────
ORG_TYPES = {"Organization", "InsuranceAgency", "LocalBusiness", "Corporation",
             "OnlineBusiness", "MedicalOrganization"}   # subtypes treated as Organization

# Required fields per type, checked on sight (**purely self-evidencing**: the page
# declaring the type triggers the row, zero external input).
# The list mirrors references/C12.md section 2 (this system's adoption line, authority =
# Google's per-feature docs); editing that table means editing this one — the drift guard
# does not cover this pair, humans do.
# 2026-08-25: with page-type conditions retired, **"should exist but doesn't" has no
# judge on either side** (a product page with no Product markup at all is caught by
# neither checker nor human review) — trade-off explained at the top of references/C12.md.
TYPE_REQUIRED = {
    "Article":          ["headline", "image", "datePublished", "dateModified", "author"],
    "NewsArticle":      ["headline", "image", "datePublished", "dateModified", "author"],
    "BlogPosting":      ["headline", "image", "datePublished", "dateModified", "author"],
    "FAQPage":          ["mainEntity"],
    "ProfilePage":      ["mainEntity"],   # in Google's rich-results list (author/staff profile pages); adopted 2026-08-25
    "BreadcrumbList":   ["itemListElement"],
    "ItemList":         ["itemListElement"],
    "InsuranceProduct": ["name", "description"],
    "Product":          ["name", "description"],
    "Offer":            ["price", "priceCurrency"],
    "Person":           ["name"],
}

# Negative scan: red on sight. The list mirrors references/C12.md section 2.4
# ("negative constraints"); the single criterion is "**who consumes it, and what's the
# return**" — no answer means don't emit it: all maintenance cost, zero return.
# 2026-08-25: `AggregateRating` moved out of this list — its problem is not "no consumer"
# (Google does consume it, shows stars) but "is there real review data behind it", which
# is a content-truthfulness question for the R5 red line and human review, not for a
# structure check. Keeping it here would split the criterion in two, and the list could
# no longer say what it is blocking.
LD_REJECTED_TYPES = {
    "SiteNavigationElement": "no consumer; navigation is already expressed by <nav>",
    "SearchAction":       "Google retired the sitelinks searchbox 2024-10, the consumer is gone",
    # WebPage subtypes rejected wholesale: no matching Google rich result, no known return.
    # Exceptions (not listed here, genuinely worth declaring): FAQPage, ProfilePage
    "ItemPage": "WebPage subtype, no return", "CollectionPage": "WebPage subtype, no return",
    "AboutPage": "WebPage subtype, no return", "ContactPage": "WebPage subtype, no return",
    "CheckoutPage": "WebPage subtype, no return", "SearchResultsPage": "WebPage subtype, no return",
}

# ── C13 soft 404 / empty-shell 200 ───────────────────
MIN_CONTENT_CHARS = 400       # tag-stripped body text below this = likely an empty shell
RETIRED_SAMPLE_SIZE = 10      # retired entries sampled for status codes

# ── C14 body-hide third-party scripts (hand-maintained list, append new tools here) ──
BODY_HIDE_PATTERNS = [
    r"hide_element\s*=\s*'body'",        # VWO
    r"body\s*\{[^}]*opacity\s*:\s*0",    # generic anti-flicker
    r"async-hide",                       # Google Optimize-family anti-flicker
]

# ── C19 OG ───────────────────────────────────────────
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630
OG_VALID_TYPES = {"website", "article", "book", "profile", "product",
                  "video.other", "video.movie", "music.song"}   # valid og:type (common subset of the ogp.me vocabulary)
# Self-evidencing trigger: these JSON-LD types on a page = it calls itself an article →
# og:type must be article, not website
ARTICLE_LD_TYPES = {"Article", "NewsArticle", "BlogPosting", "TechArticle", "ScholarlyArticle"}

# ── C20 redirect chains ──────────────────────────────
MAX_REDIRECT_HOPS = 1         # max redirects allowed for any inbound URL

# ── C23 noindex (forbidden on indexed pages) ─────────
NOINDEX_TOKENS = ("noindex", "none")          # none ≡ noindex,nofollow
NOINDEX_META_NAMES = ("robots", "googlebot")  # googlebot is a separate entry, not covered by robots

# ── C24 viewport ─────────────────────────────────────
VIEWPORT_REQUIRED_TOKEN = "width=device-width"

# ── C25 mixed content (subresources only, navigation outlinks <a> don't count) ──
SUBRESOURCE_TAGS = ("img", "script", "iframe", "video", "audio", "source", "embed", "object")

# ── user-overridable parameters ───────────────────────
# name → one-line description. **Only entries registered here** can be overridden by
# <config_dir>/config.yaml.
#
# What's not on this whitelist is excluded on purpose, in three classes:
#   secrets     CRUX_API_KEY / INDEXNOW_KEYS — live in .env, never in plaintext config
#   constants   CWV_LCP_MS / CWV_INP_MS / CWV_CLS (official Google "good" thresholds),
#               SITEMAP_MAX_URLS_PER_FILE (the sitemaps.org protocol hard cap),
#               VIEWPORT_REQUIRED_TOKEN — tune them and it's no longer the same check
#   structured  TYPE_REQUIRED / LD_REJECTED_TYPES / BODY_HIDE_PATTERNS etc. —
#               changing them changes verdict logic, which belongs in a human-reviewed PR,
#               not hidden in somebody's local yaml
TUNABLE = {
    "UA":                                  "User-Agent for fetching (a real browser UA; Cloudflare blocks fake crawler UAs)",
    "REQUEST_TIMEOUT":                     "per-request timeout (seconds)",
    "FETCH_SLEEP":                         "interval between two requests of a single worker (seconds); overall QPS ≈ workers / interval",
    "FETCH_CONCURRENCY":                   "concurrent fetch threads; 1 = sequential. Redo the concurrency output-diff before enabling",
    "PAGE_SAMPLE_SIZE":                    "page-level check coverage: 0 = the full sitemap, >0 = sample cap",
    "THROTTLE_RETRIES":                    "retries per request on 429/503 (exponential backoff)",
    "THROTTLE_BACKOFF":                    "first backoff in seconds, doubles afterwards",
    "THROTTLE_MAX_SLEEP":                  "cap on the adaptive extra added to each request interval (seconds)",
    "THROTTLE_RECOVER_AFTER":              "consecutive successes before stepping down a notch (AIMD's additive recovery)",
    "SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS": "C2: newest site-wide lastmod older than this = sitemap unmaintained",
    "SITEMAP_URL_SAMPLE_SIZE":             "C2: entries sampled for reachability",
    "SITEMAP_LASTMOD_CLUSTER_RATIO":       "C2: single-day lastmod cluster over this ratio on the run date = suspected build timestamp",
    "LANG_REDIRECT_SAMPLE_SIZE":           "C26: pages sampled for auto language redirects",
    "CRAWL_MAX_PAGES":                     "C6: crawl cap (a runaway guard); hitting it = incomplete coverage, recorded N.A.",
    "SSR_TEXT_RATIO":                      "C9: no-JS text / rendered text lower bound (enabled once headless lands)",
    "SSR_MIN_TEXT_CHARS":                  "C9: no-JS body text below this = likely CSR shell",
    "CACHE_DIFF_SAMPLE_SIZE":              "C10: pages sampled for the same-URL double-fetch diff",
    "TITLE_MAX_CHARS":                     "C11: title length cap",
    "DESC_MAX_CHARS":                      "C11: description length cap",
    "MIN_CONTENT_CHARS":                   "C13: body text lower bound (thin content)",
    "RETIRED_SAMPLE_SIZE":                 "C20: retired URLs sampled",
    "OG_IMAGE_WIDTH":                      "C19: recommended og:image width",
    "OG_IMAGE_HEIGHT":                     "C19: recommended og:image height",
    "MAX_REDIRECT_HOPS":                   "C3: canonicalization hop cap (only a single hop preserves the weight)",
    "DOC_BASE_URL":                        "base URL for the report's Docs column; swap main for a commit SHA to pin a version",
    "EVIDENCE_SUMMARY_WIDTH":              "display-width cap for the table's evidence summary; full evidence in the report's closing evidence section, untruncated",
}


def render_example():
    """Render config.example.yaml's content from TUNABLE and the **current defaults**.

    The example file is generated, not hand-written — a hand-written example eventually
    disagrees with the code, and a template stating stale defaults is worse than no
    template. `run.py --verify-only` compares it against this output and exits 1 on
    mismatch (CI runs it). After changing a default, regenerate:
        python3 scripts/config.py --write-example
    """
    lines = [
        "# seo-ops tunables — copy to <config_dir>/config.yaml, then change what you need.",
        "#   default location: ${XDG_CONFIG_HOME:-~/.config}/seo-ops/config.yaml",
        "#   mkdir -p ~/.config/seo-ops && cp references/config.example.yaml ~/.config/seo-ops/config.yaml",
        "#",
        "# Every line below is the **current default**; left as-is it equals no config at all.",
        "# Change only the lines you need — keep or delete the rest, unset keys use the defaults.",
        "#",
        "# No secrets in this file: CRUX_API_KEY / INDEXNOW_KEYS live in .env in the same directory.",
        "# Unregistered keys are rejected (a typoed key name won't be silently ignored).",
        "",
    ]
    for name, why in TUNABLE.items():
        v = globals()[name]
        lines.append(f"# {why}")
        lines.append(f"{name}: {json.dumps(v, ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines)


def load_overrides(path=None):
    """Read <config_dir>/config.yaml to override defaults.

    **Unknown keys and type mismatches error out, never silently ignored** — this is an
    acceptance tool; "I definitely tuned that threshold" while the report used the default
    because of a typoed key name is far more dangerous than a plain error.
    """
    f = path or (config_dir() / "config.yaml")
    if not f.exists():
        return
    import yaml
    data = yaml.safe_load(f.read_text()) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{f}: top level should be a key: value mapping, got {type(data).__name__}")
    for k, v in data.items():
        if k not in TUNABLE:
            raise SystemExit(
                f"{f}: unknown config key {k!r}. Valid keys are in references/config.example.yaml; "
                f"secrets go in .env in the same directory.")
        want = type(globals()[k])
        # bool is a subclass of int; don't let true quietly become 1
        if isinstance(v, bool) != (want is bool) or not isinstance(v, (want, int) if want is float else want):
            raise SystemExit(f"{f}: {k} should be {want.__name__}, got {type(v).__name__} ({v!r})")
        globals()[k] = want(v) if want is float else v


load_overrides()


if __name__ == "__main__":
    import sys
    if "--write-example" in sys.argv:
        out = Path(__file__).resolve().parents[1] / "references" / "config.example.yaml"
        out.write_text(render_example())
        print(f"✅ regenerated {out}")
    else:
        sys.exit("usage: python3 scripts/config.py --write-example")
