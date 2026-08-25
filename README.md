# seo-ops

三样东西:

| | 是什么 |
|---|---|
| [references/checklist/checklist.md](references/checklist/checklist.md) | **C 集** —— 26 条 SEO/GEO 结构检查,分站级 / 每收录页 / 条件项。每条另有一篇详细说明(判定标准、常见错法、权威依据),住 `references/checklist/references/C<N>.md` |
| [scripts/run.py](scripts/run.py) | **checker 脚本** —— 输入一个 URL 就模拟爬虫去抓、按 C 集出报告。**零 LLM、不依赖任何前端架构**:只读线上 HTTP/HTML 产出,React / Vue / Next / WordPress / 纯静态都一样测 |
| [references/content/content-checklist.md](references/content/content-checklist.md) | **T 集** —— 给网站内容设计团队的供给清单:SEO 需要哪些信息由 content 提供(title/desc、H2 大纲、图片 alt、ymyl 判定、OG 文案等),每条标注它喂的下游 C 项。每条详情住 `references/content/references/T<N>.md` |

---

## 单独跑脚本(不装 skill 也能用)

```bash
git clone https://github.com/tigerless-labs/seo-ops.git
cd seo-ops
python3 -c "import requests, yaml" || pip install -r scripts/requirements.txt
```

只要 `requests` 和 `PyYAML`,Python ≥ 3.9。报 `externally-managed-environment`(PEP 668)时用
`apt install python3-requests python3-yaml` 或建 venv。

```bash
python3 scripts/run.py --target https://example.com      # 线上站
python3 scripts/run.py --target http://localhost:3000    # 本地部署
python3 scripts/run.py                                   # 跑 sites.yaml 里全部站
python3 scripts/run.py --site <id>                       # 只跑其中一个
```

`--target` 必须是 origin(`scheme + host[:port]`,不带 path/query)。
常用参数:`--page-sample N`(抽样,默认全量)、`--sleep S` / `--workers N`(节流)、
`--out <path>`(报告落哪)、`--verify-only`(只跑自检,不联网)。

**产出**落 `~/Documents/seo-ops/out/`:`report-<site>-<date>.md`(人读)与
`checks.db`(SQLite,跨次累积可 diff)。

**配置**在 `~/.config/seo-ops/`,都不是必需的,照模板复制即可:

```bash
mkdir -p ~/.config/seo-ops
cp references/sites.example.yaml  ~/.config/seo-ops/sites.yaml    # 多站花名册
cp references/config.example.yaml ~/.config/seo-ops/config.yaml   # 改阈值
cp references/.env.example        ~/.config/seo-ops/.env          # CrUX / IndexNow key
```

271 页的站全量约 7 分钟(默认单线程 1 秒间隔)。

---

## 装成 skill(让 agent 全自动跑)

整个仓库同时是一个 Agent Skill —— 装上之后直接说「检查一下 tigerless.com 的 SEO」,
agent 会自己确认目标、跑脚本、读报告,并按 P0/P1/P2 讲清每条红项该怎么改。

### 终端安装

**Claude Code**

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.claude/skills/seo-ops
```

**Codex**

```bash
git clone https://github.com/tigerless-labs/seo-ops.git ~/.codex/skills/seo-ops
```

装项目级就把 `~/.claude` 换成 `<你的仓库>/.claude`(Codex 同理)。更新:`git pull`。

### 让 agent 自己装

把下面整段复制给 agent:

````
把 https://github.com/tigerless-labs/seo-ops 装成一个 skill:

1. clone 到你加载 skill 的位置,目录名用 seo-ops
   (Claude Code:~/.claude/skills/ 或 <repo>/.claude/skills/;Codex:~/.codex/skills/)
2. 整个仓库一起装,不要只拷 SKILL.md —— scripts/ 与 references/ 都是运行期依赖
3. 装依赖:python3 -c "import requests, yaml" || pip install -r <skill>/scripts/requirements.txt
4. 冒烟:python3 <skill>/scripts/run.py --verify-only,应输出「✅ 清单与脚本对齐」
5. 读一遍 SKILL.md,然后告诉我它能查什么、不查什么
````
