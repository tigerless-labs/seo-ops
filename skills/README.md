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

## 脚本住 skill,状态住项目

这是 Claude Code 官方给的分工,靠两个变量落地:

| | 变量 | 谁用 |
|---|---|---|
| 脚本本体 | `${CLAUDE_SKILL_DIR}` | `SKILL.md` 里写运行命令,并在 `allowed-tools` 里写同一路径 —— 两处一致才不弹权限提示 |
| 实例状态与产出 | `${CLAUDE_PROJECT_DIR}` | checker 把 `sites.yaml` / `.env` / `out/` 落在 `${CLAUDE_PROJECT_DIR}/.seo-ops/` |

**skill 目录里不许有可写状态。** 普通 skill 在 Claude Code 的字符串替换里
**没有任何「更新后仍存活」的数据目录** —— `${CLAUDE_PLUGIN_DATA}` 只有 plugin skill 能用。
skill 更新是整包覆盖,写进去的必丢(`checks.db` 尤其可惜,它设计成跨次累积好做 diff)。

状态因此跟着**被检查的项目**走,而不是跟着**工具装在哪**走。副作用是同一条命令换个安装
位置也给同一个结论 —— 反例见 `checker/config.py::load_env` 里那段注释:包内 `.env` 曾让
同一个站一处出 C4 实测值、一处记 `need-crux-key`。

装进别的项目后,**把 `.seo-ops/` 加进那个项目的 `.gitignore`**。

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
