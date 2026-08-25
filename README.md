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

## 用法

### 装

```bash
pip install -r checker/requirements.txt
```

只要 `requests` 和 `PyYAML`,其余是标准库。Python ≥ 3.9。

### 跑

```bash
python3 checker/run.py --target https://example.com
```

| 命令 | 跑什么 |
|---|---|
| `run.py --target https://example.com` | 任意站点根 URL,不需要配置文件 |
| `run.py --target http://localhost:3000` | 本地部署(自动判定为本地模式) |
| `run.py` | `sites.yaml` 里的全部站点 |
| `run.py --site <id>` | `sites.yaml` 里的一个站 |

多站先建 `sites.yaml`,照抄 `sites.example.yaml` 改。

临时覆盖参数:`--page-sample N` `--sitemap-sample N` `--max-pages N` `--sleep S`。

**`--target` 必须是 origin**(scheme + host[:port]),不带 path/query;传别的会直接报错退出,不猜。

**耗时**:默认单线程 1 秒间隔,请求数约 `2 × sitemap 条目数`。271 页的站约 7 分钟。
日常想快用 `--page-sample 100` —— 结构问题是模板级的,抽样和全量看到的是同一批。

**公网 staging 域不支持**:会被当生产域测,归一检查必然误红。测试二选一:上线,或本地部署。

### 配

判定参数全在 `checker/config.py`,按 C 号分组。改阈值只动这里,判定逻辑住 `run.py`。

**机密不进 config.py**:

```bash
cp checker/.env.example checker/.env
```

| 变量 | 给谁用 | 不填的后果 |
|---|---|---|
| `CRUX_API_KEY` | C4(Core Web Vitals,查 Chrome UX Report) | C4 记 `need-crux-key`,不判红 |
| `INDEXNOW_KEYS` | C5(IndexNow key 文件) | C5 记 `need-key-declaration`,不判红 |

CrUX key 免费、不绑卡、约 3 分钟,申请流程见 `checklist/references/C4.md`。

### 读报告

输出 `checker/out/report-<site>-<date>.md`(人读)和 `checks.db`(SQLite,机读)。

| 结果 | 含义 |
|---|---|
| ✅ pass | 测了,通过 |
| 🔴 fail | 测了,没通过 —— 证据列给出违规页与原因 |
| ⚪ N.A. | **没测**,括号里是原因码 |
| 👤 人审 | 脚本不判,列出来提醒人过 |

顶部两行告警要看:**🚦 被目标限流** = 目标站在拦我们,受影响判定记 N.A. 不记 fail,
降速重跑才有完整结论;**⚠️ 样本抓取失败** = 真的抓不到,这些页不进分母。

优先级:**P0 = 存在层/事故层**(爬不到、收不进);**P1 = 表现层**(排名与引用打折);**P2 = 优化项**。
修的顺序按这个来,别按红项数量。

### 改清单

**checklist 与脚本是两份,各自维护** —— 检查逻辑没法从表格自动生成。但条目集合可以对齐:
每次启动跑 `verify_checklist_sync()`,条目/优先级/所属节对不上就在 stdout 打 ⚠️。

**加条目的顺序:先改 `checklist/checklist.md`,再改 `run.py` 的 `CHECKS` 和判定逻辑。**
编号是永久 ID(报告与 `checks` 表按它索引):只顺延、不回收、不重排。

---

## 安装(给 code agent 的 prompt)

把下面整段复制给 Claude Code 或其他 coding agent,它会自己装好:

````
把 seo-ops 装成一个 skill。

1. 确认当前仓库根目录,建 `.claude/skills/seo-ops/`(若是个人全局安装则用
   `~/.claude/skills/seo-ops/`)。
2. 把 seo-ops 包的全部内容复制进去,保持目录结构不变:

   seo-ops/
   ├── SKILL.md
   ├── README.md
   ├── redlines.md
   ├── ai-crawlers.yaml
   ├── sites.example.yaml
   ├── checker/{run.py,config.py,requirements.txt,.env.example}
   ├── checklist/{checklist.md,references/C*.md}
   └── content/{content-checklist.md,references/T*.md}

   目录结构不能改 —— `run.py` 靠相对路径找 `checklist/checklist.md` 和
   `ai-crawlers.yaml`,挪位置会让启动时的漂移守卫失效。

3. 装依赖:`pip install -r <skill>/checker/requirements.txt`(只有 requests 和 PyYAML)。
4. 冒烟测试,确认能跑通且漂移守卫不报警:

   python3 <skill>/checker/run.py --target https://example.com --page-sample 2 --max-pages 2

   预期:输出一行「🔴 N · ✅ N · ⚪ N.A. N · 👤 人审 2」和报告路径;
   stdout 不应出现任何 ⚠️ 漂移 行。出现了说明复制不全。
5. 读一遍 SKILL.md,然后告诉我:这个 skill 覆盖什么、不覆盖什么、
   以及要跑完整判定还需要我提供哪些配置(提示:.env 里那两个可选 key)。

不要修改 checklist 的任何条目编号或优先级 —— 它们是永久 ID,被报告和 checks 表引用。
````

装好后在对话里说「跑一下 seo-ops 检查 <你的域名>」即可。
