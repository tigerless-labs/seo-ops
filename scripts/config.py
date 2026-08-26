"""checker 参数配置 — 全部可调参数的唯一入口(默认值即阶段一基线)。

原则:判定逻辑住 run.py,判定参数住本文件;改阈值/清单只动这里,人审后合并。
**机密不进本文件** — API key 一类住 `<config_dir>/.env`(默认 ~/.config/seo-ops/),模板见 `references/.env.example`。
C4(CWV)无数据时 checker 输出 no-data(N.A.),不判红——阈值本身是 Google 官方常量。
C 编号对应 references/checklist/checklist.md(2026-08-24 重排后)。
"""
import json, os
from pathlib import Path

def _documents_dir():
    """用户的「文档」目录。

    macOS 上若开了 iCloud 的「桌面与文稿」同步,~/Documents 会被重定向到
    ~/Library/Mobile Documents/... —— `Path.home()/"Documents"` 跟着符号链接走,拿到的是对的。
    报告因此可能被同步进 iCloud,这正是机密要单独放 config_dir 的原因。

    **Windows 未支持**:那边「文档」可能被 OneDrive 重定向,真值在注册表里,
    而这里拼出来的路径可能是个空壳。没有 Windows 环境可验,就不写没测过的分支
    —— 真要在 Windows 上跑,显式传 --state-dir 或设 $SEO_OPS_DIR。
    """
    return Path.home() / "Documents"


def _config_base():
    """机密目录的基座:$XDG_CONFIG_HOME 或 ~/.config(macOS / Linux 通用)。"""
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def state_dir(override=None):
    """**产出**住哪(报告与 checks.db)。--state-dir > $SEO_OPS_DIR > <文档目录>/seo-ops

    **不住包内**:这份 checker 会被复制进 skill 目录,而 skill 更新 = 整包覆盖,
    包内的可写状态必然随更新丢失(checks.db 尤其可惜,它设计成跨次累积好做 diff)。

    **也不住 cwd 或某个项目里**:checks.db 是**站点**的历史,属于「你负责哪些站」,
    不属于「你此刻在哪个代码仓库里」。同一批站从三个仓库验收,不该得到三份割裂的历史。

    落在 ~/Documents 是刻意的:报告是**给人读、要拿去跟施工方对账**的产出,
    该待在用户找得到的地方,不是藏在 dotfile 里(同 last30days 的 MEMORY_DIR 约定)。

    **配置不在这儿** —— `sites.yaml` 与 `.env` 都归 config_dir()。分界是
    「配置 / 产出」,不是「敏感 / 不敏感」:花名册不是机密,但它是你**输入**给工具的
    东西,跟工具**吐出来**的报告是两回事,混在一个目录里迟早分不清哪个能删。

    附带好处:不依赖任何 agent 私有变量,所以 Claude Code / Codex / 裸命令行行为一致。
    """
    if override:
        # 未被替换的占位符守卫。默认值已不依赖任何 agent 私有变量,但旧版 SKILL.md 里
        # 写过 `--state-dir ${CLAUDE_PROJECT_DIR}/.seo-ops` —— 那是 Claude Code 的私有扩展,
        # 不在 Agent Skills spec 里,别家 agent 照抄不会替换。两种烂法:
        #   原样传进来  → override 里还带着 "${"
        #   被 shell 吃掉 → 变成 "/.seo-ops",父目录是根
        # 后者在容器里以 root 跑会**真的建在文件系统根目录**,静默落错地方。宁可停。
        if "${" in str(override) or "$(" in str(override):
            raise SystemExit(
                f"--state-dir 里有没被替换的变量:{override}\n"
                f"`${{CLAUDE_PROJECT_DIR}}` 只有 Claude Code 会替换。**直接省略 --state-dir**\n"
                f"即可(默认 ~/Documents/seo-ops),或传一个真实路径 / 设 $SEO_OPS_DIR。")
        p = Path(override).expanduser().resolve()
        if p.parent == Path(p.anchor):
            raise SystemExit(
                f"--state-dir 指到了文件系统根下:{p}\n"
                f"多半是某个变量展开成了空字符串。**直接省略 --state-dir** 即可\n"
                f"(默认 ~/Documents/seo-ops),或传一个真实路径 / 设 $SEO_OPS_DIR。")
        return p
    if os.environ.get("SEO_OPS_DIR"):
        return Path(os.environ["SEO_OPS_DIR"]).expanduser().resolve()
    return _documents_dir() / "seo-ops"


def config_dir():
    """**配置**住哪(sites.yaml 与 .env)。$SEO_OPS_CONFIG_DIR > ${XDG_CONFIG_HOME:-~/.config}/seo-ops

    **与 state_dir 分开是有意的**,两条理由叠在一起:

    1. 配置是**输入**,报告是**输出** —— 混一个目录里迟早分不清哪个能删。
    2. 产出放 ~/Documents 是为了让人找得到,但 Documents 常被 iCloud / OneDrive /
       Dropbox 同步、被备份、被整夹分享出去,API key 不能跟着走。~/.config 不进这些通道。

    (同 last30days:产出进 Documents,key 进 ~/.config/last30days/.env。)
    """
    if os.environ.get("SEO_OPS_CONFIG_DIR"):
        return Path(os.environ["SEO_OPS_CONFIG_DIR"]).expanduser().resolve()
    return _config_base().expanduser().resolve() / "seo-ops"

def load_env(d=None):
    """按顺序读 .env,先读到的先赢:

      1. <config_dir>/.env      —— 正位(默认 ~/.config/seo-ops/.env)
      2. <state_dir>/.env       —— 旧布局,告警
      3. 包内 scripts/.env      —— 更旧的布局,告警

    `setdefault` 而非赋值:**已 export 的环境变量永远赢过所有文件** —— CI 里注入 key
    不该被谁的本地 .env 盖掉。
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
               ((d or state_dir()) / ".env", "旧布局(机密不该跟产出同住,Documents 常被云同步)"),
               (Path(__file__).with_name(".env"), "包内旧布局(随 skill 更新会被覆盖)")]
    for f, why in sources:
        if not f.exists():
            continue
        kv = parse(f)
        fresh = [k for k in kv if k not in os.environ]
        for k, v in kv.items():
            os.environ.setdefault(k, v)
        # 只在它**真的提供了值**时才喊 —— 被上一份盖掉时也喊,就成了每次都响的噪音。
        # 但真提供了值就必须喊:静默的错位配置会让同一条命令在两台机器上给出不同结论
        # (实测 C4 一处出实测值、一处记 need-crux-key)。
        if why and fresh:
            print(f"⚠️  {', '.join(fresh)} 来自 {f} —— {why}。请移到 {canonical}", flush=True)

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
CRUX_API_KEY = os.environ.get("CRUX_API_KEY", "")   # 住 <config_dir>/.env;空 = C4 记 N.A.(need-crux-key)

# ── C5 IndexNow ──────────────────────────────────────
# 住 <config_dir>/.env:INDEXNOW_KEYS=site_id:key,site_id:key(key 即站根 {key}.txt 的文件名与内容)
INDEXNOW_KEYS = dict(                               # 未登记 = N.A.(need-key-declaration)
    pair.split(":", 1) for pair in
    (p.strip() for p in os.environ.get("INDEXNOW_KEYS", "").split(",")) if ":" in pair
)

def refresh_secrets():
    """`--state-dir` 在 argparse 之后才知道(它影响 load_env 的第二个候选位置),
    而上面两个常量在 import 时就定了。run.py 解析完参数后调一次,重读并刷新。"""
    global CRUX_API_KEY, INDEXNOW_KEYS
    CRUX_API_KEY = os.environ.get("CRUX_API_KEY", "")
    INDEXNOW_KEYS = dict(
        pair.split(":", 1) for pair in
        (p.strip() for p in os.environ.get("INDEXNOW_KEYS", "").split(",")) if ":" in pair
    )

# ── C6 站内出链(内链图爬取)───────────────────────────
CRAWL_MAX_PAGES = 5000        # 爬取上限(防失控);触顶则覆盖不完整,记 N.A.

# ── C9 服务端直出(v1 启发式;比例判定待接 headless)────
SSR_TEXT_RATIO = 0.90         # 目标判定:禁 JS 文本 / 渲染版文本 下限(headless 接入后启用)
SSR_MIN_TEXT_CHARS = 500      # v1 启发式:禁 JS 抓取正文低于此值 = 疑似 CSR 空壳

# ── C10 缓存公共版 ────────────────────────────────────
CACHE_DIFF_SAMPLE_SIZE = 10   # 同 URL 双抓 diff 的抽查页数

# ── 报告渲染 ─────────────────────────────────────────
# 报告「说明」列的链接基址。给 GitHub URL 是为了报告发到哪都点得开(相对路径只有
# 装了 skill 的人能用)。**仓库私有时对外人仍是 404** —— 要给施工方看就得改 public。
# 想让验收文档引用「出报告那一刻」的说明,把 main 换成当次的 commit SHA。
DOC_BASE_URL = "https://github.com/tigerless-labs/seo-ops/blob/main/references/checklist/references"
EVIDENCE_MAX_CHARS = 300      # 单格证据上限;超出截断并指向 checks.db(库里存全量)

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

# ── 用户可覆盖的参数 ──────────────────────────────────
# 名字 → 一行说明。**只有这里登记的项**能被 <config_dir>/config.yaml 覆盖。
#
# 不在这份白名单里的是有意排除的,分三类:
#   机密    CRUX_API_KEY / INDEXNOW_KEYS —— 住 .env,不进明文配置
#   常量    CWV_LCP_MS / CWV_INP_MS / CWV_CLS(Google 官方 good 阈值)、
#           SITEMAP_MAX_URLS_PER_FILE(sitemaps.org 协议硬上限)、
#           VIEWPORT_REQUIRED_TOKEN —— 调了就不是这条检查了
#   结构化  TYPE_REQUIRED / LD_REJECTED_TYPES / BODY_HIDE_PATTERNS 等 ——
#           改它们等于改判定逻辑,该走 PR 人审,不该藏在某人本地的 yaml 里
TUNABLE = {
    "UA":                                  "抓取用的 User-Agent(真实浏览器 UA;Cloudflare 拦伪装爬虫 UA)",
    "REQUEST_TIMEOUT":                     "单请求超时(秒)",
    "FETCH_SLEEP":                         "单个 worker 两次请求的间隔(秒);整体 QPS ≈ 并发 / 间隔",
    "FETCH_CONCURRENCY":                   "并发抓取线程数;1 = 顺序执行。打开前须重做并发对拍",
    "PAGE_SAMPLE_SIZE":                    "页级检查覆盖:0 = sitemap 全量,>0 = 抽样上限",
    "THROTTLE_RETRIES":                    "单请求遇 429/503 的重试次数(指数退避)",
    "THROTTLE_BACKOFF":                    "首次退避秒数,之后翻倍",
    "THROTTLE_MAX_SLEEP":                  "自适应叠加到每请求间隔上的上限(秒)",
    "THROTTLE_RECOVER_AFTER":              "连续成功多少次回落一档(AIMD 的加性恢复)",
    "SITEMAP_NEWEST_LASTMOD_MAX_AGE_DAYS": "C2:全站最新 lastmod 距今超此值 = sitemap 失养",
    "SITEMAP_URL_SAMPLE_SIZE":             "C2:条目可达性抽查数",
    "SITEMAP_LASTMOD_CLUSTER_RATIO":       "C2:单日 lastmod 簇占比超此值且为当天 = 疑似构建戳",
    "LANG_REDIRECT_SAMPLE_SIZE":           "C26:自动语言重定向的抽样页数",
    "CRAWL_MAX_PAGES":                     "C6:站内爬取上限(防失控);触顶则覆盖不完整,记 N.A.",
    "SSR_TEXT_RATIO":                      "C9:禁 JS 文本 / 渲染版文本 下限(接 headless 后启用)",
    "SSR_MIN_TEXT_CHARS":                  "C9:禁 JS 抓取正文低于此值 = 疑似 CSR 空壳",
    "CACHE_DIFF_SAMPLE_SIZE":              "C10:同 URL 双抓 diff 的抽查页数",
    "TITLE_MAX_CHARS":                     "C11:title 长度上限",
    "DESC_MAX_CHARS":                      "C11:description 长度上限",
    "MIN_CONTENT_CHARS":                   "C13:正文字数下限(thin content)",
    "RETIRED_SAMPLE_SIZE":                 "C20:退役 URL 抽查数",
    "OG_IMAGE_WIDTH":                      "C19:og:image 建议宽",
    "OG_IMAGE_HEIGHT":                     "C19:og:image 建议高",
    "MAX_REDIRECT_HOPS":                   "C3:归一跳数上限(一跳到位才不掉权重)",
    "DOC_BASE_URL":                        "报告「说明」列的链接基址;换 main 为 commit SHA 可钉住版本",
    "EVIDENCE_MAX_CHARS":                  "报告里单格证据的字符上限;完整证据始终进 checks.db",
}


def render_example():
    """按 TUNABLE 与**当前默认值**渲染 config.example.yaml 的内容。

    示例文件是生成物,不是手写的 —— 手写的示例迟早跟代码对不上,而一份说着
    旧默认值的模板比没有模板更坏。`run.py --verify-only` 会拿它跟这里比对,
    对不上就以 1 退出(CI 会跑)。改了默认值就重新生成:
        python3 scripts/config.py --write-example
    """
    lines = [
        "# seo-ops 可调参数 —— 复制到 <config_dir>/config.yaml 后按需改。",
        "#   默认位置:${XDG_CONFIG_HOME:-~/.config}/seo-ops/config.yaml",
        "#   mkdir -p ~/.config/seo-ops && cp references/config.example.yaml ~/.config/seo-ops/config.yaml",
        "#",
        "# 下面每一行都是**当前默认值**,原样保留即等同不配置。只改你要改的那几行,",
        "# 其余留着或删掉都行 —— 没写的项走默认。",
        "#",
        "# 机密不进本文件:CRUX_API_KEY / INDEXNOW_KEYS 住同目录的 .env。",
        "# 未登记的键会被拒绝(拼错的键名不会被静默忽略)。",
        "",
    ]
    for name, why in TUNABLE.items():
        v = globals()[name]
        lines.append(f"# {why}")
        lines.append(f"{name}: {json.dumps(v, ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines)


def load_overrides(path=None):
    """读 <config_dir>/config.yaml 覆盖默认值。

    **未知键与类型不符一律报错退出**,不静默忽略 —— 这是个验收工具,
    「我明明调了阈值」却因为拼错键名而按默认值出报告,比直接报错危险得多。
    """
    f = path or (config_dir() / "config.yaml")
    if not f.exists():
        return
    import yaml
    data = yaml.safe_load(f.read_text()) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{f}:顶层应是 key: value 映射,读到 {type(data).__name__}")
    for k, v in data.items():
        if k not in TUNABLE:
            raise SystemExit(
                f"{f}:不认识的配置项 {k!r}。可用项见 references/config.example.yaml;"
                f"机密请放同目录的 .env。")
        want = type(globals()[k])
        # bool 是 int 的子类,别让 true 悄悄变成 1
        if isinstance(v, bool) != (want is bool) or not isinstance(v, (want, int) if want is float else want):
            raise SystemExit(f"{f}:{k} 应为 {want.__name__},读到 {type(v).__name__}({v!r})")
        globals()[k] = want(v) if want is float else v


load_overrides()


if __name__ == "__main__":
    import sys
    if "--write-example" in sys.argv:
        out = Path(__file__).resolve().parents[1] / "references" / "config.example.yaml"
        out.write_text(render_example())
        print(f"✅ 已重新生成 {out}")
    else:
        sys.exit("用法:python3 scripts/config.py --write-example")
