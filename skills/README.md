# skills/ —— 可单独装到别处的 skill

让 agent 在**别的仓库里**也能对着 C 集 / T 集干活,不必把整个 seo-ops clone 过去。

| skill | 给谁 | 干什么 | 带 checker |
|---|---|---|---|
| `seo-ops/` | 工程 | 对照 **C 集** 审模板、meta、结构化数据、路由与渲染策略;也能就地跑机器检查出报告 | ✅ |
| `seo-content/` | content / 设计 | 对照 **T 集** 查页面 doc 的 SEO 供给项交齐没有、合不合格 | — |

## 装

复制到 agent 加载 skill 的位置 —— Claude Code 是 `.claude/skills/`(项目级)或
`~/.claude/skills/`(个人级),别家 agent 按自己的约定。整个目录一起拷,不要只拷 `SKILL.md`。

```bash
cp -r skills/seo-ops ~/.claude/skills/
cp -r skills/seo-content ~/.claude/skills/
```

`seo-ops` 要跑 checker 的话再装两个依赖:`pip install -r <skill>/checker/requirements.txt`。
有 CrUX key 就 `mkdir -p ~/.config/seo-ops && cp <skill>/checker/.env.example ~/.config/seo-ops/.env` 填上;不填 C4 记 N.A. 不判红。

## 脚本住 skill,产出住包外

skill 目录会被整包覆盖(更新 = 重新复制),所以**里面不许有可写状态**。
checker 因此一个字节都不往 skill 里写,产出与机密各有固定去处:

| | 默认位置 | 覆盖方式 |
|---|---|---|
| 花名册与产出 | `~/Documents/seo-ops/` | `--state-dir` 或 `$SEO_OPS_DIR` |
| 机密(API key) | `~/.config/seo-ops/.env` | `$SEO_OPS_CONFIG_DIR` |

**分两处是有意的**:报告要给人读、要拿去跟施工方对账,该待在找得到的地方;
但 `~/Documents` 常被 iCloud/OneDrive/Dropbox 同步、被备份、被整夹分享出去,
API key 不能跟着走。同 last30days 的约定(产出进 Documents,key 进 `~/.config`)。

### 为什么不用 `${CLAUDE_PROJECT_DIR}`

试过,放弃了。它是 **Claude Code 的私有扩展,不在 Agent Skills spec 里**
——spec 只说「use relative paths from the skill root」,不定义任何路径变量。
后果是别家 agent(Codex 等)照抄这份 SKILL.md 时不会替换它:原样传进去,
或被 shell 展开成空串变成 `/.seo-ops`,在容器里以 root 跑会真的建在文件系统根目录。

固定位置不依赖任何变量,所以 **Claude Code / Codex / 裸命令行行为一致**。
`state_dir()` 里仍留着两道守卫,专门拦这两种烂法,会直接报错退出而不是静默落错地方。

顺带:产出也不该跟着「当前项目」走。`sites.yaml` 是一份**站点**花名册、
`checks.db` 是**站点**的历史,属于「你负责哪些站」,不属于「你此刻在哪个仓库里」
—— 同一批站从三个仓库验收,不该得到三份割裂的历史。

## 副本是生成物

正本住仓库根,skill 里的是副本 —— skill 要能被单独复制走,必须自包含。

```bash
python3 skills/sync.py           # 改完正本,重新生成副本
python3 skills/sync.py --check   # 只校验,有漂移就打印差异并以 1 退出(CI 会跑)
```

**不要直接改 skill 里的副本**,改了下次同步就没了。带哪些正本在 `sync.py` 的 `PAYLOAD` 里登记:
两个 skill 都带全套 references(T 集每条链到下游 C、C12 又反链 content-checklist,
那些链接就是「责任可回溯」的实现,断一条少一条),只有 `seo-ops` 带 `checker/` 与
`ai-crawlers.yaml`(C1 的运行期依赖,漏了会跑到一半崩)。
