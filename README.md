# seo-ops

**SEO 基础工程的检查清单 + checker 脚本,整个仓库就是一个 agent skill。**

自包含,零外部依赖(除 `requests` / `PyYAML`),不联系任何服务,只读目标站点的公开 HTTP 产出。

---

## 装

**整个仓库就是一个 skill。** clone 到 agent 加载 skill 的位置即可:

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.claude/skills/seo-ops
pip install -r ~/.claude/skills/seo-ops/scripts/requirements.txt
```

Claude Code 个人级用 `~/.claude/skills/`、项目级用 `<repo>/.claude/skills/`;
Codex 用 `~/.codex/skills/` 或 `.codex/skills/`;别家 agent 按自己的约定。
更新就 `git pull` —— 没有副本、没有同步脚本,只有一份正本。

## 用

装好后直接说:

> 跑一下 tigerless.com 的 SEO 检查

命令行、配置项、报告怎么读,agent 从 `SKILL.md` 自己查,不用你记。

配置(花名册 + API key)在 **`~/.config/seo-ops/`**,产出在 **`~/Documents/seo-ops/out/`**
—— 都在 skill 目录外,所以更新时原地不动,也不可能被误提交。

## content 团队怎么用

**你只需要过一份清单:T 集。** 不用跑脚本,不用读 C 集(那是工程侧的活)。

装法同上,然后说一句:**「用 seo-ops 检查这份页面 doc 的 SEO 供给项」**,把文档给它。
它按 T 集逐条列出缺什么、怎么补,你照着补。就这些。

清单本体是 [references/content/content-checklist.md](references/content/content-checklist.md),想自己读也行
—— 每条都有一篇「要交什么、什么样算合格」的详细说明。

---

## 这是什么

**SEO 基础工程** = 让搜索引擎和 AI 检索能**抓到、读懂、收录、引用**一个网站所必需的机器可读结构。

它是地基:做好了不保证排名,做不好上面盖什么都没用——爬虫抓不到的页面,内容再好也不存在。
所以它的判定是**二元的结构问题**(该有的结构在不在、对不对),而不是效果问题(排名高不高)。

| 路径 | 是什么 | 给谁 |
|---|---|---|
| `references/checklist/checklist.md` | **C 集** — 26 条结构检查,每条一篇详细说明 + 权威依据 | 工程团队 |
| `references/content/content-checklist.md` | **T 集** — SEO 所需信息的供给清单,每条标注它喂的下游 C 项 | **content / 设计团队** |
| `scripts/run.py` | 跑 C 集的机器项,输出与 checklist 同构的报告 | 谁验收谁跑 |

外加 `redlines.md`(R1–R8 禁止事项)与 `references/ai-crawlers.yaml`(C1 检查的 AI 爬虫 UA 清单)。

## 为什么这么设计

**C 集与 T 集分开** — 机器可读结构里有一部分只有写内容的人写得出来(图片 alt、llms.txt
摘要、ymyl 判定),那部分单独立为 T 集。好处是**责任可回溯**:C 项红了,顺着「下游」列
反查到对应的 T,立刻知道是 content 欠供还是 frontend 没落,两个团队不用吵谁该干什么。

**三态判定** `pass / fail / N.A.(reason)` — 「没测」和「没事」不许混成一个绿。
报告分母恒定:每次都是同样 26 行,不因为某项测不了就少一行。

**纯 deterministic,零 LLM** — 抓取 → 解析 → 阈值比较 → 拼 markdown。同站同配置两次跑
逐字相同。这是它能当验收依据、能拿去跟施工方争议的全部理由。

**爬虫视角** — 不存 cookie、不发 `Accept-Language`。Googlebot 每次抓页都是无状态首访;
复用 cookie 会让 checker 表现得像个「浏览过一遍的用户」,测的就不是爬虫看到的东西了。
