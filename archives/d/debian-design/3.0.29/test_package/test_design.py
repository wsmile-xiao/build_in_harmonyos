#!/usr/bin/env python3
"""debian-design 3.0.29 适配自检（M，非上游用例）。

用法: python3 test_design.py <package_folder>

补上游没有的一致性检查：节点/模板齐全、模板仍是模板（占位符还在）、
上游组合骨架 Makefile 随包交付、安装目录未混入上游维护文件。
上游 N=0（无测试目录、无 autopkgtest、Makefile 的组合依赖外部 boxer），
因此这些断言是**适配自检**，与消费者用例（consumer_design.py）分列申报。
"""

import os
import sys

BLEND_DIR = os.path.join("share", "design-blends")
NODES = ("desktop", "desktop-animation", "desktop-graphics", "desktop-web")
SKEL = ("preseed.cfg.in", "script.sh.in")
EXPECTED_CLASSES = 59
FORBIDDEN = ("debian", "sources.list", "content", ".git")

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def count_classes(path):
    classes, in_classes = 0, False
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.strip().startswith("classes:"):
            in_classes = True
            continue
        if in_classes:
            if line.startswith(("  - ", "- ")):
                classes += 1
            elif line.strip() and not line.startswith((" ", "\t")):
                in_classes = False
    return classes


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    blend = os.path.join(pkg, BLEND_DIR)
    nodes_dir = os.path.join(blend, "nodes")
    skel_dir = os.path.join(blend, "skel")

    check(os.path.isdir(nodes_dir), f"{BLEND_DIR}/nodes/ 存在")
    found = sorted(n[:-4] for n in os.listdir(nodes_dir)) if os.path.isdir(nodes_dir) else []
    check(found == sorted(NODES), f"节点集合与上游一致（{len(NODES)} 个：{', '.join(NODES)}）")

    total = sum(count_classes(os.path.join(nodes_dir, n + ".yml"))
                for n in found if os.path.isfile(os.path.join(nodes_dir, n + ".yml")))
    check(total == EXPECTED_CLASSES, f"类清单总数 == {EXPECTED_CLASSES}（实际 {total}）")

    check(all(os.path.isfile(os.path.join(skel_dir, s)) for s in SKEL),
          f"两份 live 安装模板齐备（{', '.join(SKEL)}）")

    preseed = open(os.path.join(skel_dir, "preseed.cfg.in"), encoding="utf-8").read()
    script = open(os.path.join(skel_dir, "script.sh.in"), encoding="utf-8").read()
    check("[% suite %]" in preseed and "[% suite %]" in script
          and "[% pkglist %]" in script,
          "模板仍带占位符（[% suite %] / [% pkglist %] 未被提前展开）")

    check(os.path.isfile(os.path.join(blend, "Makefile")),
          "上游组合骨架 Makefile 随包交付")

    leaked = [e for e in FORBIDDEN if os.path.exists(os.path.join(blend, e))]
    check(not leaked, f"安装目录未混入上游维护文件/构建产物（发现 {leaked}）")

    passed = sum(1 for ok, _ in _results if ok)
    total_n = len(_results)
    print(f"\n        [test] {passed}/{total_n} assertions passed")
    if passed != total_n:
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
