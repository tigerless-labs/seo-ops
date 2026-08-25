# skills/ —— 可单独装到别处的知识 skill

这两个 skill 让 agent 在**别的仓库里**也能对着 C 集 / T 集干活,不必把整个 seo-ops clone 过去。

| skill | 给谁 | 干什么 |
|---|---|---|
| `seo-ops/` | 工程 | 对照 **C 集** 审模板、meta、结构化数据、路由与渲染策略;code review 与上线前自查 |
| `seo-content/` | content / 设计 | 对照 **T 集** 查页面 doc 的 SEO 供给项交齐没有、合不合格 |

## 装

复制到 agent 加载 skill 的位置 —— Claude Code 是 `.claude/skills/`(项目级)或
`~/.claude/skills/`(个人级),别家 agent 按自己的约定。整个目录一起拷,不要只拷 `SKILL.md`。

```bash
cp -r skills/seo-ops ~/.claude/skills/
cp -r skills/seo-content ~/.claude/skills/
```

## 这两个 skill 里没有可写状态

**只有知识,没有脚本、没有配置、没有产出目录。** 所以更新时整个覆盖掉就行,不会丢东西。

这是有意的。Claude Code 的字符串替换里,普通 skill 没有任何「更新后仍存活」的数据目录
——`${CLAUDE_PLUGIN_DATA}` 只有 plugin skill 能用。**skill 目录不是放可变状态的地方**,
所以要跑 checker(需要 `sites.yaml`、`checker/.env`、`checker/out/`)就
[clone 本仓库](https://github.com/tigerless-labs/seo-ops):那三样都在 `.gitignore` 里,
`git pull` 更新时原地不动。

## `checklist/` 与 `content/` 是生成物

正本住仓库根,skill 里的是副本 —— skill 要能被单独复制走,必须自包含。

```bash
python3 skills/sync.py           # 改完正本,重新生成副本
python3 skills/sync.py --check   # 只校验,有漂移就打印差异并以 1 退出
```

**不要直接改 skill 里的副本**,改了下次同步就没了。两个 skill 带同一套 references,
因为 T 集每条都链到下游 C(`../checklist/references/C*.md`)、C12 又反链回 content-checklist
——那些链接就是「责任可回溯」的实现,断一条少一条。
