---
name: seo-content
description: 检查内容设计文档(页面 doc)有没有交齐 SEO 所需的供给项 —— T 集。当 content / 设计团队在写或评审一份页面 doc、内容设计稿、栏目规划,需要确认 title/description、H1/H2 大纲、图片 alt 文案、ymyl 判定、OG 分享文案、双语配对、作者资质等是否齐备且合格时使用。也用于给一份 doc 补「SEO 头部块」。
---

# seo-content · 内容设计文档的 SEO 供给检查

## 这个 skill 干什么

拿一份**页面 doc / 内容设计文档**,对照 **T 集** 逐条查:SEO 需要的信息,content 侧交齐了没有、
交得合不合格。缺什么就指出来,并告诉写作者**这条要怎么交**。

**定位 = 补集。** 常规页面 doc(按 layout 分段写文案)、layout 设计、URL 照旧交付,
本 skill 不重复审那些。只管**常规 doc 通常不覆盖的 SEO 供给项** —— 它们该作为一个
「SEO 头部块」补在每页 doc 顶部。

**不干什么**:不判内容写得好不好、不改文案风格、不做关键词研究、不查页面上线后的实际产出
(那是 `seo-ops` skill 与 checker 的事)。

## 怎么用

1. 读 [content/content-checklist.md](content/content-checklist.md) —— T 集索引,分三节:
   - **站级**(T1–T2):一次性供给 + 低频维护,不是每页都要
   - **每页必交**(T3–T10、T14):页面 doc 顶部的「SEO 头部块」
   - **条件项**(T12–T13):按 flag 或页面内容触发,不触发就不要求
2. 对着手上的 doc 逐条核。每条的详细说明住 `content/references/T<N>.md`
   (介绍 + 怎么交 + 常见错误)—— **指出缺失时把「怎么交」一起给出**,不要只说「缺 T5」。
3. 输出按这个形状给:

   | T | 供给项 | 状态 | 说明 |
   |---|---|---|---|
   | T5 | title / description | 🔴 缺 | desc 未写;title 68 字超了 60 上限,需压缩 |
   | T4 | ymyl 判定 | ✅ | 标了 false,内容不涉健康/财务/法律,判定合理 |
   | T12 | 作者资质 | ⚪ N.A. | ymyl=false,本条不触发 |

   **三态照实记**:不触发的条件项记 N.A. 并写明为什么不触发,别记成 pass;
   看不到的东西记 N.A.,别猜一个绿。

## 判定要点(最常出错的几条)

- **T4 `ymyl` 判定是条件项的唯一开关** —— 内容影响读者健康 / 财务 / 法律 / 人身安全即 `true`。
  **拿不准标 `true`**。漏标 = 下游 C21 整条静默失效,没有任何地方会报警。
- **T14 图片 alt** —— 内容图逐张一句描述(讲图里是什么,**不堆关键词**);
  纯装饰图标注「装饰」,由前端落成 `alt=""`。
- **T5 title / description** —— title ≤60、desc ≤150,**每页唯一不复制**。
  站级有公式的按公式,但不能几页共用一句。
- **T8 双语** —— en/zh 同交不留单边;确实只有一种语言的,**显式声明** en only / zh only,
  不要留空(留空和「还没写」分不开)。
- **T12 审核必须真实发生** —— ymyl 内容的审核人与审核日期不是走过场的字段,
  假署名踩红线 R2。审核流程归 content 管理团队,本 skill 只查有没有交。

## 硬约束

- **T 号是永久 ID**,只顺延、不回收、不重排。编号有断档正常(如 T11 已退役)。
- **每条 T 都标注了下游 C 项** —— 这是「责任可回溯」的实现:C 红了能反查到 T,
  分清是 content 欠供还是 frontend 没落。引用时保留编号对应关系,别改。
- **有些 SEO 项不该找 content 要** —— sitemap 分片、canonical header、viewport、
  `og:type` 取值等,判定输入全在 frontend 侧。content-checklist 文末列了这些「判过但不加 T 的」
  及理由,**被要求补这类东西时指出来**,别照单全收。

---

`content/` 与 `checklist/` 是仓库正本的副本,由 `skills/sync.py` 生成。**不要在这里改**,
要改去 [seo-ops 仓库](https://github.com/tigerless-labs/seo-ops) 改正本。
