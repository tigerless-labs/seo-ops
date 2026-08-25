"""checker 参数配置 — 全部可调参数的唯一入口(默认值即阶段一基线)。

原则:判定逻辑住 run.py,判定参数住本文件;改阈值/清单只动这里,人审后合并。
**机密不进本文件** — API key 一类住 `<state_dir>/.env`(已 gitignore),模板见 `.env.example`。
C4(CWV)无数据时 checker 输出 no-data(N.A.),不判红——阈值本身是 Google 官方常量。
C 编号对应 checklist/checklist.md(2026-08-24 重排后)。
"""
import os
from pathlib import Path

def state_dir(override=None):
    """实例状态(sites.yaml / .env / out/)住哪 —— **不住包内,住项目侧**。

    优先级:--state-dir > $SEO_OPS_DIR > ${CLAUDE_PROJECT_DIR:-cwd}/.seo-ops

    为什么不放包内:这份 checker 会被复制进 skill 目录,而 skill 更新 = 整包覆盖,
    包内的可写状态必然随更新丢失(checks.db 尤其可惜,它设计成跨次累积好做 diff)。
    状态该跟着「被检查的项目」走,而不是跟着「工具装在哪」走。

    **注意 `CLAUDE_PROJECT_DIR` 在 Bash 里通常读不到** —— Claude Code 只把它作为
    字符串替换喂给 SKILL.md 正文与 allowed-tools,以及作为环境变量喂给 hook / stdio MCP
    等被 spawn 的进程;Bash 工具的 shell 不在其列。所以 skill 里的调用**必须显式传**
    `--state-dir ${CLAUDE_PROJECT_DIR}/.seo-ops`(替换在 markdown 里就完成了)。
    这里仍读一次环境变量,是为了 hook / MCP 那类真能拿到它的场景。
    都没有时退到 cwd:clone 本仓库直接用时 cwd 就是仓库根,得到 <仓库>/.seo-ops/。
    """
    if override:
        return Path(override).expanduser().resolve()
    if os.environ.get("SEO_OPS_DIR"):
        return Path(os.environ["SEO_OPS_DIR"]).expanduser().resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve() / ".seo-ops"

def load_env(d=None):
    """读 <state_dir>/.env,再读包内 checker/.env(旧布局,兼容)。

    `setdefault` 而非赋值:**已 export 的环境变量永远赢过文件** —— CI 里注入 key
    不该被谁的本地 .env 盖掉。先读的先赢,所以 state_dir 的 .env 优先于包内旧的。
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

    sd = d or state_dir()
    legacy = Path(__file__).with_name(".env")
    for f in (sd / ".env", legacy):
        if not f.exists():
            continue
        kv = parse(f)
        fresh = [k for k in kv if k not in os.environ]
        for k, v in kv.items():
            os.environ.setdefault(k, v)
        # 静默的包内配置最坑:同一条命令换个安装位置就给出不同结论(实测 C4 一处出
        # 实测值、一处记 need-crux-key)。兼容可以留,但必须让人看见。
        # 只在它**真的提供了值**时才喊 —— 被上一份盖掉时喊,就成了每次都响的噪音。
        if f == legacy and fresh:
            print(f"⚠️  {', '.join(fresh)} 来自包内 {legacy} —— 它随 skill 更新会被覆盖。"
                  f"请移到 {sd / '.env'}", flush=True)

load_env()

# ── 运行目标(单参数,模式自动判定)────────────────────
# TARGET:站点**根 URL(origin)** = scheme + host[:port],不带 path/query/fragment
#   (合法:"http://localhost:3000"、"https://www.tigerless.com";
#    非法:"…/blog"、"…?x=1" — 脚本启动即校验报错,不猜)。
#   一切入口从根派生:/robots.txt、sitemap、llms.txt、内链爬取起点。
#   空 = 按 sites.yaml 全部站点跑(线上)。
#   - host 为 localhost / 127.x / 裸 IP / *.local → **本地模式**:
#     C3/C4 记 N.A.(reason=need-domain);C2/C6/C8 的绝对 URL 比对降级为
#     自洽检查(声明 host 从产出内部推断多数值,替换为 TARGET host 后抓取验证)。
#   - 否则 → **域名模式**:全量判定;C4 无 CrUX 数据时记 N.A.(reason=need-crux-data)。
# 不支持公网 staging 域(会被当生产域测,C3 误红)——测试二选一:上线,或本地部署。
TARGET = ""    # e.g. "http://localhost:3000" 或 "https://www.tigerless.com"

# ── 抓取 ──────────────────────────────────────────────
# 真实浏览器 UA:Cloudflare 拦伪装爬虫 UA(2026-08-21 tigerless.com 实测 403)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
REQUEST_TIMEOUT = 20          # 秒
FETCH_SLEEP = 1.0             # **单个 worker** 两次请求的间隔(秒);整体 QPS ≈ FETCH_CONCURRENCY / FETCH_SLEEP
# 默认 1 = 顺序执行。271 页约 7 分钟 —— 对每日定时任务毫无痛感,
# 却省掉一整类风险(线程安全、共享退避状态、限流误报、并发对拍的验证负担)。
# 实测:顺序跑对 tigerless.com **零限流**;那些 429 全是并发打出来的。
# `Fetcher.map()` 在 workers<=1 时走的就是普通列表推导,不建线程 —— 并发只是留了个接缝,不是默认路径。
# 什么时候再打开:站点规模上千页、单轮超过 20 分钟时。届时**必须重做并发对拍**(见 README)。
FETCH_CONCURRENCY = 1
PAGE_SAMPLE_SIZE = 0          # 页级检查覆盖范围:0 = sitemap 登记的全部页(默认);>0 = 抽样上限(调试用)

# ── 限流自适应(并发的安全带)──────────────────────────
# 被限流的请求**不算检查不通过** —— 那是我们打太快,不是站点有问题。
# 429/503 一律:退避重试 → 仍不行则记 N.A.(reason=throttled),并全局减速 + 报告顶部告警。
# 教训(2026-08-25 实测):8 worker × 1s 对 tigerless.com = 271 页里 192 页吃 429,
# 「站内死链」从 2 条虚报成 106 条 —— 假红比跑得慢危险得多。
THROTTLE_STATUSES = (429, 503)
THROTTLE_RETRIES = 3          # 单请求遇限流的重试次数(指数退避;有 Retry-After 头则听它的)
THROTTLE_BACKOFF = 2.0        # 首次退避秒数,之后翻倍
THROTTLE_MAX_SLEEP = 4.0      # 自适应叠加到每请求间隔上的上限(秒)
THROTTLE_RECOVER_AFTER = 20   # 连续成功多少次回落一档(AIMD:撞墙乘性退避,顺畅了加性恢复)
                              # 缺了这一半 = 退避只涨不降,早期一次 429 就把整轮永久拖慢 5 倍

# ── C2 sitemap ───────────────────────────────────────
SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS = 30   # 全站最新 lastmod 距今超此值 = sitemap 失养
SITEMAP_URL_SAMPLE_SIZE = 20               # 条目可达性(无 4xx/5xx)抽查数
SITEMAP_MAX_URLS_PER_FILE = 50000          # 协议硬上限(sitemaps.org):单份超限整份失效,须走 index 分片
# lastmod 真实性:构建时间戳的定义 = 永远等于最近一次构建。checker 天天跑,所以只需判
# 「最大单日簇占比 ≥ 阈值 且 该日 == 运行当天」—— 构建戳天天命中,真实批量编辑只在当天误报一次,
# 次日日期退到过去自动转绿。误报有自愈期,漏报没有(见 references/C2.md)。
SITEMAP_LASTMOD_CLUSTER_RATIO = 0.20

# ── C26 自动语言重定向(站级,抽样)────────────────────
# 同一 URL 在不同 Accept-Language 下落点不同 = 按推测语言自动跳转。
# Googlebot 不发 Accept-Language → 只能看到默认语言版,另一版对爬虫等于不存在。
LANG_REDIRECT_SAMPLE_SIZE = 5
LANG_REDIRECT_PROBES = ("en-US,en;q=0.9", "zh-CN,zh;q=0.9")

# ── C4 CWV(Google 官方 good 阈值,常量)──────────────
CWV_LCP_MS = 2500
CWV_INP_MS = 200
CWV_CLS = 0.1
CRUX_API_KEY = os.environ.get("CRUX_API_KEY", "")   # 住 .env;空 = 未接 CrUX,C4 记 N.A.(need-crux-key)

# ── C5 IndexNow ──────────────────────────────────────
# 住 .env:INDEXNOW_KEYS=site_id:key,site_id:key(key 即站根 {key}.txt 的文件名与内容)
INDEXNOW_KEYS = dict(                               # 未登记 = N.A.(need-key-declaration)
    pair.split(":", 1) for pair in
    (p.strip() for p in os.environ.get("INDEXNOW_KEYS", "").split(",")) if ":" in pair
)

def refresh_secrets():
    """`--state-dir` 在 argparse 之后才知道,而上面两个常量在 import 时就定了。
    run.py 解析完参数后调一次,按新的 state_dir 重读 .env 并刷新。"""
    global CRUX_API_KEY, INDEXNOW_KEYS
    CRUX_API_KEY = os.environ.get("CRUX_API_KEY", "")
    INDEXNOW_KEYS = dict(
        pair.split(":", 1) for pair in
        (p.strip() for p in os.environ.get("INDEXNOW_KEYS", "").split(",")) if ":" in pair
    )

# ── C6 无 orphan(内链图爬取)─────────────────────────
CRAWL_MAX_PAGES = 5000        # 内链图爬取上限(防失控)

# ── C9 服务端直出(v1 启发式;比例判定待接 headless)────
SSR_TEXT_RATIO = 0.90         # 目标判定:禁 JS 文本 / 渲染版文本 下限(headless 接入后启用)
SSR_MIN_TEXT_CHARS = 500      # v1 启发式:禁 JS 抓取正文低于此值 = 疑似 CSR 空壳

# ── C10 缓存公共版 ────────────────────────────────────
CACHE_DIFF_SAMPLE_SIZE = 10   # 同 URL 双抓 diff 的抽查页数

# ── C11 title / description ──────────────────────────
TITLE_MAX_CHARS = 60
DESC_MAX_CHARS = 150

# ── C12 JSON-LD 基础项 ───────────────────────────────
ORG_TYPES = {"Organization", "InsuranceAgency", "LocalBusiness", "Corporation",
             "OnlineBusiness", "MedicalOrganization"}   # 视同 Organization 的子类型

# 出现即查的类型必填参数(**纯自证触发**:页面声明了该类型就查这一行,零外部输入)。
# 清单来源 = references/C12.md 二节(本系统采纳线,权威依据 = Google 各 feature 文档),
# 改那张表须同步改这里 —— 漂移守卫不覆盖这一对,靠人。
# 2026-08-25:页型条件退役后,**「该有而没有」不再有任何一方判定**
# (产品页整页没有 Product 标记这类缺失,checker 与人审都不覆盖)——
# 取舍见 references/C12.md 开头说明。
TYPE_REQUIRED = {
    "Article":          ["headline", "image", "datePublished", "dateModified", "author"],
    "NewsArticle":      ["headline", "image", "datePublished", "dateModified", "author"],
    "BlogPosting":      ["headline", "image", "datePublished", "dateModified", "author"],
    "FAQPage":          ["mainEntity"],
    "ProfilePage":      ["mainEntity"],   # Google 富媒体清单内(作者/员工档案页);2026-08-25 采纳
    "BreadcrumbList":   ["itemListElement"],
    "ItemList":         ["itemListElement"],
    "InsuranceProduct": ["name", "description"],
    "Product":          ["name", "description"],
    "Offer":            ["price", "priceCurrency"],
    "Person":           ["name"],
}

# 负向扫描:出现即红。清单来源 = references/C12.md 二节 4「负向约束」
# 判据统一是「**谁消费它、给什么回报**」—— 答不出就不发出去,发了只有维护成本没有回报。
# 2026-08-25:`AggregateRating` 移出本清单 —— 它的问题不是「没有消费方」(Google 真消费,
# 出星级),而是「有没有真实评价数据」,那是内容真实性问题,归 R5 红线与人审,不是结构检查该判的。
# 混在这里会让判据变成两套,清单也就说不清自己在拦什么。
LD_REJECTED_TYPES = {
    "SiteNavigationElement": "无消费方;导航信息 <nav> 已表达",
    "SearchAction":       "Google 2024-10 下线 sitelinks searchbox,消费方已消失",
    # WebPage 子类型整体不采纳:Google 无对应富媒体、无已知回报。
    # 例外(不在此列,是真该声明的):FAQPage、ProfilePage
    "ItemPage": "WebPage 子类型,无回报", "CollectionPage": "WebPage 子类型,无回报",
    "AboutPage": "WebPage 子类型,无回报", "ContactPage": "WebPage 子类型,无回报",
    "CheckoutPage": "WebPage 子类型,无回报", "SearchResultsPage": "WebPage 子类型,无回报",
}

# ── C13 soft 404 / 空壳 200 ──────────────────────────
MIN_CONTENT_CHARS = 400       # 去标签正文字符数低于此值 = 疑似空壳
RETIRED_SAMPLE_SIZE = 10      # retired 条目状态码抽查数

# ── C14 body-hide 第三方脚本(人维护清单,新工具在此追加)──
BODY_HIDE_PATTERNS = [
    r"hide_element\s*=\s*'body'",        # VWO
    r"body\s*\{[^}]*opacity\s*:\s*0",    # 通用 anti-flicker
    r"async-hide",                       # Google Optimize 系 anti-flicker
]

# ── C19 OG ───────────────────────────────────────────
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630
OG_VALID_TYPES = {"website", "article", "book", "profile", "product",
                  "video.other", "video.movie", "music.song"}   # 合法 og:type(ogp.me 词表常用子集)
# 自证触发:页面 JSON-LD 出现这些类型 = 自称文章 → og:type 必须是 article,不能是 website
ARTICLE_LD_TYPES = {"Article", "NewsArticle", "BlogPosting", "TechArticle", "ScholarlyArticle"}

# ── C20 跳转链 ───────────────────────────────────────
MAX_REDIRECT_HOPS = 1         # 任意入站 URL 允许的最大重定向次数

# ── C23 noindex(收录页禁出现)────────────────────────
NOINDEX_TOKENS = ("noindex", "none")          # none ≡ noindex,nofollow
NOINDEX_META_NAMES = ("robots", "googlebot")  # googlebot 是独立条目,不被 robots 覆盖

# ── C24 viewport ─────────────────────────────────────
VIEWPORT_REQUIRED_TOKEN = "width=device-width"

# ── C25 mixed content(只判子资源,导航出链 <a> 不算)──
SUBRESOURCE_TAGS = ("img", "script", "iframe", "video", "audio", "source", "embed", "object")
