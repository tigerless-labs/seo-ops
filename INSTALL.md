# 安装 seo-ops

> 本篇是给 **code agent** 读的安装说明。人不用照做——把 README 里那段 prompt 复制给 agent 即可。

## 1. 定安装位置

按**你自己加载 skill 的方式**决定放哪 —— 各家 agent 约定不同,这里不规定。
只有一条硬要求:整包放在同一个目录下,`seo-ops/` 内部的相对结构不动。

如果你支持项目级与全局两种安装,问用户装哪种;不确定就装项目级。

## 2. 复制整包

把 seo-ops 的全部内容复制进去,**保持目录结构不变**:

```
seo-ops/
├── SKILL.md
├── README.md
├── INSTALL.md
├── redlines.md
├── ai-crawlers.yaml
├── sites.example.yaml
├── checker/{run.py,config.py,requirements.txt,.env.example}
├── checklist/{checklist.md,references/C*.md}
└── content/{content-checklist.md,references/T*.md}
```

目录结构不能改 —— `run.py` 靠相对路径找 `checklist/checklist.md` 和 `ai-crawlers.yaml`,
挪位置会让启动时的漂移守卫失效。

## 3. 装依赖

```bash
pip install -r <skill>/checker/requirements.txt
```

只有 `requests` 和 `PyYAML`,其余是标准库。Python ≥ 3.9。

## 4. 冒烟测试

```bash
python3 <skill>/checker/run.py --target https://example.com --page-sample 2 --max-pages 2
```

预期:输出一行「🔴 N · ✅ N · ⚪ N.A. N · 👤 人审 2」和报告路径;
**stdout 不应出现任何 ⚠️ 漂移 行** —— 出现了说明复制不全,回到第 2 步。

## 5. 可选配置

两个 key 不填也能跑,只是对应条目记 N.A. 不判红:

```bash
cp <skill>/checker/.env.example <skill>/checker/.env
```

| 变量 | 给谁用 | 不填的后果 |
|---|---|---|
| `CRUX_API_KEY` | C4 Core Web Vitals(查 Chrome UX Report) | C4 记 `need-crux-key` |
| `INDEXNOW_KEYS` | C5 IndexNow key 文件 | C5 记 `need-key-declaration` |

CrUX key 免费、不绑卡、约 3 分钟,申请流程见 `checklist/references/C4.md`。

## 6. 汇报

读一遍 `SKILL.md`,然后告诉用户:这个 skill 覆盖什么、不覆盖什么,
以及要跑完整判定还需要提供哪些配置。

---

**不要修改 checklist 的任何条目编号或优先级** —— 它们是永久 ID,被报告和 `checks` 表引用,
只顺延、不回收、不重排。
