---
name: seo-ops
description: SEO 基础工程的检查清单与 checker 脚本。当需要检查或验收一个网站的 SEO/GEO 结构合规(robots、sitemap、canonical、JSON-LD、OG、hreflang、CWV、AI 爬虫放行等),或需要知道 content 团队该为 SEO 提供哪些信息时使用。跑 checker 出报告、查某条检查的详细要求、定 content 供给清单,都走这里。
---

# seo-ops · SEO 基础工程

## 覆盖范围

**SEO 基础工程** = 让搜索引擎和 AI 检索能**抓到、读懂、收录、引用**一个网站所必需的机器可读结构。

它是地基,不是增长手段。做好了不保证排名,但做不好上面盖什么都没用——爬虫抓不到的页面,
内容再好也不存在。所以它的判定是**二元的结构问题**(该有的结构在不在、对不对),
不是效果问题(排名高不高、流量多不多)。

**查什么**:最终 HTTP/HTML 产出的机器可读面——谁产出的不管(后端模板、前端代码、
第三方脚本),只要爬虫看得见就被覆盖。分界线是「机器可读面 / 人可感面」,不是前端/后端。

**不查**:样式、交互、体验、代码质量;内容真伪与质量;排名与流量;流程。
**清单全绿 ≠ 全部合规。**

## 包里有什么

路径都相对包根:

| 路径 | 是什么 | 什么时候读 |
|---|---|---|
| [checklist/checklist.md](checklist/checklist.md) | **C 集**:26 条结构检查,分站级 / 每收录页 / 条件项 | 要知道查哪些项、优先级多少 |
| `checklist/references/C<N>.md` | 每条 C 的详细说明:判定标准、常见错法、权威依据 | 某条 C 红了、或要给工程解释「到底要什么」 |
| [content/content-checklist.md](content/content-checklist.md) | **T 集**:SEO 所需信息的供给清单,每条标注它喂的下游 C 项 | 要给 content / 设计团队开交付单 |
| `content/references/T<N>.md` | 每条 T 的详细说明:要交什么、什么样算合格 | 具体写某条素材时 |
| [checker/run.py](checker/run.py) | 跑 C 集机器项,出报告 | 验收时 |
| [redlines.md](redlines.md) | **R 集**:R1–R8 禁止事项(人闸,不是机器检查) | 动内容策略、动链接、动结构化数据之前 |
| [ai-crawlers.yaml](ai-crawlers.yaml) | C1 检查的 AI 爬虫 UA 清单 | 要增删被检查的 AI 爬虫时 |

`<N>` 是条目编号,与清单里的 ID 一一对应:C12 的详情就是 `checklist/references/C12.md`。
编号有断档是正常的(如无 T11)——退役的号不回收,详见「改清单的时候」。

## 跑 checker

```bash
pip install -r checker/requirements.txt
```

**一个「站」= 一个 origin**(scheme + host[:port],不带 path/query)。子域名算独立的站
(`blog.` / `docs.` 各算一个);裸域与 www 不算两个 —— 它们该归一到同一个 canonical host,
这正是 C3 要检的,所以只认你选定的那一个。

### 单站:不需要任何配置文件

```bash
python3 checker/run.py --target https://example.com      # 线上站
python3 checker/run.py --target http://localhost:3000    # 本地部署,自动判定为本地模式
```

`--target` 必须是 origin,传带 path/query 的 URL 会直接报错退出,不猜。

**公网 staging 域不支持** —— 会被当生产域测,归一检查(C3)必然误红。
要在上线前测,二选一:本地部署跑 `http://localhost:<port>`,或等上线后跑生产域。

### 多站:一次跑一批站,先建一份站点花名册

「多站」= 你手上有几个域名要同时验收(如 `tigerless.com` + `tigerless.ai` + `blog.tigerless.com`),
不想每次手敲 `--target`,也想让每个站各带自己的渲染策略与必测页。这时才需要 `sites.yaml`:

```bash
cp sites.example.yaml sites.yaml     # 照抄改成自己的站,一个站一条记录
python3 checker/run.py               # 跑花名册里全部站
python3 checker/run.py --site <id>   # 只跑其中一个
```

每条记录填:`id`(报告文件名与 `checks` 表的 site 列用它)、`production`(origin,必填)、
`rendering`(ssr/ssg/isr,C15 按此分支)、`sitemap`(默认 `<production>/sitemap.xml`)、
`samples`(sitemap 之外额外加抓的必测页,标 `ymyl: true` 触发 C21 人审)。
字段说明见 [sites.example.yaml](sites.example.yaml) 的注释。

`sites.yaml` 在 `.gitignore` 里 —— 它是各人各机器的配置,只有 example 模板进版本库。

### 通用参数

临时覆盖:`--page-sample N` `--sitemap-sample N` `--max-pages N` `--sleep S`。

耗时:默认单线程 1 秒间隔,约 `2 × sitemap 条目数` 个请求。271 页的站约 7 分钟;
想快用 `--page-sample 100` 抽样——结构问题是模板级的,抽样和全量看到的是同一批。

## 读报告

每次跑落两份产出到 `checker/out/`:

| 产出 | 给谁 | 是什么 |
|---|---|---|
| `report-<site>-<date>.md` | 人读 | 结构与 checklist 一一对应,每次都是同样 26 行 |
| `checks.db` | 机读 | SQLite,表 `checks(site, url, rule_id, status, evidence, checked_at)`,主键 `(site,url,rule_id)`;跨次累积,可做两次跑之间的 diff |

| 结果 | 含义 |
|---|---|
| ✅ pass | 测了,通过 |
| 🔴 fail | 测了,没通过——证据列给出违规页与原因 |
| ⚪ N.A. | **没测**,括号里是原因码。**「没测」不是「没事」** |
| 👤 人审 | 脚本不判,列出来提醒人过 |

常见 N.A. 原因码:`need-domain`(本地模式)、`need-crux-key` / `need-crux-data`(C4)、
`need-key-declaration`(C5)、`need-declaration`(未声明渲染策略)、`no-pages`、
`crawl-capped`(爬取触上限)、`throttled`(被目标限流,降速重跑)。

**先看报告顶部的告警行**,有就说明这次结论不完整:

- 🚦 **被目标限流**(429/503)—— 是我们打太快,不是站点有问题。受影响的判定已记 N.A.
  不记 fail(**假红比跑得慢危险**)。想要完整结论:`--workers` 减半或调大 `--sleep` 重跑。
- ⚠️ **样本抓取失败**(非限流)—— 真的抓不到,这些页不进分母。

优先级:**P0 = 存在层/事故层**(爬不到、收不进);**P1 = 表现层**(排名与引用打折);**P2 = 优化项**。

## 配置

判定参数全在 [checker/config.py](checker/config.py),按 C 号分组。改阈值只动这里,判定逻辑住 `run.py`。

常调的:

| 参数 | 作用 |
|---|---|
| `FETCH_SLEEP` / `FETCH_CONCURRENCY` | 抓取节流;整体 QPS ≈ 并发 / 间隔。默认 1 / 1 |
| `PAGE_SAMPLE_SIZE` | 页级检查覆盖:`0` = 全量,`>0` = 抽样上限 |
| `CRAWL_MAX_PAGES` | 内链图爬取上限(C6) |
| `TITLE_MAX_CHARS` / `DESC_MAX_CHARS` | C11 长度线 |
| `TYPE_REQUIRED` | C12 各 JSON-LD 类型的必填字段 |
| `LD_REJECTED_TYPES` | C12 负向扫描:不采纳的类型及理由 |
| `BODY_HIDE_PATTERNS` | C14 第三方脚本黑名单(新工具在此追加) |
| `ai-crawlers.yaml` | C1 检查的 AI 爬虫 UA 清单 |

**机密不进 config.py**:`CRUX_API_KEY`(C4)与 `INDEXNOW_KEYS`(C5)住 `checker/.env`,
模板见 `checker/.env.example`。不填就相应条目记 N.A.,不判红。

## 改清单的时候

**checklist 与脚本是两份,各自维护**——检查逻辑没法从表格自动生成。但条目集合可以对齐:
每次启动会跑 `verify_checklist_sync()`,「有哪些条目、什么优先级、在哪一节」对不上就在 stdout 打 ⚠️。

**加条目的顺序:先改 checklist.md,再改 run.py 的 `CHECKS` 和判定逻辑。**
编号是永久 ID,只顺延、不回收、不重排。
