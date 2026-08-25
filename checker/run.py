#!/usr/bin/env python3
"""checker — 手动运行的检查脚本。用法与判定说明见仓库根 CLAUDE.md。

条目定义住 checklist/checklist.md(**唯一真相**),本脚本实现其机器项
C1–C20、C23–C26;C21/C22 为人审项,报表列出不判。
两份靠 verify_checklist_sync() 每次启动对齐 —— 检查逻辑无法自动生成(每条手写),
但「有哪些条目、什么优先级、在哪一节」必须对得上,对不上就在 stdout 喊。

  python3 checker/run.py                       # config.TARGET 为空 → 按 sites.yaml 全部站点跑
  python3 checker/run.py --site tigerless-com  # 只跑 sites.yaml 里的一个站
  python3 checker/run.py --target http://localhost:3000   # 单站覆盖(本地模式自动判定)

不往包内写任何东西(这份 checker 会被复制进 skill,skill 更新 = 整包覆盖)。两处外部目录:
  <state-dir>  默认 ~/Documents/seo-ops   —— 花名册与产出,给人读的东西
    ├── sites.yaml                        — 站点花名册(多站才需要)
    └── out/report-<site>-<date>.md       — 与 checklist 同构的表单(三节;结果 + 证据)
        out/checks.db                     — checks 快照(SQLite,schema 见 CLAUDE.md)
  <config-dir> 默认 ~/.config/seo-ops     —— 机密,单独放
    └── .env                              — API key(已 export 的环境变量优先)
  Documents 常被云同步/备份/整夹分享,所以 key 不跟产出同住。

三条不变量:
  1. **三态判定** pass / fail / N.A.(reason) —— 「没测」和「没事」不许混成一个绿。
  2. **纯 deterministic,零 LLM** —— 抓取 → 正则/json 解析 → 阈值比较 → 拼 markdown。
     同站同配置两次跑必须逐字相同;这是它能当验收依据、能拿去跟施工方争议的前提。
  3. **爬虫视角** —— 不存 cookie、不发 Accept-Language。checker 要看的是 Googlebot 看到的东西,
     不是「浏览过一遍的用户」看到的东西(见 references/C26.md)。

只读线上 HTTP/HTML 产出,栈无关;真实浏览器 UA(Cloudflare 拦伪装爬虫 UA)。
默认单线程(config.FETCH_CONCURRENCY = 1);并发是留着的接缝,打开前须重做对拍。
"""
import argparse, collections, json, re, sqlite3, sys, threading, time, traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.cookiejar import DefaultCookiePolicy
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests, yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as CFG

def _resolve_paths():
    """定位三份数据文件,兼容两种布局 —— 这份脚本既可能住在本仓库根下,也可能被塞进
    别的仓库当子目录用。路径写死就会分叉成两个副本,分叉了就必然有一份先烂掉。
      本仓库    :  checker/run.py  +  checklist/checklist.md
      嵌在别处:  <any>/checker/run.py  +  <any>/checklist/checklist.md
    """
    here = Path(__file__).resolve()
    for root in (here.parents[2], here.parents[1]):
        for sub in ("docs/checklist/checklist.md", "checklist/checklist.md"):
            if (root / sub).exists():
                return root, root / sub
    return here.parents[2], here.parents[2] / "docs" / "checklist" / "checklist.md"

ROOT, CHECKLIST_MD = _resolve_paths()
NOW = datetime.now(timezone.utc)

# ───────────────────────── fetch 层 ─────────────────────────

class Fetcher:
    """并发抓取器。

    **默认顺序执行(config.FETCH_CONCURRENCY = 1)** —— `map()` 此时走普通列表推导,不建线程。
    并发只是留了个接缝,给日后上千页的站用;打开前必须重做并发对拍。

    接缝打开后,保证输出仍逐字可复现的三条(checker 是验收工具,两次跑必须给出同一份报告):
      1. `map()` 按输入原序返回 —— 并发只改抓取时机,不改结果顺序;
      2. 同一 URL 只放一个线程去抓,其余等它的结果(per-key 锁)—— 不会出现「同页两份不同快照」;
      3. Session 按线程独立(requests.Session 非线程安全)。
    节流语义:`sleep` 是**单个 worker** 两次请求间隔,整体 QPS ≈ workers / sleep。
    """
    def __init__(self, sleep, workers):
        self.local = threading.local()
        self.sleep = sleep
        self.workers = max(1, workers)
        self.cache = {}
        self.throttled = 0        # 被 429/503 挡下的请求数;>0 = 本次结果打折,报告顶部要说
        self._extra = 0.0         # 自适应额外间隔:挨限流乘性退避,连续成功加性恢复(AIMD)
        self._ok = 0              # 恢复计数器
        self._lock = threading.Lock()
        self._keylocks = {}

    def _session(self):
        s = getattr(self.local, "s", None)
        if s is None:
            s = requests.Session()
            s.headers["User-Agent"] = CFG.UA
            # 一律不存 cookie:爬虫每次都是**无状态首访**,不会带着上一页的状态。
            # 复用 cookie 会让 checker 表现得像个用户 —— 2026-08-25 实测 tigerless.com:
            # 无 cookie 首访 /home 两跳到 /cn(中文,Set-Cookie 记语言),带 cookie 则一跳到 /(英文);
            # Session 复用导致「第一个被抓的页是哪个」决定整份报告,结果随并发调度漂移。
            s.cookies.set_policy(DefaultCookiePolicy(allowed_domains=[]))
            # 显式不发 Accept-Language(requests 里 None = 不发这个头)。默认本来就不发,
            # 但那是「碰巧对」—— 钉死它,免得日后有人加一行默认 header 就悄悄换了视角:
            # Googlebot 按「无语言偏好」抓,带上这个头就变成用户视角(C26 正是量这个差异的)。
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
            with self._lock:                      # AIMD 的「加性恢复」那一半
                if self._extra:
                    self._ok += 1
                    if self._ok >= CFG.THROTTLE_RECOVER_AFTER:
                        self._ok = 0
                        self._extra = max(0.0, self._extra - CFG.THROTTLE_BACKOFF / 2)
        else:
            with self._lock:
                self.throttled += 1
                self._ok = 0
                self._extra = min(self._extra * 2 + 0.5, CFG.THROTTLE_MAX_SLEEP)   # 乘性退避
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
        """返回 dict(status, text, headers, final_url, hops, err);带缓存。
        force=True(C10 双抓)绕过缓存且不回写 —— 那一次要的就是「再抓一遍看变不变」。"""
        if force:
            return self._fetch(url, redirects, headers)
        key = (url, redirects, tuple(sorted((headers or {}).items())))
        with self._lock:
            if key in self.cache:
                return self.cache[key]
            kl = self._keylocks.setdefault(key, threading.Lock())
        with kl:
            with self._lock:
                if key in self.cache:            # 等锁期间别人已抓完
                    return self.cache[key]
            out = self._fetch(url, redirects, headers)
            with self._lock:
                self.cache[key] = out
            return out

    def map(self, fn, items):
        """并发跑 fn(item),**按 items 原序返回**;workers<=1 时退化为顺序执行(调试用)。"""
        items = list(items)
        if self.workers <= 1 or len(items) <= 1:
            return [fn(i) for i in items]
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            return list(ex.map(fn, items))

# ───────────────────────── HTML 解析helpers ─────────────────────────

def strip_text(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>",
               "", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def metas(html):
    """meta name/property → content(小写键;同名取第一个)。"""
    out = {}
    for m in re.finditer(r'<meta\s+[^>]*>', html, flags=re.I):
        tag = m.group(0)
        k = re.search(r'(?:name|property)\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
        v = re.search(r'content\s*=\s*["\']([^"\']*)["\']', tag, flags=re.I)
        if k and v:
            out.setdefault(k.group(1).strip().lower(), v.group(1).strip())
    return out

def ld_blocks(html):
    """[(parsed_or_None, raw)];parsed 为 json.loads 结果。"""
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
    """HTTP 通道的 canonical:`Link: <url>; rel="canonical"`。
    与 HTML 的 <link rel=canonical> 并存且不一致时,引擎自行择一 —— 控制权就丢了(C8)。"""
    v = headers.get("Link") or headers.get("link") or ""
    for part in v.split(","):
        if re.search(r'rel\s*=\s*"?canonical"?', part, flags=re.I):
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1).strip()
    return None

def norm_url(u):
    """比较用归一:去 fragment,path 去尾斜杠(根除外)。"""
    p = urlparse(u)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return f"{p.scheme}://{p.netloc}{path}" + (f"?{p.query}" if p.query else "")

def headings(html):
    return [int(m.group(1)) for m in re.finditer(r"<h([1-6])[\s>]", html, flags=re.I)]

def throttled(r):
    """429/503 = 我们打太快,不是页面坏了 —— 任何判定都不许把它算作 fail。"""
    return r["status"] in CFG.THROTTLE_STATUSES

def is_local(host):
    if host in ("localhost",) or host.endswith(".local"):
        return True
    return bool(re.match(r"^(\d{1,3}\.){3}\d{1,3}$|^127\.|^\[?::1\]?$", host))

# ───────────────────────── 结果收集 ─────────────────────────

PASS, FAIL, NA, HUMAN = "pass", "fail", "N.A.", "人审"

class Result:
    def __init__(self):
        self.rows = {}          # cid → (status, evidence)
        self.page_rows = []     # (url, cid, status, evidence)

    def set(self, cid, status, evidence=""):
        self.rows[cid] = (status, evidence)

    def page(self, url, cid, status, evidence=""):
        self.page_rows.append((url, cid, status, evidence))

def agg_pages(result, cid, pages_status):
    """按页结果聚合成条目结果:任一 fail → fail(证据列违规页 ≤5);空集 = N.A.,不算 pass。"""
    if not pages_status:
        result.set(cid, NA, "no-pages(页面样本为空或全部抓取失败)")
        return
    fails = [(u, ev) for u, st, ev in pages_status if st == FAIL]
    if fails:
        ev = ";".join(f"{u}({ev})" if ev else u for u, ev in fails[:5])
        more = f" …共 {len(fails)} 页" if len(fails) > 5 else ""
        result.set(cid, FAIL, ev + more)
    else:
        oks = [1 for _, st, _ in pages_status if st == PASS]
        result.set(cid, PASS, f"{len(oks)}/{len(pages_status)} 页通过")
    for u, st, ev in pages_status:
        result.page(u, cid, st, ev)

# ───────────────────────── 各项检查 ─────────────────────────

def check_site(site, f, args):
    """site: dict(id, origin, declared_host, rendering, samples[{url,ymyl,locale,pair}], sitemap)"""
    R = Result()
    origin = site["origin"].rstrip("/")
    host = urlparse(origin).netloc
    local = is_local(host.split(":")[0])
    mode = "本地模式" if local else "域名模式"

    # ---------- 前置:站点根可达吗 ----------
    # 连不上就别出报告。一个域名打错的站会一路降级成「几个红 + 一堆 N.A.」,
    # 看起来像一份体检结果,实际上什么都没测到 —— **半真的报告比没有报告更坏**。
    # 这里只认连接层失败(status is None:DNS/超时/拒连);500 之类是「站活着但坏了」,该照常测。
    root = f.get(origin + "/")
    if root["status"] is None:
        raise RuntimeError(f"站点根不可达({origin}/):{root['err']}")

    # ---------- 页面样本集:sites.yaml samples + sitemap 抽样 ----------
    sitemap_entries, sitemap_err, sitemap_shards = collect_sitemap(site, f, local, origin)
    sitemap_urls = [u for u, _ in sitemap_entries]
    limit = args.page_sample if args.page_sample > 0 else None   # 0 = 全量(sitemap 登记的全部页)
    sample_pages = [{**s, "url": origin + s["url"]} for s in site.get("samples", [])]
    seen = {norm_url(p["url"]) for p in sample_pages}
    for u in sitemap_urls:
        if limit is not None and len(sample_pages) >= limit: break
        u2 = map_host(u, site, local, origin)
        if norm_url(u2) not in seen:
            sample_pages.append({"url": u2})
            seen.add(norm_url(u2))
    def fetch_page(p):                       # 抓取量最大的一处:全量模式下 = sitemap 登记的所有页
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
        # 连接层失败 ≠ 404。抓不到就是没测到,不许当「无文件 = 默认全放行」报绿。
        R.set("C1", NA, f"unreachable(robots.txt 抓取失败:{r['err']})")
    elif r["status"] != 200:
        R.set("C1", PASS, f"robots.txt {r['status']}(无文件 = 默认全放行;但 要求 robots.txt 由模板生成,建议补)")
    else:
        blocked = [ua for ua in all_uas if robots_blocks(r["text"], ua)]
        if blocked:
            R.set("C1", FAIL, f"被拦 UA:{', '.join(blocked)}")
        else:
            R.set("C1", PASS, f"{len(all_uas)} 个 UA 全放行")

    # ---------- C2 sitemap ----------
    if sitemap_err:
        R.set("C2", FAIL, sitemap_err)
    elif not sitemap_urls:
        R.set("C2", FAIL, "sitemap 无条目")
    else:
        problems = []
        problems += lastmod_problems(sitemap_entries)
        over = [(s, n) for s, n in sitemap_shards if n > CFG.SITEMAP_MAX_URLS_PER_FILE]
        if over:
            problems.append("单份超协议上限(须走 index 分片):" +
                            ";".join(f"{s} {n} 条 > {CFG.SITEMAP_MAX_URLS_PER_FILE}" for s, n in over[:3]))
        def probe(u):
            # 不跟随重定向:sitemap 的语义是「这些 URL 就是规范地址」,**起点**必须 200。
            # 跟随了就等于只看终点 —— 一条 302 到别处的条目也会被算作可达(旧实现的洞)。
            rr = f.get(map_host(u, site, local, origin), redirects=False)
            if throttled(rr):
                return None                       # 限流不算条目坏
            if rr["status"] == 200:
                return None
            if rr["status"] and 300 <= rr["status"] < 400:
                return f"{u} → {rr['status']} 重定向到 {rr['headers'].get('Location', '?')}(条目应自身即 canonical)"
            return f"{u} → {rr['status'] or rr['err']}"
        bad = [x for x in f.map(probe, sitemap_urls[:args.sitemap_sample]) if x]
        if bad:
            problems.append("抽查异常:" + ";".join(bad[:5]))
        R.set("C2", FAIL if problems else PASS,
              ";".join(problems) if problems else
              f"{len(sitemap_urls)} 条;抽查 {min(len(sitemap_urls), args.sitemap_sample)} 条可达")

    # ---------- C3 归一 301 ----------
    if local:
        R.set("C3", NA, "need-domain(本地模式)")
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
            R.set("C3", FAIL, ";".join(errs[:3]))
        elif len(finals) == 1:
            R.set("C3", PASS, f"四变体归一 → {finals.pop()}")
        else:
            R.set("C3", FAIL, f"归宿不一:{sorted(finals)}")

    # ---------- C4 CWV ----------
    if local:
        R.set("C4", NA, "need-domain(本地模式)")
    elif not CFG.CRUX_API_KEY:
        R.set("C4", NA, "need-crux-key(config 未配 CrUX API key)")
    else:
        R.set("C4", *crux_check(site, f))

    # ---------- C5 IndexNow key ----------
    key = CFG.INDEXNOW_KEYS.get(site["id"])
    if not key:
        R.set("C5", NA, "need-key-declaration(config.INDEXNOW_KEYS 未登记)")
    else:
        rr = f.get(f"{origin}/{key}.txt")
        ok = rr["status"] == 200 and key in rr["text"]
        R.set("C5", PASS if ok else FAIL, f"/{key}.txt → {rr['status']}")

    # ---------- C6 内链图健康(无 orphan + 无站内死链)----------
    crawled, discovered, capped, dead_links, crawl_thr = crawl_links(f, origin, args.max_pages)
    dead_ev = bad_link_evidence(dead_links)
    if crawl_thr:
        # 限流页的出链没被解析 → 它的子页会被误判成 orphan。整条记 N.A.,不发假红。
        R.set("C6", NA, f"throttled(爬取中 {crawl_thr} 页被限流,orphan 判定失真;"
                        f"降 --workers 或调大 --sleep 重跑)"
                        + (";" + dead_ev if dead_ev else ""))
    elif not sitemap_urls:
        R.set("C6", FAIL if dead_links else NA,
              dead_ev or "sitemap 不可用,orphan 无从比对")
    else:
        smset = {norm_url(map_host(u, site, local, origin)) for u in sitemap_urls}
        orphan = smset - discovered
        if capped:
            # 触顶时 orphan 判定不成立(没爬完不能说"没链到"),但已抓到的死链是确凿的,照报
            R.set("C6", FAIL if dead_links else NA,
                  (dead_ev + ";" if dead_ev else "") +
                  f"crawl-capped(爬 {crawled} 页触上限 {args.max_pages};"
                  f"orphan 部分数据:未见于内链 {len(orphan)}/{len(smset)} 条,仅供参考)")
        elif orphan or dead_links:
            ev = []
            if orphan: ev.append(f"orphan {len(orphan)} 条:" + ";".join(sorted(orphan)[:5]))
            if dead_ev: ev.append(dead_ev)
            R.set("C6", FAIL, ";".join(ev))
        else:
            R.set("C6", PASS, f"sitemap {len(smset)} 条全部内链可达、站内链接无 4xx/5xx(爬 {crawled} 页)")

    # ---------- C7 llms.txt ----------
    rr = f.get(origin + "/llms.txt")
    if rr["status"] != 200:
        R.set("C7", FAIL, f"/llms.txt → {rr['status'] or rr['err']}")
    elif rr["text"].strip().startswith("<") or len(rr["text"].strip()) < 50:
        R.set("C7", FAIL, "存在但非合法 markdown 或近空")
    else:
        R.set("C7", PASS, f"{len(rr['text'])} 字符;重点页覆盖与摘要 → 人审(对照 T2)")

    # ---------- C26 无自动语言重定向(站级,抽样)----------
    probes = [{"Accept-Language": lang} for lang in CFG.LANG_REDIRECT_PROBES]
    targets = [p["url"] for p in ok_pages[:CFG.LANG_REDIRECT_SAMPLE_SIZE]]
    if not targets:
        R.set("C26", NA, "no-pages(无可测页面)")
    else:
        div = []
        for u in targets:
            rs = [f.get(u, headers=h) for h in probes]
            if len({norm_url(r["final_url"]) for r in rs}) > 1:
                # 无语言头 = 爬虫视角(这一次已在页面样本阶段抓过,走缓存,零额外请求)
                bot = f.get(u)
                langs = [l.split(",")[0] for l in CFG.LANG_REDIRECT_PROBES]
                div.append(
                    f"**{u}** 的落点随 Accept-Language 变(同一 URL 两种行为,非「两语言两 URL」):"
                    + " / ".join(f"{l}→{r['final_url']}(hop {r['hops']})" for l, r in zip(langs, rs))
                    + f";而爬虫不发 Accept-Language → 实得 {bot['final_url']}(hop {bot['hops']})"
                      f",另一版对爬虫无可达 URL")
        R.set("C26", FAIL if div else PASS,
              ";".join(div[:3]) if div else
              f"抽查 {len(targets)} 页,同一 URL 在各 Accept-Language 下落点一致(语言差异全在 URL 上,合规)")

    # ---------- 页级:C8–C20 ----------
    declared_hosts = [urlparse(canonical_href(p["html"]) or "").netloc
                      for p in ok_pages if canonical_href(p["html"])]
    # sorted() 不能省:平票时 max(set(...)) 的胜者取决于 set 迭代序 → 取决于字符串哈希 →
    # Python 每进程随机化,同一份输入两次跑可能给出不同 majority_host。与并发无关,单线程也会飘。
    majority_host = max(sorted(set(declared_hosts)), key=declared_hosts.count) if declared_hosts else None

    # C8 canonical(HTML + HTTP header 两路)
    st = []
    for p in ok_pages:
        href = canonical_href(p["html"])
        hdr = header_canonical(p["fetch"]["headers"])
        fu = norm_url(p["fetch"]["final_url"])
        probs = []
        if href and hdr and norm_url(urljoin(fu, href)) != norm_url(urljoin(fu, hdr)):
            probs.append(f"两路冲突:HTML={href} / header={hdr}")
        src = href or hdr
        if not src:
            st.append((p["url"], FAIL, "无 canonical(HTML 与 HTTP header 两路皆无)")); continue
        cu = norm_url(urljoin(fu, src))
        if local:
            okc = (majority_host and urlparse(cu).netloc == majority_host
                   and urlparse(cu).path == urlparse(fu).path)
            if not okc:
                probs.append(f"canonical={cu}(自洽检查,声明域={majority_host})")
        elif cu != fu:
            probs.append(f"canonical={cu} ≠ {fu}")
        st.append((p["url"], FAIL if probs else PASS, ";".join(probs)))
    agg_pages(R, "C8", st)

    # C9 服务端直出(v1 启发式)
    st = [(p["url"],
           PASS if len(p["text"]) >= CFG.SSR_MIN_TEXT_CHARS else FAIL,
           f"{len(p['text'])} 字符" + ("" if len(p["text"]) >= CFG.SSR_MIN_TEXT_CHARS
                                       else f" < {CFG.SSR_MIN_TEXT_CHARS},疑似 CSR 空壳/薄内容"))
          for p in ok_pages]
    agg_pages(R, "C9", st)
    if R.rows.get("C9") and R.rows["C9"][0] == PASS:
        R.set("C9", PASS, R.rows["C9"][1] + "(启发式;90% 比例判定待接 headless)")

    # C10 缓存公共版(双抓 diff,抽查)
    st = []
    dbl = ok_pages[:CFG.CACHE_DIFF_SAMPLE_SIZE]
    for p, r2 in zip(dbl, f.map(lambda q: f.get(q["url"], force=True), dbl)):
        if r2["status"] != 200:
            st.append((p["url"], NA, f"二抓 {r2['status']}")); continue
        same = r2["text"] == p["html"]
        st.append((p["url"], PASS if same else FAIL,
                   "" if same else f"两次抓取 diff 非空(len {len(p['html'])} vs {len(r2['text'])})"))
    agg_pages(R, "C10", st)

    # C23 收录页无 noindex(自证:进了 sitemap = 声明要收录,再挂 noindex 即自相矛盾)
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
        st.append((p["url"], FAIL if hits else PASS, ";".join(hits)))
    agg_pages(R, "C23", st)

    # C11 title/description
    st, titles, descs = [], {}, {}
    for p in ok_pages:
        m = re.search(r"<title[^>]*>(.*?)</title>", p["html"], flags=re.S | re.I)
        t = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        d = metas(p["html"]).get("description", "")
        probs = []
        if not t: probs.append("无 title")
        elif len(t) > CFG.TITLE_MAX_CHARS: probs.append(f"title {len(t)} 字符 > {CFG.TITLE_MAX_CHARS}")
        if not d: probs.append("无 description")
        elif len(d) > CFG.DESC_MAX_CHARS: probs.append(f"desc {len(d)} 字符 > {CFG.DESC_MAX_CHARS}")
        if t: titles.setdefault(t, []).append(p["url"])
        if d: descs.setdefault(d, []).append(p["url"])
        st.append((p["url"], FAIL if probs else PASS, ";".join(probs)))
    dup = [f"title 重复×{len(v)}" for v in titles.values() if len(v) > 1] + \
          [f"desc 重复×{len(v)}" for v in descs.values() if len(v) > 1]
    agg_pages(R, "C11", st)
    if dup:
        prev = R.rows["C11"]
        R.set("C11", FAIL, (prev[1] + ";" if prev[1] else "") + ";".join(dup))

    # C12 JSON-LD 基础项(类型 + 基础组必填参数)+ 负向扫描
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
        """基础组必填参数:任一 Organization 节点齐 name/url/logo/sameAs,
        任一 WebSite 节点齐 name/url,即算满足(兼容 @id 分块引用写法)。"""
        orgs = [n for n in nodes if str(n.get("@type")) in CFG.ORG_TYPES
                or (isinstance(n.get("@type"), list) and set(n["@type"]) & CFG.ORG_TYPES)]
        wss = [n for n in nodes if n.get("@type") == "WebSite"]
        probs = []
        if orgs:
            best = min((tuple(f for f in ("name", "url", "logo", "sameAs") if not n.get(f))
                        for n in orgs), key=len)
            if best: probs.append("Organization 缺参数:" + ",".join(best))
        if wss:
            best = min((tuple(f for f in ("name", "url") if not n.get(f))
                        for n in wss), key=len)
            if best: probs.append("WebSite 缺参数:" + ",".join(best))
        return probs

    st, rejected_hit = [], {}          # 不采纳类型 → 命中页(负向扫描,出现即红)
    for p in ok_pages:
        blocks = ld_blocks(p["html"])
        if not blocks:
            st.append((p["url"], FAIL, "无 ld+json")); continue
        parse_err = any(b[0] is None for b in blocks)
        types = [t for b in blocks if b[0] for t in ld_types(b[0])]
        has_org = any(t in CFG.ORG_TYPES for t in types)
        has_ws = "WebSite" in types
        for t in set(types) & set(CFG.LD_REJECTED_TYPES):
            rejected_hit.setdefault(t, []).append(p["url"])
        probs = []
        if parse_err: probs.append("解析失败块")
        if not has_org: probs.append("缺 Organization(含子类型)")
        if not has_ws: probs.append("缺 WebSite")
        if not probs:
            nodes = typed_nodes(blocks)
            probs += base_group_probs(nodes)
            for n in nodes:                       # 出现即查:声明了的类型字段必须齐
                ts = n["@type"] if isinstance(n["@type"], list) else [n["@type"]]
                for t in ts:
                    req = CFG.TYPE_REQUIRED.get(t)
                    if req:
                        missing = [fld for fld in req if not n.get(fld)]
                        if missing:
                            probs.append(f"{t} 缺参数:{','.join(missing)}")
        st.append((p["url"], FAIL if probs else PASS, ";".join(sorted(set(probs)))))
    agg_pages(R, "C12", st)
    if rejected_hit:
        prev = R.rows["C12"]
        ev = ";".join(f"不采纳类型 {t}({CFG.LD_REJECTED_TYPES[t]})出现于 {len(us)} 页:{us[0]}"
                      for t, us in sorted(rejected_hit.items()))
        R.set("C12", FAIL, (prev[1] + ";" if prev[1] else "") + ev)

    # C13 空壳 200
    st = [(p["url"],
           FAIL if len(p["text"]) < CFG.MIN_CONTENT_CHARS else PASS,
           f"{len(p['text'])} 字符" + ("" if len(p["text"]) >= CFG.MIN_CONTENT_CHARS else " < 阈值"))
          for p in ok_pages]
    agg_pages(R, "C13", st)
    prev = R.rows["C13"]
    R.set("C13", prev[0], prev[1] + ";retired 抽查未接(need-topic-queue)")

    # C14 body-hide 脚本
    st = []
    for p in ok_pages:
        hits = [pat for pat in CFG.BODY_HIDE_PATTERNS if re.search(pat, p["html"], flags=re.I)]
        st.append((p["url"], FAIL if hits else PASS, ";".join(hits)))
    agg_pages(R, "C14", st)

    # C15 渲染成本 × 声明
    rendering = site.get("rendering")
    if not rendering:
        R.set("C15", NA, "need-declaration(sites.yaml 未声明渲染策略)")
    elif rendering in ("ssg", "isr"):
        R.set("C15", PASS, f"声明 {rendering},免缓存头要求")
    else:
        st = []
        for p in ok_pages:
            cc = p["fetch"]["headers"].get("Cache-Control", "")
            ok = "s-maxage" in cc
            st.append((p["url"], PASS if ok else FAIL,
                       f"Cache-Control: {cc or '(无)'}"))
        agg_pages(R, "C15", st)

    # C16 snippet meta
    st = []
    for p in ok_pages:
        robots = metas(p["html"]).get("robots", "")
        ok = "max-snippet:-1" in robots.replace(" ", "") and "max-image-preview:large" in robots.replace(" ", "")
        st.append((p["url"], PASS if ok else FAIL, f"robots meta: {robots or '(无)'}"))
    agg_pages(R, "C16", st)

    # C24 viewport meta
    st = []
    for p in ok_pages:
        vp = metas(p["html"]).get("viewport", "")
        ok = CFG.VIEWPORT_REQUIRED_TOKEN in vp.replace(" ", "")
        st.append((p["url"], PASS if ok else FAIL,
                   "" if ok else f"viewport: {vp or '(无)'}"))
    agg_pages(R, "C24", st)

    # C17 标题层级
    st = []
    for p in ok_pages:
        hs = headings(p["html"])
        h1n = hs.count(1)
        probs = []
        if h1n != 1: probs.append(f"h1×{h1n}")
        prev_l = None
        for l in hs:
            if prev_l is not None and l > prev_l + 1:
                probs.append(f"跳级 h{prev_l}→h{l}"); break
            prev_l = l
        st.append((p["url"], FAIL if probs else PASS, ";".join(probs)))
    agg_pages(R, "C17", st)

    # C18 图片属性齐(width/height + alt)
    st = []
    for p in ok_pages:
        imgs = re.findall(r"<img\s[^>]*>", p["html"], flags=re.I)
        no_size = [i for i in imgs
                   if not (re.search(r"\bwidth\s*=", i, flags=re.I) and re.search(r"\bheight\s*=", i, flags=re.I))]
        # 判「属性在不在」而非「值空不空」:alt="" 是装饰图的正确写法,缺属性才是机器只能猜
        no_alt = [i for i in imgs if not re.search(r"\balt\s*=", i, flags=re.I)]
        probs = []
        if no_size: probs.append(f"{len(no_size)}/{len(imgs)} 图缺尺寸")
        if no_alt: probs.append(f"{len(no_alt)}/{len(imgs)} 图缺 alt 属性")
        st.append((p["url"], FAIL if probs else PASS,
                   ";".join(probs) if probs else f"{len(imgs)} 图尺寸+alt 齐"))
    agg_pages(R, "C18", st)

    # C19 OG 全套
    need = ["og:title", "og:description", "og:type", "og:url", "og:image"]
    st = []
    for p in ok_pages:
        mm = metas(p["html"])
        missing = [k for k in need if k not in mm]
        if "twitter:card" not in mm: missing.append("twitter:card")
        probs = ["缺 " + ",".join(missing)] if missing else []
        w, h = mm.get("og:image:width"), mm.get("og:image:height")
        if w and h and (w, h) != (str(CFG.OG_IMAGE_WIDTH), str(CFG.OG_IMAGE_HEIGHT)):
            probs.append(f"og:image 声明 {w}×{h} ≠ {CFG.OG_IMAGE_WIDTH}×{CFG.OG_IMAGE_HEIGHT}")
        img = mm.get("og:image", "")
        if img and not img.lower().startswith(("http://", "https://")):
            probs.append(f"og:image 非绝对 URL:{img}")
        # og:type 取值:合法词表 + 自证触发(页面 JSON-LD 自称文章 → 必须 article,不能 website)
        ogt = mm.get("og:type", "").lower()
        if ogt and ogt not in CFG.OG_VALID_TYPES:
            probs.append(f"og:type 非法取值:{ogt}")
        page_ld = {t for b in ld_blocks(p["html"]) if b[0] for t in ld_types(b[0])}
        if ogt and (page_ld & CFG.ARTICLE_LD_TYPES) and ogt != "article":
            probs.append(f"og:type={ogt},但页面 JSON-LD 自称 "
                         f"{','.join(sorted(page_ld & CFG.ARTICLE_LD_TYPES))} → 应为 article")
        st.append((p["url"], FAIL if probs else PASS, ";".join(probs)))
    agg_pages(R, "C19", st)

    # C20 跳转链(只统计成功抓取的页)
    st = []
    for p in pages:
        if p["fetch"]["status"] is None or throttled(p["fetch"]):
            continue
        hops = p["fetch"]["hops"]
        st.append((p["url"], PASS if hops <= CFG.MAX_REDIRECT_HOPS else FAIL,
                   f"{hops} hop"))
    agg_pages(R, "C20", st)

    # C25 mixed content(只判子资源;<a> 是导航出链,不触发拦截,不判)
    sub_re = re.compile(r"<(?:%s)\s[^>]*\bsrc\s*=\s*[\"']http://([^\"']+)"
                        % "|".join(CFG.SUBRESOURCE_TAGS), flags=re.I)
    link_re = re.compile(r"<link\s[^>]*\bhref\s*=\s*[\"']http://([^\"']+)", flags=re.I)
    st = []
    for p in ok_pages:
        if not p["fetch"]["final_url"].lower().startswith("https://"):
            st.append((p["url"], NA, "http 页,无混合内容可言")); continue
        hits = sub_re.findall(p["html"]) + link_re.findall(p["html"])
        st.append((p["url"], FAIL if hits else PASS,
                   f"{len(hits)} 处 http:// 子资源:" + ";".join("http://" + h for h in hits[:3])
                   if hits else ""))
    agg_pages(R, "C25", st)

    # C21/C22 人审
    R.set("C21", HUMAN, "上线前对照 C21 的 YMYL 信任块清单过检(见 checklist/references/C21.md)(触发:ymyl=true)")
    R.set("C22", HUMAN, "人工核对语言对两侧互指 + x-default(触发:站点有多语言配置)")

    R.throttled_total = f.throttled
    return R, mode, len(ok_pages), len(pages)

# ───────────────────────── 子过程 ─────────────────────────

def robots_blocks(txt, ua):
    """简化 robots 解析:该 UA 生效组里 Disallow:/ 且无 Allow:/ → 视为被拦。"""
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

def bad_link_evidence(bad):
    """C6 的坏出链证据:按 4xx 语义分组。判定不变(都算红 —— 爬虫跟着链接撞墙、消耗抓取预算),
    但**名字要对**:401/403 是「页面活着,只是不给匿名看」,和「内容没了」是两回事。
    统称「死链」会让人去找一个根本不存在的坏页面,而两类的修法完全不同:
      · 404/410/5xx → 内容没了 → 清入链(下架事务漏了一步,见 C13)
      · 401/403     → 页面活着,只是没给我们看 —— **成因不唯一,不许替它下结论**

    401/403 的成因至少五种,checker 分辨不了,所以只陈述事实 + 列出分支让人判:
      登录态/权限门 · WAF 反爬挑战(拦的是 checker,不是爬虫)· 地域封锁 · 配错权限 · 付费墙
    2026-08-25 实测教训:tigerless.com 的 /login、/user/Plan 三条 403 body 是
    「Just a moment...」= Cloudflare 挑战页,**根本不是登录门** —— 我第一版直接标成
    「登录态入口」,是拿个案倒推通例,错了。
    """
    def fmt(rows):
        return ";".join(f"{u} → {st}(来源 {src})" for u, st, src in rows[:5])
    restricted = [r for r in bad if r[1] in (401, 403)]
    broken = [r for r in bad if r[1] not in (401, 403)]
    parts = []
    if broken:
        parts.append(f"站内死链 {len(broken)} 条:{fmt(broken)}")
    if restricted:
        parts.append(f"访问受限 {len(restricted)} 条(401/403,页面存在但未返回内容;"
                     f"成因需人确认 — 登录态 / WAF 挑战 / 地域限制 / 权限配错。"
                     f"正解:未登录时不输出该链接或加 rel=nofollow + robots.txt Disallow + 不进 sitemap;"
                     f"若为 WAF 则核对规则是否放行已验证爬虫):{fmt(restricted)}")
    return ";".join(parts)

def lastmod_problems(entries):
    """C2 的 lastmod 三判:覆盖率 / 新鲜度 / 真实性。

    旧实现只做「有没有」+「最新一条够不够新」—— 量的是**最好的那一条**,于是:
    271 条里 1 条带 lastmod 算「有」;270 条烂在 2021 年,1 条是今天就算「新鲜」;
    取构建时间的站全站永远等于今天,反而永远绿灯。三个洞是同一个形状。
    """
    total = len(entries)
    dated = [(u, s) for u, s in entries if s]
    probs = []
    if not dated:
        return ["条目均无 lastmod"]
    if len(dated) < total:
        probs.append(f"lastmod 覆盖 {len(dated)}/{total} 条(应为全覆盖)")

    days = []
    for _, s in dated:
        try:
            days.append(datetime.fromisoformat(s[:10]).date())
        except Exception:
            pass
    if days:
        age = (NOW.date() - max(days)).days
        if age > CFG.SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS:
            probs.append(f"最新 lastmod {max(days)}(距今 {age} 天)"
                         f"> {CFG.SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS} 天,疑失养")

    # date-only:协议允许,但丢掉时分与时区,一天多改几次就分不出先后
    dateonly = [s for _, s in dated if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)]
    if dateonly:
        probs.append(f"{len(dateonly)}/{len(dated)} 条为 date-only(建议完整 W3C datetime 带时区)")

    # 真实性:最大单日簇 + 该日是否就是今天 → 构建时间戳天天命中,真实批量编辑次日自愈
    if days:
        top_day, top_n = collections.Counter(days).most_common(1)[0]
        ratio = top_n / len(days)
        if ratio >= CFG.SITEMAP_LASTMOD_CLUSTER_RATIO and top_day >= NOW.date():
            probs.append(f"疑构建时间戳:{top_n}/{len(days)} 条({ratio:.0%})lastmod = {top_day}"
                         f"(运行当天);真为批量编辑则次日自动转绿")
    return probs

def collect_sitemap(site, f, local, origin):
    """返回 (entries, err, shards)。entries = [(loc, lastmod_str | None)] —— **逐条配对**,
    不是两个独立的正则列表:覆盖率(多少条带 lastmod)只有配对之后才算得出来。
    shards = [(sitemap_url, 条目数)],用于单份规模判定(协议硬上限 5 万条)。"""
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
    """本地模式:把声明域(production host)映射为 TARGET host。"""
    if not local:
        return url
    prod = urlparse(site.get("production") or "")
    u = urlparse(url)
    if prod.netloc and u.netloc == prod.netloc:
        o = urlparse(origin)
        return u._replace(scheme=o.scheme, netloc=o.netloc).geturl()
    return url

def crawl_links(f, origin, max_pages):
    """BFS 内链;返回 (爬取页数, 发现的站内 URL 集合(norm), 是否触顶, 死链 [(url, status, 来源页)])。

    死链与 orphan 同源于这一次爬取:orphan 问「图上有没有这条边」,死链问「这条边通不通」。
    只覆盖站内链接 —— 站外出链每轮打第三方站,慢且易被 429/403 误报,归生成侧自检 + 人审(C6.md)。

    逐层并发:一层内的页互不依赖(新发现只会进**下一层**),所以整层可以并发抓,
    再**按层内原序**合并结果 —— 与逐页 BFS 的 discovered/parent/dead 完全一致,输出可复现。
    """
    o = urlparse(origin)
    start = norm_url(origin + "/")
    frontier, seen_fetch, discovered = [start], set(), {start}
    parent, dead, thr = {}, [], 0
    while frontier and len(seen_fetch) < max_pages:
        level = frontier[:max_pages - len(seen_fetch)]   # 与顺序版同样的截断点
        frontier = frontier[len(level):]
        for u, r in zip(level, f.map(f.get, level)):
            seen_fetch.add(u)
            if throttled(r):
                thr += 1                 # 限流页:不算死链,但它的出链没被解析 → orphan 判定也失真
                continue
            if r["status"] is None or r["status"] >= 400:
                dead.append((u, r["status"] or r["err"], parent.get(u, "(起点)")))
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

def crux_check(site, f):
    host = urlparse(site["origin"]).netloc
    try:
        r = requests.post(
            f"https://chromeuxreport.googleapis.com/v1/records:queryRecord?key={CFG.CRUX_API_KEY}",
            json={"origin": f"https://{host}"}, timeout=CFG.REQUEST_TIMEOUT)
        if r.status_code == 404:
            return NA, "need-crux-data(CrUX 无该站数据)"
        d = r.json().get("record", {}).get("metrics", {})
        def p75(k): return d.get(k, {}).get("percentiles", {}).get("p75")
        lcp, inp, cls = p75("largest_contentful_paint"), p75("interaction_to_next_paint"), p75("cumulative_layout_shift")
        probs = []
        if lcp and float(lcp) > CFG.CWV_LCP_MS: probs.append(f"LCP {lcp}ms")
        if inp and float(inp) > CFG.CWV_INP_MS: probs.append(f"INP {inp}ms")
        if cls and float(cls) > CFG.CWV_CLS: probs.append(f"CLS {cls}")
        return (FAIL if probs else PASS,
                ";".join(probs) or f"LCP {lcp} / INP {inp} / CLS {cls}")
    except Exception as e:
        return NA, f"CrUX 异常:{str(e)[:80]}"

# ───────────────────────── 报表输出 ─────────────────────────

CHECKS = [
    ("一、站级(每站一次)", [
        ("C1", "P0", "robots.txt 放行 ai-crawlers.yaml 全部 UA"),
        ("C2", "P0", "sitemap 可达、lastmod 新鲜、无 4xx/5xx 条目、单份 ≤5 万条"),
        ("C3", "P0", "归一 301:www/裸域、http/https、尾斜杠 → 同一 canonical host"),
        ("C26", "P0", "语言版本按 URL 固定,不按请求头分流(同一 URL 在各 Accept-Language 下落点必须一致)"),
        ("C4", "P1", "CWV:LCP<2.5s / INP<200ms / CLS<0.1"),
        ("C5", "P1", "IndexNow key 文件在站根可达"),
        ("C6", "P1", "内链图健康:无 orphan + 站内出链无 4xx/5xx(站外归人审)"),
        ("C7", "P2", "llms.txt 存在且为非空合法 markdown(重点页覆盖 = 人审)"),
    ]),
    ("二、每收录页", [
        ("C8", "P0", "自引用 canonical(== 归一 URL),HTML 与 HTTP header 两路不冲突"),
        ("C9", "P0", "服务端直出完整正文(禁 CSR 空壳)"),
        ("C10", "P0", "缓存 HTML 为无个性化公共版"),
        ("C23", "P0", "收录页无 noindex(meta robots/googlebot + X-Robots-Tag)"),
        ("C11", "P1", "title 唯一 ≤60;description 唯一 ≤150"),
        ("C12", "P1", "JSON-LD:块/基础组/出现类型的必填参数/无不采纳类型(声明↔可见一致 = 人审)"),
        ("C13", "P1", "无 soft 404 / 空壳 200(retired 走 301/410)"),
        ("C14", "P1", "无 body-hide 型第三方脚本"),
        ("C16", "P1", "snippet 控制:max-snippet:-1, max-image-preview:large"),
        ("C24", "P1", "viewport meta 存在且含 width=device-width"),
        ("C17", "P2", "标题层级:恰好一个 h1,h2→h3 逐级不跳级"),
        ("C18", "P2", "图片属性齐:显式 width/height + 每张具 alt 属性"),
        ("C19", "P2", "OG 全套 + twitter:card;og:type 取值正确;og:image 绝对 URL"),
        ("C20", "P2", "无跳转链:redirect hop ≤1"),
        ("C15", "P2", "渲染成本策略与声明一致(SSR 须 s-maxage+SWR / SSG 免)"),
        ("C25", "P2", "HTTPS 页无 mixed content(子资源不走 http://)"),
    ]),
    ("三、条件项(人审项;flag / 站点配置触发)", [
        ("C21", "P0", "YMYL 信任块(byline/审核/更新标注可见;引用权威;JSON-LD 与可见一致)"),
        ("C22", "P1", "hreflang 页面级双向互指 + x-default"),
    ]),
]

ICON = {PASS: "✅ pass", FAIL: "🔴 fail", NA: "⚪ N.A.", HUMAN: "👤 人审"}

def verify_checklist_sync():
    """漂移守卫:CHECKS(报告骨架)必须与 checklist/checklist.md 的条目一致。
    检查逻辑无法自动生成(每条手写),但「有哪些条目、什么优先级、在哪一节」必须对得上;
    对不上就喊出来,不让报告默默说谎。

    返回漂移消息列表(空 = 对齐)—— 打印是给人看的,返回值是给 CI 看的。"""
    md = CHECKLIST_MD
    if not md.exists():
        print("⚠️  未找到 checklist.md,跳过同步校验", flush=True); return []
    doc, sec = [], -1
    for line in md.read_text().splitlines():
        if line.startswith("## ") and re.match(r"## [一二三]、", line):
            sec += 1
        m = re.match(r"\|\s*(C\d+)\s*\|\s*(P\d)\s*\|", line)
        if m and sec >= 0:
            doc.append((sec, m.group(1), m.group(2)))
    code = [(i, cid, prio) for i, (_, items) in enumerate(CHECKS) for cid, prio, _ in items]
    if doc == code:
        return []
    msgs = []
    d, c = {x[1]: x for x in doc}, {x[1]: x for x in code}
    for cid in sorted(set(d) - set(c), key=lambda s: int(s[1:])):
        msgs.append(f"⚠️  漂移:checklist 有 {cid}(优先级 {d[cid][2]}),脚本未实现")
    for cid in sorted(set(c) - set(d), key=lambda s: int(s[1:])):
        msgs.append(f"⚠️  漂移:脚本有 {cid},checklist 已无此条目")
    for cid in sorted(set(d) & set(c), key=lambda s: int(s[1:])):
        if d[cid][2] != c[cid][2]:
            msgs.append(f"⚠️  漂移:{cid} 优先级 checklist={d[cid][2]} / 脚本={c[cid][2]}")
        elif d[cid][0] != c[cid][0]:
            msgs.append(f"⚠️  漂移:{cid} 所属节 checklist=第{d[cid][0]+1}节 / 脚本=第{c[cid][0]+1}节")
    for m in msgs:
        print(m, flush=True)
    return msgs

def render_report(site, R, mode, ok_n, total_n, args):
    lines = [f"# checker 报告:{site['id']}",
             "",
             f"- 目标:{site['origin']}({mode})",
             f"- 时间:{NOW.strftime('%Y-%m-%d %H:%M UTC')} · 页面 {ok_n}/{total_n}"
             f"({'全量' if args.page_sample == 0 else f'抽样上限 {args.page_sample}'})"
             f" · sitemap 抽查 {args.sitemap_sample} · 内链爬取上限 {args.max_pages}"
             f" · 并发 {args.workers} × 间隔 {args.sleep}s",
             f"- 判定参数:checker/config.py;条目定义:checklist/checklist.md", ""]
    if getattr(R, "throttled_total", 0):
        lines += [f"- 🚦 **被目标限流 {R.throttled_total} 次(429/503),其中页面样本 "
                  f"{getattr(R, 'thr_pages', 0)} 页**——受影响的判定已记 N.A. 而非 fail"
                  f"(限流是我们打太快,不是站点有问题)。想要完整结论:"
                  f"`--workers {max(1, args.workers // 2)}` 或调大 `--sleep` 重跑。", ""]
    if getattr(R, "fetch_fails", None):
        lines.append("- ⚠️ 样本抓取失败(非限流):" + ";".join(R.fetch_fails[:6]) +
                     (f" …共 {len(R.fetch_fails)}" if len(R.fetch_fails) > 6 else ""))
        lines.append("")
    counts = {"fail_p0": 0, "fail": 0, "pass": 0, "na": 0}
    for sec, items in CHECKS:
        lines += [f"## {sec}", "", "| ID | 优先级 | 检查 | 结果 | 证据 |", "|---|---|---|---|---|"]
        for cid, prio, name in items:
            status, ev = R.rows.get(cid, (NA, "未实现"))
            if status == FAIL:
                counts["fail"] += 1
                if prio == "P0": counts["fail_p0"] += 1
            elif status == PASS: counts["pass"] += 1
            elif status == NA: counts["na"] += 1
            ev = ev.replace("|", "\\|")
            lines.append(f"| {cid} | {prio} | {name} | {ICON[status]} | {ev} |")
        lines.append("")
    lines.insert(5, f"**结论:🔴 {counts['fail']}(其中 P0 {counts['fail_p0']})· "
                    f"✅ {counts['pass']} · ⚪ N.A. {counts['na']} · 👤 人审 2**")
    return "\n".join(lines)

COLS = ("site", "url", "rule_id", "status", "evidence", "checked_at")

def save_db(db_path, site_id, R):
    """checks 快照落库。2026-08-25 去掉 page_type 列(页型退役)——
    旧库自动迁移:按列名搬运幸存字段,历史快照不丢,diff 还能继续做。"""
    conn = sqlite3.connect(db_path)
    old = [r[1] for r in conn.execute("PRAGMA table_info(checks)")]
    if old and old != list(COLS):
        conn.execute("ALTER TABLE checks RENAME TO checks_old")
        conn.execute(f"CREATE TABLE checks({','.join(c + ' TEXT' for c in COLS)},"
                     f" PRIMARY KEY(site, url, rule_id))")
        keep = [c for c in COLS if c in old]          # 按列名搬,不靠位置
        conn.execute(f"INSERT INTO checks({','.join(keep)}) SELECT {','.join(keep)} FROM checks_old")
        conn.execute("DROP TABLE checks_old")
    else:
        conn.execute(f"CREATE TABLE IF NOT EXISTS checks({','.join(c + ' TEXT' for c in COLS)},"
                     f" PRIMARY KEY(site, url, rule_id))")
    ts, ph = NOW.isoformat(), ",".join("?" * len(COLS))
    for cid, (status, ev) in R.rows.items():
        conn.execute(f"REPLACE INTO checks VALUES({ph})", (site_id, "@site", cid, status, ev, ts))
    for url, cid, status, ev in R.page_rows:
        conn.execute(f"REPLACE INTO checks VALUES({ph})", (site_id, url, cid, status, ev, ts))
    conn.commit(); conn.close()

# ───────────────────────── main ─────────────────────────

def sites_file(override=None):
    """找站点花名册。<state_dir>/sites.yaml 为准,包内 sites.yaml 是旧布局的兼容回退。

    找不到时不静默跑空 —— 直接退出并把该建在哪、照谁抄说清楚。
    「配置缺失」是使用者的问题,不是脚本该猜的东西。
    """
    sd = CFG.state_dir(override)
    for f in (sd / "sites.yaml", ROOT / "sites.yaml"):
        if f.exists():
            return f
    sys.exit(
        f"没找到 sites.yaml。多站要先建一份站点花名册:\n"
        f"  mkdir -p {sd}\n"
        f"  cp {ROOT / 'sites.example.yaml'} {sd / 'sites.yaml'}\n"
        f"然后按注释改成自己的站。只跑单个站不需要本文件:--target https://example.com"
    )


def load_sites(args):
    if args.target or CFG.TARGET:
        t = (args.target or CFG.TARGET).rstrip("/")
        p = urlparse(t)
        if not p.scheme or not p.netloc or p.path not in ("", "/") or p.query or p.fragment:
            sys.exit(f"TARGET 必须是根 URL(origin),收到:{t}")
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
        sys.exit("sites.yaml 无匹配站点")
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
                    help="并发抓取线程数;1 = 顺序执行(对拍用)")
    ap.add_argument("--state-dir", default=None,
                    help="花名册与产出目录;默认 ~/Documents/seo-ops,也可用 $SEO_OPS_DIR")
    ap.add_argument("--out", default=None, help="报告与 checks.db 落在哪;默认 <state-dir>/out")
    ap.add_argument("--verify-only", action="store_true",
                    help="只跑漂移守卫(清单 vs 脚本),不联网;有漂移则以 1 退出。CI 用")
    args = ap.parse_args()

    if args.verify_only:
        drift = verify_checklist_sync()
        print("✅ 清单与脚本对齐" if not drift else f"🔴 {len(drift)} 处漂移", flush=True)
        sys.exit(1 if drift else 0)

    # state_dir 要等 argparse 之后才确定,而 .env 在 import config 时就读过一遍了 —— 重读一次。
    sd = CFG.state_dir(args.state_dir)
    CFG.load_env(sd); CFG.refresh_secrets()

    verify_checklist_sync()
    out_dir = Path(args.out) if args.out else sd / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    sites = load_sites(args)
    failed = []
    for site in sites:
        # 每站独立隔离:A 站崩了不该让 B 站白等。多站工具的基本要求。
        print(f"== {site['id']} ({site['origin']}) ==", flush=True)
        try:
            f = Fetcher(args.sleep, args.workers)
            R, mode, ok_n, total_n = check_site(site, f, args)
            report = render_report(site, R, mode, ok_n, total_n, args)
            path = out_dir / f"report-{site['id']}-{NOW.strftime('%Y%m%d')}.md"
            path.write_text(report)
            save_db(out_dir / "checks.db", site["id"], R)
            print(report.split("\n**结论")[1].split("\n")[0].replace("**", "").lstrip(":"), flush=True)
            print(f"→ {path}", flush=True)
        except Exception:
            failed.append(site["id"])
            print(f"🔴 {site['id']} 检查中断,该站无结果:", flush=True)
            traceback.print_exc()
            print("(其余站点继续)", flush=True)

    # 退出码:**静默成功是验收工具唯一不能接受的失败模式**。
    # 脚本自己崩了必须比它报的红项更响 —— 不然放进 cron 就是「挂了看起来像正常」。
    # 注意:被 `| tee` 一类管道包住时退出码会被吃掉,调用方需 `set -o pipefail`。
    if failed:
        print(f"\n🔴 {len(failed)}/{len(sites)} 个站点检查中断:{', '.join(failed)}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
