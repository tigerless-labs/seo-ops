# seo-ops

**SEO 基础工程的检查清单 + checker 脚本,打包成一个 Claude Code skill。**

自包含,零外部依赖(除 `requests` / `PyYAML`),不联系任何服务,只读目标站点的公开 HTTP 产出。

---

## 这是什么

**SEO 基础工程** = 让搜索引擎和 AI 检索能**抓到、读懂、收录、引用**一个网站所必需的机器可读结构。

它是地基:做好了不保证排名,做不好上面盖什么都没用——爬虫抓不到的页面,内容再好也不存在。
所以它的判定是**二元的结构问题**(该有的结构在不在、对不对),而不是效果问题(排名高不高)。

包里三份东西:

| 路径 | 是什么 | 给谁 |
|---|---|---|
| `checklist/checklist.md` | **C 集** — 26 条结构检查,分站级 / 每收录页 / 条件项;每条一篇详细说明 + 权威依据 | 工程团队 |
| `content/content-checklist.md` | **T 集** — SEO 基础工程所需信息的供给清单;每条标注它喂的下游 C 项 | **content / 设计团队** |
| `checker/run.py` | 跑 C 集的机器项,输出与 checklist 同构的报告 | 谁验收谁跑 |

外加 `redlines.md`(R1–R8 禁止事项)与 `ai-crawlers.yaml`(C1 检查的 AI 爬虫 UA 清单)。

### 为什么分成 C 集和 T 集

页面上线要满足的机器可读结构由 C 集检查,但其中一部分**只有写内容的人写得出来**
——图片 alt 文案、llms.txt 的一句话摘要、ymyl 判定。T 集就是那部分的交付单。

好处是**责任可回溯**:C 项红了,顺着「下游」列反查到对应的 T,立刻知道是 content 欠供
还是 frontend 没落。两个团队不用对着同一份文档吵谁该干什么。

### 三个设计约束

1. **三态判定** `pass / fail / N.A.(reason)` — 「没测」和「没事」不许混成一个绿。
   报告的分母恒定:每次都是同样 26 行,不因为某项测不了就少一行。
2. **纯 deterministic,零 LLM** — 抓取 → 正则/json 解析 → 阈值比较 → 拼 markdown。
   同站同配置两次跑逐字相同。这是它能当验收依据、能拿去跟施工方争议的全部理由。
3. **爬虫视角** — 不存 cookie、不发 `Accept-Language`。Googlebot 每次抓页都是无状态首访;
   复用 cookie 会让 checker 表现得像个「浏览过一遍的用户」,测的就不是爬虫看到的东西了。

---

## 装

把下面整段复制给 Claude Code 或其他 coding agent,它会自己装好:

````
按 https://github.com/tigerless-labs/seo-ops/blob/main/INSTALL.md 的说明,
把 seo-ops 装成一个 skill。装完照该文档最后一步向我汇报。
````

## 用

装好后直接在对话里说:

> 跑一下 seo-ops 检查 tigerless.com

命令行、配置项、报告怎么读,agent 都在 `SKILL.md` 里,不用你记。
