# 检查清单(C 集,静态结构检查)

> **定义:全部代码的「机器足迹」检查清单**——检查对象是最终 HTTP/HTML 产出的**机器可读面**,
> 谁产出的不管(后端模板、前端代码、第三方脚本的产出,只要爬虫看得见就被覆盖);
> 分界线是「机器可读面 / 人可感面」,不是前端/后端——样式、交互、体验与代码内部质量不在此列。
> **用途单一:静态结构检查**——只判「该有的结构在不在、对不对」,不判内容质量、不判效果、不含流程。
> checker(手动运行的检查脚本)按一、二节实现(`checks` 表逐项落库);三节为人审项。
> 边界:本清单全绿 ≠ 全部合规——内容真伪/质量类审核归 content 管理团队(YMYL 走专业部门,R2),
> 红线见 conformance,流程判定见 methods;本系统只提供结构位与结构校验。
> 适用范围:**站级**(每站一次)/ **每收录页** / **条件项**(由 flag 或站点配置触发,不由页型触发)。
> 每条目的详细说明各自一篇,住 [references/](references/)(介绍 + 实现指导两段);本表是索引与判定一览。

## 一、站级(每站一次)

| ID | 优先级 | 检查 | 判定 | 执行层 |
|---|---|---|---|---|
| C1 | P0 | robots.txt 放行全部 AI 爬虫 | fetch + 逐 UA 比对 | checker |
| C2 | P0 | sitemap 打得开、条目都活着、更新时间是真的 | fetch + **禁重定向**抽查 + lastmod 覆盖率/离散度/单日簇 + 逐份条目计数 | checker |
| C3 | P0 | 同一个页面只有一个网址(www/裸域、http/https、尾斜杠都归到同一个) | 四变体 curl(**需真实域名;预发/无域名时记 N.A.**) | checker |
| C26 | P0 | 语言版本各有固定网址,不按浏览器语言自动跳 | 抽样页各发一次 en-US / zh-CN,比对 final_url;不一致 = 存在按推测语言的自动跳转 | checker |
| C4 | P1 | 真实用户的加载 / 响应 / 视觉稳定达标(Core Web Vitals) | CrUX API(**需域名且上线后有真实流量(约 28 天);此前记 N.A.**) | checker |
| C5 | P1 | IndexNow 的验证文件放在站根且打得开 | fetch key 文件,200 且内容 == key(**需站点方报 key 登记进 config.INDEXNOW_KEYS;未登记记 N.A.**) | checker |
| C6 | P1 | 页面上的站内链接不指向坏页(404 / 403 / 5xx) | 爬内链图,目标不在 sitemap 里的站内链接状态码 <400;未爬全则记 N.A. | checker |
| C7 | P2 | 站根有 llms.txt —— 给 AI 引擎的站点目录 | fetch + 格式检查 | checker + 人审 |

## 二、每收录页

| ID | 优先级 | 检查 | 判定 | 执行层 |
|---|---|---|---|---|
| C8 | P0 | 每页声明自己的规范网址,而且只声明一次 | 抓页比对 `<link rel=canonical>` × `Link: rel="canonical"` 响应头 | checker |
| C9 | P0 | 不执行 JS 也能拿到完整正文 | 禁 JS 抓取 ≥ 渲染版 90% | checker |
| C10 | P0 | 缓存下来的 HTML 里没有任何因人而异的内容 | 同一 URL 两次匿名抓取 diff 为空(抽查) | checker |
| C23 | P0 | 要收录的页没有被 noindex 挡住 | 抓页查 robots/googlebot meta + `X-Robots-Tag` 响应头 | checker |
| C11 | P1 | 每页的标题与摘要各不相同,且都不超长 | 样本集合比对 | checker |
| C12 | P1 | 结构化数据(JSON-LD)在、必填字段齐、没有已失效的类型 | 解析 ld+json(存在 / 语法 / 基础组与类型参数 / 负向扫描) | checker + 人审 |
| C13 | P1 | 没有「返回 200 但其实是空页或错误页」 | 内容长度阈值 + retired 抽查 | checker |
| C14 | P1 | 没有会把整页藏起来的第三方脚本(爬虫可能只拿到空白) | grep 已知 pattern + 渲染首屏非空白 | checker |
| C16 | P1 | 允许搜索结果展示完整摘要与大图 | 抓页查 robots meta | checker |
| C24 | P1 | 有移动端 viewport 声明 | 抓页查 meta | checker |
| C17 | P2 | 标题层级是一棵树:一个 h1,往下逐级不跳 | DOM 解析 heading 序列 | checker |
| C18 | P2 | 每张图都写了宽高和 alt | DOM/模板 grep | 站点 CI + checker |
| C19 | P2 | 分享到社交平台能出正确的预览卡(Open Graph) | 抓页查 meta;image 声明 1200×630;og:type × JSON-LD 文章类型交叉验 | checker |
| C20 | P2 | 不绕路:任何网址最多跳一次就到最终页 | 抓取时统计 redirect 链长 | checker |
| C15 | P2 | 收录页不是每次请求现渲染(SSR 要有 CDN 缓存) | curl 响应头 × 渲染策略声明 | checker |
| C25 | P2 | HTTPS 页里没有走 http:// 的图片或脚本 | 扫 img/script/iframe/link 等子资源 URL 协议 | checker |

## 三、条件项(人审项,不进 checker 脚本)

| ID | 优先级 | 检查 | 触发条件 | 判定 | 执行层 |
|---|---|---|---|---|---|
| C21 | P0 | YMYL 内容有作者、审核与权威引用 | `ymyl=true` | 上线前对照 C21 的 YMYL 信任块清单过检(见 references/checklist/references/C21.md) | 人审 |
| C22 | P1 | 语言版本之间用 hreflang 双向指认 | 站点有多语言配置 | 人工核对语言对两侧互指 | 人审 |

> 编号纪律:编号为**永久 ID**(被 `checks` 表/豁免引用):只顺延(下一条 C27)、不回收、不重排。
> **能并则并**:新检查若与旧条目**同优先级 + 同执行层 + 同一次抓取动作**,并进旧条目扩判定,不占新号
> (2026-08-25 的 C2/C6/C8/C18/C19 五处即此);判定动作或优先级不同才新开号。
> 表内行序 = 优先级分组(P0→P1→P2),同优先级内语义邻接;
> 新增条目编号顺延,行位插进所属节的优先级段。
> 优先级口径:**P0 = 存在层/事故层**(爬不到、收不进、合规或隐私风险,伤全站);
> **P1 = 表现层**(排名与引用打折);**P2 = 优化项**。
> 执行层「checker」= 手动运行的检查脚本(checker/);「站点 CI」= 各 repo 工程师侧。

## 权威依据(官方文档,C 集)

| 规则 | 依据 |
|---|---|
| C 全集总纲 | [Google Search Essentials](https://developers.google.com/search/docs/essentials)(前 Webmaster Guidelines) |
| C12 结构化数据 | [Google Structured Data 政策](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) + [schema.org](https://schema.org) |
| C8 canonical / C2 sitemap / robots | [Google Crawling & Indexing 文档](https://developers.google.com/search/docs/crawling-indexing)、[sitemaps.org](https://www.sitemaps.org)(协议本体) |
| C22 hreflang / C26 语言重定向 | [Google 多语言版本指南](https://developers.google.com/search/docs/specialty/international/localized-versions)(明确:别按推测语言自动跳转,用 hreflang 声明 + 让用户自选) |
| C4 CWV | [web.dev/vitals](https://web.dev/articles/vitals)(Chrome 团队,指标定义与阈值出处) |
| C1 AI 爬虫 UA | [OpenAI bots](https://platform.openai.com/docs/bots)、[Perplexity crawlers](https://docs.perplexity.ai/guides/bots)、Anthropic support 的 ClaudeBot 页、[Google crawler 清单](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers)(Google-Extended) |
| C16 / C23 robots 指令 | [Google robots meta 标签文档](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)(`max-snippet`/`noindex` 与 `X-Robots-Tag` 同源) |
| C18 图片 alt | [Google 图片 SEO 最佳实践](https://developers.google.com/search/docs/appearance/google-images) |
| C24 viewport | [Google:移动设备友好](https://developers.google.com/search/docs/appearance/mobile-friendly) |
| C25 mixed content | [MDN:混合内容](https://developer.mozilla.org/docs/Web/Security/Mixed_content)(浏览器拦截行为的规范说明) |
| C19 OG | [ogp.me](https://ogp.me)(The Open Graph protocol)+ 各社交平台卡片文档 |
| C5 IndexNow(C2 配套) | [indexnow.org](https://www.indexnow.org)(Microsoft/Bing 主导的开放协议) |
| C7 llms.txt | [llmstxt.org](https://llmstxt.org)(社区约定,非官方标准 — 唯一无大厂背书项) |
| C10/C20 | Search Essentials 反 cloaking / 重定向指南(隶属 C 全集总纲链接) |

链接失效或政策更新属 harness 变更,人审后更新本表。
