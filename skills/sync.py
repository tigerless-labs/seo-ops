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
PAYLOAD = ("checklist", "content")          # 正本目录名,skill 内同名


def targets():
    return sorted(p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def diff(a: Path, b: Path, rel=""):
    """逐文件比对,返回差异描述列表。b 缺失/多余/内容不同都算。"""
    out = []
    if not b.exists():
        return [f"  缺整个目录:{rel or b.name}/"]
    cmp = filecmp.dircmp(a, b)
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
        for name in PAYLOAD:
            src, dst = ROOT / name, skill / name
            if check:
                d = diff(src, dst)
                if d:
                    drift[f"{skill.name}/{name}"] = d
            else:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

    if check:
        if drift:
            print("⚠️  skill 副本与正本不一致 —— 跑 `python3 skills/sync.py` 重新生成:\n")
            for k, lines in drift.items():
                print(f"{k}/")
                print("\n".join(lines))
            sys.exit(1)
        print(f"✅ {len(skills)} 个 skill 的副本与正本一致")
    else:
        print(f"✅ 已同步 {', '.join(p.name for p in skills)}({'、'.join(PAYLOAD)})")


if __name__ == "__main__":
    main()
