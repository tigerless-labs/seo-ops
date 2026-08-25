#!/usr/bin/env python3
"""把仓库根的 checklist/ 与 content/ 同步进各个 skill 目录。

skill 要能被单独复制到别的仓库用,所以必须自包含 —— 清单正本住仓库根,
skill 里的是副本。**副本是生成物,不要手改**:改正本,再跑本脚本。

  python3 skills/sync.py            # 生成/更新副本
  python3 skills/sync.py --check    # 只校验;有漂移则打印差异并以 1 退出(给 CI / 提交前用)

为什么整份复制而不是挑着复制:T 集每条都链到下游 C(../checklist/references/C*.md),
C12 又反链 content-checklist.md —— 那些链接是「责任可回溯」的实现,断一条就少一条。
两个 skill 因此带同一套 references,区别只在 SKILL.md 给的入口与职责。
"""
import filecmp, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# 每个 skill 带哪些正本(目录或文件)。两个都带全套 references(T 集每条链到下游 C,
# 断了就少一条可回溯路径)与 redlines.md(R 集是两边都要引的硬约束);
# 只有 seo-ops 带 checker —— content 团队不跑机器验收。
#
# **ai-crawlers.yaml 是 run.py 的运行期依赖**(C1 读它),漏了它 skill 副本会跑到一半崩;
# sites.example.yaml 则是 sites_file() 找不到花名册时给出的抄写模板。
# 教训:自包含要按「运行时真正打开哪些文件」列,不能按「感觉哪些是文档」列。
PAYLOAD = {
    "seo-ops":     ("checklist", "content", "checker",
                    "ai-crawlers.yaml", "sites.example.yaml", "redlines.md"),
    "seo-content": ("checklist", "content", "redlines.md"),
}

# checker 里这些是实例状态或本地产物,不进 skill(状态住 <state-dir>,见 config.state_dir)。
# 复制与校验必须用同一份清单 —— 两处不一致的话,--check 会把「有意不复制」报成漂移。
EXCLUDE_NAMES = [".env", "out", "__pycache__"]
EXCLUDE = shutil.ignore_patterns(*EXCLUDE_NAMES, "*.pyc")


def targets():
    return sorted(p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def diff(a: Path, b: Path, rel=""):
    """逐文件比对,返回差异描述列表。b 缺失/多余/内容不同都算。a 是文件时按单文件比。"""
    out = []
    if not b.exists():
        return [f"  缺:{rel or b.name}" + ("/" if a.is_dir() else "")]
    if a.is_file():
        return [] if filecmp.cmp(a, b, shallow=False) else [f"  改:{b.name}"]
    cmp = filecmp.dircmp(a, b, ignore=EXCLUDE_NAMES)
    out += [f"  少:{rel}{n}" for n in sorted(cmp.left_only)]
    out += [f"  多:{rel}{n}" for n in sorted(cmp.right_only)]
    out += [f"  改:{rel}{n}" for n in sorted(cmp.diff_files)]
    for sub in sorted(cmp.common_dirs):
        out += diff(a / sub, b / sub, f"{rel}{sub}/")
    return out


def main():
    check = "--check" in sys.argv
    skills = targets()
    if not skills:
        sys.exit("skills/ 下没有找到任何含 SKILL.md 的目录")

    drift = {}
    for skill in skills:
        payload = PAYLOAD.get(skill.name)
        if payload is None:
            sys.exit(f"skills/{skill.name}/ 没在 sync.py 的 PAYLOAD 里登记,不知道该同步什么")
        for name in payload:
            src, dst = ROOT / name, skill / name
            if check:
                d = diff(src, dst)
                if d:
                    drift[f"{skill.name}/{name}"] = d
            elif src.is_file():
                shutil.copy2(src, dst)
            else:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=EXCLUDE)

    if check:
        if drift:
            print("⚠️  skill 副本与正本不一致 —— 跑 `python3 skills/sync.py` 重新生成:\n")
            for k, lines in drift.items():
                print(k)
                print("\n".join(lines))
            sys.exit(1)
        print(f"✅ {len(skills)} 个 skill 的副本与正本一致")
    else:
        for p in skills:
            print(f"✅ {p.name} ← {'、'.join(PAYLOAD[p.name])}")


if __name__ == "__main__":
    main()
