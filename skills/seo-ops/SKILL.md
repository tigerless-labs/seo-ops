---
name: seo-ops
description: SEO 基础工程的结构检查清单(C 集,26 条)与 checker 脚本。当需要审查或验收一个网站/页面的 SEO/GEO 结构合规——robots、sitemap、canonical、归一 301、JSON-LD、OG、hreflang、CWV、AI 爬虫放行、渲染策略——要跑机器检查出一份报告,或要判断某个前端改动会不会影响收录与被引用时使用。也用于回答「这条检查到底要什么」「为什么要有它」。
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/checker/run.py *)
compatibility: Requires Python 3.9+, requests, PyYAML, and network access to the target site
---

# seo-ops · SEO 基础工程结构检查

## 这个 skill 干什么

对照 **C 集(26 条结构检查)** 审代码与页面产出:模板、meta、结构化数据、robots/sitemap、
路由与渲染策略。用于 code review、上线前自查、以及解释某条要求的依据。

**判定是二元的结构问题**(该有的结构在不在、对不对),不是效果问题(排名高不高)。

两种用法:**对照清单审代码**(不联网),或**跑 checker 出报告**(联网抓目标站)。

**不查**:样式、交互、体验、代码质量;内容真伪与质量;排名与流量。
**清单全绿 ≠ 全部合规。**

## 跑 checker

`<skill>` = 本 SKILL.md 所在目录的绝对路径。

```bash
pip install -r <skill>/checker/requirements.txt      # 首次;只要 requests 和 PyYAML
python3 <skill>/checker/run.py --target https://example.com
```

**不要往 skill 目录里写任何东西** —— skill 更新是整包覆盖,写进去的必丢。
脚本自己也不写:产出与机密各有固定去处,与 skill 装在哪、你在哪个目录跑都无关。

```
~/Documents/seo-ops/          # 产出与花名册($SEO_OPS_DIR 或 --state-dir 可改)
├── sites.yaml                #   多站花名册;单站用 --target,不需要本文件
└── out/
    ├── report-<site>-<date>.md    # 人读,与 checklist 一一对应,每次都是同样 26 行
    └── checks.db                  # 机读,SQLite,跨次累积可做 diff

~/.config/seo-ops/            # 机密($SEO_OPS_CONFIG_DIR 可改)
└── .env                      #   CRUX_API_KEY / INDEXNOW_KEYS;已 export 的环境变量优先
```

**机密单独放**是因为 `~/Documents` 常被 iCloud / OneDrive / Dropbox 同步、被备份、
被整个文件夹分享出去 —— 报告该待在人找得到的地方,key 不该跟着走。

报告放 Documents 而不是当前项目里,也是有意的:`sites.yaml` 是一份**站点**花名册、
`checks.db` 是**站点**的历史,它们属于「你负责哪些站」,不属于「你此刻在哪个仓库里」。
同一批站从三个仓库验收,不该得到三份割裂的历史。

`checks(site, url, rule_id, status, evidence, checked_at)`,主键 `(site, url, rule_id)`。

### 常用参数

| | |
|---|---|
| `--target <origin>` | 单站,不需要配置文件。**必须是 origin**(scheme + host[:port]),带 path/query 会报错退出 |
| `--site <id>` / 不传 | 按 `<state-dir>/sites.yaml` 跑其中一个 / 全部 |
| `--page-sample N` | 页级检查抽样上限;`0` = 全量。271 页的站全量约 7 分钟,想快用 `--page-sample 100` |
| `--sleep S` / `--workers N` | 节流。整体 QPS ≈ workers / sleep,默认 1 / 1 |
| `--state-dir <path>` | 花名册与产出目录,默认 `~/Documents/seo-ops`;也可用 `$SEO_OPS_DIR` |

**先看报告顶部的告警行**,有就说明这次结论不完整:🚦 被目标限流(429/503)= 我们打太快,
受影响的判定已记 N.A. 不记 fail,**假红比跑得慢危险** —— `--workers` 减半或调大 `--sleep`
重跑才有完整结论;⚠️ 样本抓取失败 = 真抓不到,这些页不进分母。

**公网 staging 域不支持** —— 会被当生产域测,归一检查(C3)必然误红。
上线前要测:本地部署跑 `http://localhost:<port>`,或等上线后跑生产域。

## 怎么用

1. 先读 [checklist/checklist.md](checklist/checklist.md) —— 26 条的索引,含优先级与所属节。
2. 定位相关条目,读它的详细说明 `checklist/references/C<N>.md`(判定标准、常见错法、权威依据)。
3. 按**优先级**给结论,不按红项数量:
   - **P0 = 存在层/事故层** —— 爬不到、收不进。先修这些。
   - **P1 = 表现层** —— 排名与引用打折。
   - **P2 = 优化项**。
4. 报结论用三态:**pass / fail / N.A.(原因)**。
   **「没测」不许说成「没事」** —— 看不到线上产出、拿不到配置、需要人工判断的,
   一律记 N.A. 并写明原因,不要猜一个绿。

## 硬约束

- **条目编号是永久 ID**,报告与 `checks` 表按它索引。引用时写 `C12` 这样的编号,
  不要改号、不要重排、不要把退役的号回收。编号有断档是正常的。
- **C21 / C22 是人审项** —— 脚本不判,agent 也不要替人下结论,列出来提醒人过。
- **YMYL 内容**(影响健康 / 财务 / 法律 / 人身安全)触发 C21;**拿不准按 YMYL 处理**。
- **红线另有一套**:R1–R8 是禁止事项(买链接、cloaking、假结构化数据、PII 进 prompt 等),
  是人闸不是机器检查。动内容策略、链接、结构化数据之前先看 [redlines.md](redlines.md)。

## 与 content 团队的分工

C 集里有一部分判定输入**只有写内容的人写得出来**(图片 alt 文案、llms.txt 摘要、
ymyl 判定、作者资质)。那部分单列为 **T 集**,住 [content/content-checklist.md](content/content-checklist.md)。

**C 项红了,顺着它的「下游」反查对应的 T** —— 立刻能分清是 content 欠供还是 frontend 没落,
不用两边猜。给 content 团队开交付单用 `seo-content` skill。

---

`checklist/`、`content/`、`checker/` 都是仓库正本的副本,由 `skills/sync.py` 生成。
**不要在这里改**,要改去 [seo-ops 仓库](https://github.com/tigerless-labs/seo-ops) 改正本
—— 改在这里的东西下次更新 skill 就没了。
