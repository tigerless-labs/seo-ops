# 义务:红线与流程(SEO Conformance)

> 分工:**checklist 管「查什么」**(C 集结构检查,机器执行);**本篇管「禁什么」**(红线,
> 人闸把守);流程类判定(如新增 URL 走评审)由使用方自定,不在本包。编号共用一套,永不重排。

## 红线 R1–R8(禁止事项)

| ID | 红线 | 依据 |
|---|---|---|
| R1 | agent 不直接改生产,一切变更走 PR + 人审 |  |
| R2 | YMYL 内容(保险/医疗/金融)未过**公司专业部门审核**不得发布;署名如实(审核流程归 content 管理团队) | YMYL/E-E-A-T |
| R3 | 无真数据支撑的批量生成页(thin content) | scaled content abuse |
| R4 | 同一内容多域发布且无 canonical 归属 |  |
| R5 | 虚假结构化数据(假评分/假 FAQ)、买评价/自造评分 | 人工处罚 |
| R6 | 买链接、链接农场、任何 link scheme 参与 | Penguin/人工处罚 |
| R7 | Cloaking:给爬虫与用户提供不同内容(缓存公共壳 + 客户端补个性化不算;按 UA 特供内容才算);隐藏文本、keyword 堆砌同列 | Google spam 政策,除名级 |
| R8 | 用户级数据(PII)进入 store、harness、prompt 或任何第三方 API(含 LLM 调用) | 隐私;GA4 只取聚合 |

## 权威依据(官方文档,R 集)

> C 集的权威依据随清单住 [checklist/checklist.md](checklist/checklist.md)。

| 规则 | 依据 |
|---|---|
| R3(scaled content)/ R6(link spam)/ R7(cloaking、隐藏文本、堆砌) | [Google Spam Policies](https://developers.google.com/search/docs/essentials/spam-policies) — 每条红线在此有明文对应 |
| R5(虚假结构化数据、买评价) | [Google Structured Data 政策](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) |
| R2 背后的 YMYL/E-E-A-T | [Google Search Quality Rater Guidelines](https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf)(评估员手册,E-E-A-T 与 YMYL 的原始定义) |

维护约定:链接失效或政策更新属 harness 变更,人审后更新本表;R/C 编号永久、只顺延不重排。
