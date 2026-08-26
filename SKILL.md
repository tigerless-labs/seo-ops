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

| 用户给了 | 走哪条 | 照哪一节做 |
|---|---|---|
| 域名 / URL | 跑 checker 出报告 | 「**跑 checker**」→ 完了看「**读报告**」 |
| 代码、模板、PR、页面文件 | 不跑脚本,对照 C 集逐条审机器可读产出面 | 「**覆盖范围**」定边界,条目读 `references/checklist/checklist.md` |

目的确认之后就**不要再反复请示**。其余去处:
用户问某条检查为什么/怎么改 → 「**报告出来之后**」;
要不要建配置、建哪个 → 「**配置**」;
依赖装不上 → 「**环境**」。

两条路径都**以 [references/checklist/checklist.md](references/checklist/checklist.md) 为准**,
不凭印象判;某条不确定就读 `references/checklist/references/C<N>.md`。
引用条目写编号(`C12`),编号是永久 ID,不要改号或重排。

### 报告出来之后

**报告本身就是结论,不用主动逐条讲解。** 每行带一列 **说明**,是该条正本的 GitHub 链接
—— 那是给**读报告的人**点的(报告发到哪都打得开)。**你自己要读的是本地那份**:
`references/checklist/references/C<N>.md`。

**用户问到哪一条,先读 `references/checklist/references/C<N>.md` 再答**
(如问 C12 就读 `references/checklist/references/C12.md`):「为什么是问题」取自 `## 介绍`,
「怎么改」取自 `## 实现指导`。**不要凭证据推断作答** —— 证据只说明哪几页不合格,
说不出这条为什么存在、正解是什么、权威依据在哪。

### 环境

```bash
python3 -c "import requests, yaml" || pip install -r scripts/requirements.txt
```

报 `externally-managed-environment`(PEP 668,Debian/Ubuntu 常见)时用系统包
`apt install python3-requests python3-yaml` 或建 venv —— **不要加 `--break-system-packages`**,
那是拿系统 Python 冒险换一个两行的依赖。

## 覆盖范围

**SEO 基础工程** = 让搜索引擎和 AI 检索能**抓到、读懂、收录、引用**一个网站所必需的机器可读结构。

**查什么**:最终 HTTP/HTML 产出的机器可读面——谁产出的不管(后端模板、前端代码、
第三方脚本),只要爬虫看得见就被覆盖。分界线是「机器可读面 / 人可感面」,不是前端/后端。

**不查**:样式、交互、体验、代码质量;内容真伪与质量;排名与流量;流程。
**清单全绿 ≠ 全部合规。**

**人闸另有一套**:R1–R8 禁止事项(买链接、cloaking、假结构化数据、PII 进 prompt 等)住
[redlines.md](redlines.md),机器不查。动内容策略、链接、结构化数据之前先看。

## 这里有什么

| 路径 | 是什么 |
|---|---|
| [references/checklist/checklist.md](references/checklist/checklist.md) | **C 集**索引:26 条,分站级 / 每收录页 / 条件项 |
| `references/checklist/references/C<N>.md` | 每条 C 的正本:`## 介绍`(为什么)+ `## 实现指导`(怎么改)+ 权威依据 |
| `references/content/` | **T 集**:C 红了反查「是谁欠供」用,不在本 skill 的职责内 |
| `scripts/run.py` · `scripts/config.py` | 判定逻辑 / 判定参数 |
| `references/ai-crawlers.yaml` | C1 的 AI 爬虫 UA 清单,运行期读取 |
| `references/{sites,config}.example.yaml` · `references/.env.example` | 三份配置模板,见「**配置**」 |

`<N>` 与清单里的 ID 一一对应,C12 的正本就是 `references/checklist/references/C12.md`;
编号有断档是正常的(退役的号不回收)。

**skill 目录只读,零写入** —— 更新时整包覆盖,写进去的必丢。

## 跑 checker

**确认目标是 origin → 一次问完必要配置(见「配置」)→ 直接跑。**
先跑起来,别为可选项停下 —— 三份配置全都不是必需的。

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

### 多站:一次跑一批站

「多站」= 你手上有几个域名要同时验收(如 `tigerless.com` + `tigerless.ai` + `blog.tigerless.com`),
不想每次手敲 `--target`,也想让每个站各带自己的渲染策略与必测页。建好 `sites.yaml`(见「配置」)后:

```bash
python3 scripts/run.py               # 跑花名册里全部站
python3 scripts/run.py --site <id>   # 只跑其中一个
```

每条记录填:`id`(报告文件名与 `checks` 表的 site 列用它)、`production`(origin,必填)、
`rendering`(ssr/ssg/isr,C15 按此分支)、`sitemap`(默认 `<production>/sitemap.xml`)、
`samples`(sitemap 之外额外加抓的必测页,标 `ymyl: true` 触发 C21 人审)。
找不到花名册时脚本会直接退出并打出该建在哪,不静默跑空。

### 通用参数

临时覆盖:`--page-sample N` `--sitemap-sample N` `--max-pages N` `--sleep S` `--workers N`。
落点覆盖:`--state-dir <path>` / `--out <path>`。
`--verify-only`:只跑两道漂移守卫,不联网,有漂移以 1 退出(CI 用)。

耗时:默认单线程 1 秒间隔,约 `2 × sitemap 条目数` 个请求。271 页的站约 7 分钟
(**跑之前告诉用户大概要等多久**);想快用 `--page-sample 100` 抽样 ——
结构问题是模板级的,抽样和全量看到的是同一批。

## 读报告

每次跑落两份到 `~/Documents/seo-ops/out/`(`--state-dir` / `--out` / `$SEO_OPS_DIR` 可改):

| 产出 | 给谁 | 是什么 |
|---|---|---|
| `report-<site>-<date>.md` | 人读 | 结构与 checklist 一一对应,每次都是同样 26 行 |
| `checks.db` | 机读 | SQLite,`checks(site, url, rule_id, status, evidence, checked_at)`,主键 `(site,url,rule_id)`;跨次累积可 diff |

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

**三份都不是必需的**,住 `~/.config/seo-ops/`(`$SEO_OPS_CONFIG_DIR` 可改),
照模板复制即可 —— **不要改 `scripts/config.py`**,那是 skill 本体,更新时整包覆盖。

```bash
mkdir -p ~/.config/seo-ops
```

| 文件 | 什么时候才需要 | 不建的后果 | 怎么建 |
|---|---|---|---|
| `sites.yaml` | 多站,或要声明渲染策略 / 标 YMYL 页 | 单站用 `--target` 照跑;C15 记 `need-declaration`、C21 无人审清单 | `cp references/sites.example.yaml ~/.config/seo-ops/sites.yaml` |
| `.env` | **只在用户要「完整判定」时**(CrUX / IndexNow key) | **非必需**;C4 记 `need-crux-key`、C5 记 `need-key-declaration`,其余照跑 | `cp references/.env.example ~/.config/seo-ops/.env` |
| `config.yaml` | 只在要改阈值时 | 无,全走默认 | `cp references/config.example.yaml ~/.config/seo-ops/config.yaml` |

`.env` 是隐藏文件,`ls` 不带 `-a` 会看着像空目录。
**已 export 的环境变量永远赢过 `.env`** —— CI 注入 key 不会被谁的本地文件盖掉。
旧位置(`<state-dir>/sites.yaml`、`<state-dir>/.env`、`scripts/.env`)仍能读,
但真取到值时会打告警提醒搬走 —— 静默的错位配置会让同一条命令给出不同结论。

### config.yaml 能调什么

模板里每一行都是**当前默认值**,原样保留即等同不配置;只改要改的几行。常调的:

| 参数 | 作用 |
|---|---|
| `FETCH_SLEEP` / `FETCH_CONCURRENCY` | 抓取节流;整体 QPS ≈ 并发 / 间隔。默认 1 / 1 |
| `PAGE_SAMPLE_SIZE` | 页级检查覆盖:`0` = 全量,`>0` = 抽样上限 |
| `CRAWL_MAX_PAGES` | 站内爬取上限(C6) |
| `TITLE_MAX_CHARS` / `DESC_MAX_CHARS` | C11 长度线 |
| `THROTTLE_*` | 限流退避与恢复 |
| `DOC_BASE_URL` | 报告「说明」列的链接基址;换成 commit SHA 可钉住版本 |

**未登记的键与类型不符一律报错退出**,不静默忽略 —— 拼错键名却按默认值出报告,比报错危险。

**三类不能在这里调**:**机密**(住 `.env`)、**常量**(CWV 三阈值是 Google 官方 good 线、
sitemap 5 万条是协议硬上限、viewport token 是规范值 —— 调了就不是这条检查了)、
**结构化判定**(`TYPE_REQUIRED`、`LD_REJECTED_TYPES`、`BODY_HIDE_PATTERNS` ——
改它们等于改判定逻辑,该走 PR 人审,不该藏在某人本地的 yaml 里)。
