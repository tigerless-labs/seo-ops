---
name: seo-ops
description: SEO 基础工程的结构检查清单(C 集,26 条)。当需要审查或验收一个网站/页面的 SEO/GEO 结构合规——robots、sitemap、canonical、归一 301、JSON-LD、OG、hreflang、CWV、AI 爬虫放行、渲染策略——或要判断某个前端改动会不会影响收录与被引用时使用。也用于回答「这条检查到底要什么」「为什么要有它」。
---

# seo-ops · SEO 基础工程结构检查

## 这个 skill 干什么

对照 **C 集(26 条结构检查)** 审代码与页面产出:模板、meta、结构化数据、robots/sitemap、
路由与渲染策略。用于 code review、上线前自查、以及解释某条要求的依据。

**判定是二元的结构问题**(该有的结构在不在、对不对),不是效果问题(排名高不高)。

**不在这里的**:跑机器验收的 checker 脚本。它需要联网抓取 + 站点配置,住在
[seo-ops 仓库](https://github.com/tigerless-labs/seo-ops)。要一份可提交的验收报告,
clone 那个仓库跑 `checker/run.py`;本 skill 只做人/agent 侧的对照审查。

**不查**:样式、交互、体验、代码质量;内容真伪与质量;排名与流量。
**清单全绿 ≠ 全部合规。**

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
  是人闸不是机器检查。动内容策略、链接、结构化数据之前先看仓库里的 `redlines.md`。

## 与 content 团队的分工

C 集里有一部分判定输入**只有写内容的人写得出来**(图片 alt 文案、llms.txt 摘要、
ymyl 判定、作者资质)。那部分单列为 **T 集**,住 [content/content-checklist.md](content/content-checklist.md)。

**C 项红了,顺着它的「下游」反查对应的 T** —— 立刻能分清是 content 欠供还是 frontend 没落,
不用两边猜。给 content 团队开交付单用 `seo-content` skill。

---

`checklist/` 与 `content/` 是仓库正本的副本,由 `skills/sync.py` 生成。**不要在这里改**,
要改去 [seo-ops 仓库](https://github.com/tigerless-labs/seo-ops) 改正本。
