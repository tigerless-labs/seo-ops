---
name: seo-ops
description: SEO 基础工程的结构检查清单与 checker 脚本。当需要审查或验收一个网站/页面的 SEO/GEO 结构合规(robots、sitemap、canonical、归一 301、JSON-LD、OG、hreflang、CWV、AI 爬虫放行、渲染策略),要跑机器检查出一份报告,或要判断某个前端改动会不会影响收录与被引用时使用。也用于回答「这条检查到底要什么」「为什么要有它」。
compatibility: Requires Python 3.9+, requests, PyYAML, and network access to the target site
---

# seo-ops · SEO 基础工程

对照 **C 集**(26 条结构检查)审一个网站的模板与产出,或跑 checker 出一份验收报告。

## 怎么干活

触发本 skill 时,**先花两三句让用户知道他拿到的是什么**,再动手:

> 这里有 26 条 SEO/GEO 结构检查(C 集),查的是爬虫能不能抓到、读懂、收录、引用一个网站
> —— 二元的结构问题,不是排名好不好。可以**对着线上站跑 checker 出一份报告**,
> 也可以**对着代码/模板逐条审**。你要查哪个?

**确认目的再开工**,因为「查线上站」和「查代码」是两件事,猜错就白跑一遍:

| 用户给了 | 走哪条 |
|---|---|
| 域名 / URL | 跑 checker 出报告 |
| 代码、模板、PR、页面文件 | 不跑脚本,对照 C 集逐条审机器可读产出面 |

目的确认之后就**不要再反复请示**,按下面的流程走完。

两条路径都**以 [references/checklist/checklist.md](references/checklist/checklist.md) 为准**,
不凭印象判;某条不确定就读 `references/checklist/references/C<N>.md`。
引用条目写编号(`C12`),编号是永久 ID,不要改号或重排。

### 跑 checker 的流程

**确认目标是 origin → 一次问完必要配置 → 直接跑。** 先跑起来,别为可选项停下:

| | 什么时候才需要 | 没有的后果 |
|---|---|---|
| 目标 origin | 总是 | 跑不了 |
| `sites.yaml` | 多站,或要声明渲染策略 / 标 YMYL 页 | 单站用 `--target`;C15 记 `need-declaration`、C21 无人审清单 |
| `.env` 里的 CrUX key | **只在用户要「完整判定」时** | **非必需**,C4 记 `need-crux-key`,其余 25 条照跑 |
| `config.yaml` | 只在要改阈值时 | 无,全走默认 |

271 页的站约 7 分钟,跑之前告诉用户大概要等多久。

### 报告出来之后

**报告本身就是结论,不用主动逐条讲解。** 每行带一列 **说明**,链到该条的正本
`references/checklist/references/C<N>.md` —— 判定标准、常见错法、权威依据、怎么改都在那篇。

**用户问到哪一条,先读 `references/checklist/references/C<N>.md` 再答**
(如问 C12 就读 `references/checklist/references/C12.md`):「为什么是问题」取自 `## 介绍`,
「怎么改」取自 `## 实现指导`。**不要凭证据推断作答** —— 证据只说明哪几页不合格,
说不出这条为什么存在、正解是什么、权威依据在哪。

### 环境

```bash
python3 -c "import requests, yaml"     # 只要这两个依赖
ls -a ~/.config/seo-ops/               # .env 是隐藏文件,不带 -a 看着像空目录
```

装不上且报 `externally-managed-environment`(PEP 668,Debian/Ubuntu 常见)时用系统包
`apt install python3-requests python3-yaml` 或建 venv —— **不要加 `--break-system-packages`**,
那是拿系统 Python 冒险换一个两行的依赖。

## 覆盖范围

**SEO 基础工程** = 让搜索引擎和 AI 检索能**抓到、读懂、收录、引用**一个网站所必需的机器可读结构。

它是地基,不是增长手段。做好了不保证排名,但做不好上面盖什么都没用——爬虫抓不到的页面,
内容再好也不存在。所以它的判定是**二元的结构问题**(该有的结构在不在、对不对),
不是效果问题(排名高不高、流量多不多)。

**查什么**:最终 HTTP/HTML 产出的机器可读面——谁产出的不管(后端模板、前端代码、
第三方脚本),只要爬虫看得见就被覆盖。分界线是「机器可读面 / 人可感面」,不是前端/后端。

**不查**:样式、交互、体验、代码质量;内容真伪与质量;排名与流量;流程。
**清单全绿 ≠ 全部合规。**

## 这里有什么

skill 本体(只读,更新时整包覆盖 —— **一个字节都别往里写**):

```
<skill>/
├── SKILL.md                     本文件
├── README.md                    给人读的介绍
├── redlines.md                  R 集:R1–R8 禁止事项(人闸,不是机器检查)
├── scripts/
│   ├── run.py                   跑 C 集机器项,出报告
│   ├── config.py                判定参数(按 C 号分组)
│   └── requirements.txt         requests + PyYAML
└── references/
    ├── checklist/
    │   ├── checklist.md         C 集:26 条结构检查,分站级/每收录页/条件项
    │   └── references/C<N>.md   每条 C 的详细说明:判定标准、常见错法、权威依据
    ├── content/                 T 集:C 项红了反查「是谁欠供」用,不在本 skill 的职责内
    │   ├── content-checklist.md
    │   └── references/T<N>.md
    ├── ai-crawlers.yaml         C1 检查的 AI 爬虫 UA 清单(run.py 运行期读取)
    ├── sites.example.yaml       花名册模板,字段说明就在它的注释里
    ├── config.example.yaml      可调参数模板(**生成物**,见「配置」一节)
    └── .env.example             机密模板
```

`<N>` 是条目编号,与清单里的 ID 一一对应:C12 的详情就是
`references/checklist/references/C12.md`。编号有断档是正常的(如无 T11)——
退役的号不回收,详见「改清单的时候」。

## 状态文件都在哪

**skill 目录外,分两处**,按「配置 / 产出」切,不按「敏感 / 不敏感」切:

| 位置 | 装什么 | 谁写的 | 怎么改位置 |
|---|---|---|---|
| `~/.config/seo-ops/sites.yaml` | 站点花名册(多站才需要;单站用 `--target`) | 你 | `$SEO_OPS_CONFIG_DIR` |
| `~/.config/seo-ops/config.yaml` | 可调参数覆盖(不建就全走默认) | 你 | 同上 |
| `~/.config/seo-ops/.env` | `CRUX_API_KEY` / `INDEXNOW_KEYS` | 你 | 同上 |
| `~/Documents/seo-ops/out/report-<site>-<date>.md` | 人读的报告,每次同样 26 行 | 脚本 | `--state-dir` / `--out` / `$SEO_OPS_DIR` |
| `~/Documents/seo-ops/out/checks.db` | 机读快照,跨次累积可 diff | 脚本 | 同上 |

**优先级**:`--state-dir` > `$SEO_OPS_DIR` > `~/Documents/seo-ops`;
配置侧是 `$SEO_OPS_CONFIG_DIR` > `${XDG_CONFIG_HOME:-~/.config}/seo-ops`。
**已 export 的环境变量永远赢过 `.env` 文件** —— CI 注入 key 不会被谁的本地文件盖掉。

**旧位置仍能读**(`<state-dir>/sites.yaml`、`<state-dir>/.env`、`scripts/.env`),
但真从它们取到值时会打告警提醒搬走 —— 静默的错位配置会让同一条命令给出不同结论。

## 跑 checker

```bash
pip install -r scripts/requirements.txt      # 首次;只要 requests 和 PyYAML
python3 scripts/run.py --target https://example.com
```

产出与配置的落点见上一节「状态文件都在哪」。**skill 目录零写入。**

**一个「站」= 一个 origin**(scheme + host[:port],不带 path/query)。子域名算独立的站
(`blog.` / `docs.` 各算一个);裸域与 www 不算两个 —— 它们该归一到同一个 canonical host,
这正是 C3 要检的,所以只认你选定的那一个。

### 单站:不需要任何配置文件

```bash
python3 scripts/run.py --target https://example.com      # 线上站
python3 scripts/run.py --target http://localhost:3000    # 本地部署,自动判定为本地模式
```

`--target` 必须是 origin,传带 path/query 的 URL 会直接报错退出,不猜。

**公网 staging 域不支持** —— 会被当生产域测,归一检查(C3)必然误红。
要在上线前测,二选一:本地部署跑 `http://localhost:<port>`,或等上线后跑生产域。

### 多站:一次跑一批站,先建一份站点花名册

「多站」= 你手上有几个域名要同时验收(如 `tigerless.com` + `tigerless.ai` + `blog.tigerless.com`),
不想每次手敲 `--target`,也想让每个站各带自己的渲染策略与必测页。这时才需要 `sites.yaml`:

```bash
mkdir -p ~/.config/seo-ops && cp references/sites.example.yaml ~/.config/seo-ops/sites.yaml
python3 scripts/run.py               # 跑花名册里全部站
python3 scripts/run.py --site <id>   # 只跑其中一个
```

找不到花名册时脚本会直接退出并把该建在哪、照谁抄打出来,不会静默跑空。

每条记录填:`id`(报告文件名与 `checks` 表的 site 列用它)、`production`(origin,必填)、
`rendering`(ssr/ssg/isr,C15 按此分支)、`sitemap`(默认 `<production>/sitemap.xml`)、
`samples`(sitemap 之外额外加抓的必测页,标 `ymyl: true` 触发 C21 人审)。
字段说明见 [references/sites.example.yaml](references/sites.example.yaml) 的注释。

花名册在 skill 目录外,所以更新(`git pull` 或整包覆盖)时原地不动,也不可能被误提交
—— 版本库里只有 `sites.example.yaml` 模板。

### 通用参数

临时覆盖:`--page-sample N` `--sitemap-sample N` `--max-pages N` `--sleep S` `--workers N`。
位置覆盖:产出用 `--state-dir` / `--out` 或 `$SEO_OPS_DIR`;配置用 `$SEO_OPS_CONFIG_DIR`。

`--verify-only`:只跑两道漂移守卫(清单 vs 脚本、config.example vs 默认值),
不联网,有漂移以 1 退出 —— CI 用的入口。

耗时:默认单线程 1 秒间隔,约 `2 × sitemap 条目数` 个请求。271 页的站约 7 分钟;
想快用 `--page-sample 100` 抽样——结构问题是模板级的,抽样和全量看到的是同一批。

## 读报告

每次跑落两份产出到 `~/Documents/seo-ops/out/`:

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

**调参数不要改 `scripts/config.py`** —— 那是 skill 本体,更新时整包覆盖,改了就没。
建一份自己的:

```bash
mkdir -p ~/.config/seo-ops && cp references/config.example.yaml ~/.config/seo-ops/config.yaml
```

模板里每一行都是**当前默认值**,原样保留即等同不配置;只改要改的几行,其余留着或删掉都行。
不建这个文件就全走默认。

常调的:

| 参数 | 作用 |
|---|---|
| `FETCH_SLEEP` / `FETCH_CONCURRENCY` | 抓取节流;整体 QPS ≈ 并发 / 间隔。默认 1 / 1 |
| `PAGE_SAMPLE_SIZE` | 页级检查覆盖:`0` = 全量,`>0` = 抽样上限 |
| `CRAWL_MAX_PAGES` | 站内爬取上限(C6) |
| `TITLE_MAX_CHARS` / `DESC_MAX_CHARS` | C11 长度线 |
| `THROTTLE_*` | 限流退避与恢复 |

**未登记的键会被拒绝并退出**,不静默忽略 —— 拼错键名却按默认值出报告,比直接报错危险。
类型不符同样报错。

**三类东西不能在这里调**:

- **机密** —— `CRUX_API_KEY`(C4)、`INDEXNOW_KEYS`(C5)住同目录的 `.env`,
  模板见 `references/.env.example`。不填就相应条目记 N.A.,不判红。
- **常量** —— CWV 三个阈值是 Google 官方 good 线、sitemap 5 万条是 sitemaps.org
  协议硬上限、viewport token 是规范值;调了就不是这条检查了。
- **结构化判定** —— `TYPE_REQUIRED`(C12 必填字段)、`LD_REJECTED_TYPES`、
  `BODY_HIDE_PATTERNS`(C14 第三方脚本黑名单)。改它们等于改判定逻辑,
  该走 PR 人审,不该藏在某人本地的 yaml 里。要改就改 `scripts/config.py`。
