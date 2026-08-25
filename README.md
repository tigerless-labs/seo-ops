# seo-ops

**SEO 基础工程的检查清单 + checker 脚本。**

自包含,零外部依赖(除 `requests` / `PyYAML`),不联系任何服务,只读目标站点的公开 HTTP 产出。

---

## 装

```bash
git clone https://github.com/tigerless-labs/seo-ops.git
cd seo-ops && pip install -r checker/requirements.txt
```

只有 `requests` 和 `PyYAML`,其余是标准库。Python ≥ 3.9。

## 用

在这个目录里开 Claude Code(或别的 coding agent),直接说:

> 跑一下 tigerless.com 的 SEO 检查

命令行、配置项、报告怎么读,agent 会从 `CLAUDE.md` 自己查,不用你记。

报告落在 `.seo-ops/out/`。这个目录连同 `.env` 都在 `.gitignore` 里 —— 更新直接 `git pull`,
你的花名册、API key、历史报告原地不动。

## 装到别的仓库去

想让**别的仓库**的 agent 也能对着清单干活(审模板、查页面 doc),不用把整个仓库 clone 过去
—— [skills/](skills/README.md) 下有两个可单独安装的 skill,复制走即可:

| skill | 给谁 |
|---|---|
| `skills/seo-ops` | 工程:对照 C 集审模板、meta、结构化数据、路由与渲染策略;也带 checker,能就地跑 |
| `skills/seo-content` | content / 设计:对照 T 集查页面 doc 的 SEO 供给项 |

装进去之后,报告和配置落在**那个项目**的 `.seo-ops/` 下,不在 skill 目录里 ——
skill 更新是整包覆盖,状态放里面必丢。

---

## 这是什么

**SEO 基础工程** = 让搜索引擎和 AI 检索能**抓到、读懂、收录、引用**一个网站所必需的机器可读结构。

它是地基:做好了不保证排名,做不好上面盖什么都没用——爬虫抓不到的页面,内容再好也不存在。
所以它的判定是**二元的结构问题**(该有的结构在不在、对不对),而不是效果问题(排名高不高)。

| 路径 | 是什么 | 给谁 |
|---|---|---|
| `checklist/checklist.md` | **C 集** — 26 条结构检查,每条一篇详细说明 + 权威依据 | 工程团队 |
| `content/content-checklist.md` | **T 集** — SEO 所需信息的供给清单,每条标注它喂的下游 C 项 | **content / 设计团队** |
| `checker/run.py` | 跑 C 集的机器项,输出与 checklist 同构的报告 | 谁验收谁跑 |

外加 `redlines.md`(R1–R8 禁止事项)与 `ai-crawlers.yaml`(C1 检查的 AI 爬虫 UA 清单)。

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
