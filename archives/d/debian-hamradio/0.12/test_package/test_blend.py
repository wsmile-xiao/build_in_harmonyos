#!/usr/bin/env python3
"""debian-hamradio 数据包验证脚本。

用法: python3 test_blend.py <package_folder>

验证的是**任务数据本体**而不是"文件存在"：

  * `debian-hamradio-tasks.desc`（tasksel 消费的成品）里的每个 `Task:` 段都必须有
    `Description:`，并且**除去 meta 任务外，每个任务名都要能在 `tasks/` 里找到
    同名源文件** —— 少一个源文件就是该任务的描述无法再生成/回溯；
  * `.desc` 的段数与 `tasks/` 的文件数必须与上游逐字一致；
  * `tasks/` 下每个源文件都必须自带 `Task:` 与 `Description:` 字段；
  * logo 必须是合法 SVG（根元素为 svg）；
  * 安装目录里不能混进构建系统（Makefile）、上游打包目录（debian/）或维护脚本
    （src/*.py、dependency_data/）。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

BLEND = "debian-hamradio"
PREFIX = "hamradio-"
EXPECTED_TASK_SECTIONS = 13
EXPECTED_TASK_FILES = 12
EXPECT_EXACT_TASK_FILES = True
EXPECT_LOGO = False
EXPECT_DOC = False
LOGO_NAME = ""
SVG_NS = "{http://www.w3.org/2000/svg}"
DESC_NAME = BLEND + "-tasks.desc"

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_blend.py <package_folder>")
        return 2
    package_folder = sys.argv[1]
    share = os.path.join(package_folder, "share")
    tasks_dir = os.path.join(share, "blends", BLEND, "tasks")
    desc_path = os.path.join(share, "tasksel", "descs", DESC_NAME)

    # ── 1. 成品 .desc ──────────────────────────────────────────────────
    if not check(os.path.isfile(desc_path), f"share/tasksel/descs/{DESC_NAME} 存在"):
        return finish()
    with open(desc_path, encoding="utf-8", errors="replace") as handle:
        desc = handle.read()
    sections = re.split(r"^Task:\s*", desc, flags=re.M)[1:]
    names = [s.splitlines()[0].strip() for s in sections]
    check(len(names) == EXPECTED_TASK_SECTIONS,
          f".desc 含 {EXPECTED_TASK_SECTIONS} 个 Task 段（实际 {len(names)}）")
    check(len(set(names)) == len(names), "Task 名无重复")
    check(names and names[0] == BLEND, f"首个 Task 段是 meta 任务 {BLEND}")
    no_desc = [n for n in names if "Description:" not in desc.split("Task: " + n, 1)[-1][:400]]
    check(not no_desc, f"每个 Task 段都有 Description（缺 {no_desc[:3]}）")

    # ── 2. 逐任务源文件 ────────────────────────────────────────────────
    if not check(os.path.isdir(tasks_dir), "share/blends/<blend>/tasks/ 存在"):
        return finish()
    sources = sorted(os.listdir(tasks_dir))
    check(len(sources) == EXPECTED_TASK_FILES,
          f"tasks/ 源文件数 == {EXPECTED_TASK_FILES}（实际 {len(sources)}）")

    mapped = [n[len(PREFIX):] for n in names
              if n != BLEND and n.startswith(PREFIX)]
    missing = [m for m in mapped if m not in sources]
    check(not missing,
          f".desc 的每个任务都有同名源文件（缺 {missing[:5]}）")
    if EXPECT_EXACT_TASK_FILES:
        check(set(mapped) == set(sources),
              f"tasks/ 与 .desc 的任务集合完全一致"
              f"（多 {sorted(set(sources) - set(mapped))[:5]}）")

    bad = []
    for name in sources:
        text = open(os.path.join(tasks_dir, name), encoding="utf-8",
                    errors="replace").read()
        head = text[:600]
        if not re.search(r"^Task:\s*\S", head, re.M) or "Description:" not in head:
            bad.append(name)
    check(not bad, f"每个任务源文件都含 Task: 与 Description:（异常 {bad[:3]}）")

    # ── 3. logo ────────────────────────────────────────────────────────
    if EXPECT_LOGO:
        logo = os.path.join(share, "pixmaps", LOGO_NAME)
        if check(os.path.isfile(logo), f"share/pixmaps/{LOGO_NAME} 存在"):
            try:
                root = ET.parse(logo).getroot()
                ok = root.tag == SVG_NS + "svg"
            except ET.ParseError:
                ok = False
            check(ok, "logo 是合法 SVG（根元素为 svg）")

    # ── 4. 文档 / 许可 / 纯净性 ────────────────────────────────────────
    doc_dir = os.path.join(share, "doc", BLEND)
    docs = sorted(os.listdir(doc_dir)) if os.path.isdir(doc_dir) else []
    if EXPECT_DOC:
        check(docs == ["AUTHORS"], f"share/doc/{BLEND} 随包发布（实际 {docs}）")
    else:
        check(not docs, f"上游无 AUTHORS，share/doc/{BLEND} 不应凭空出现（实际 {docs}）")

    lic_dir = os.path.join(package_folder, "licenses")
    lic = sorted(os.listdir(lic_dir)) if os.path.isdir(lic_dir) else []
    check(bool(lic), f"licenses/ 已发布（{lic}）")

    forbidden = ("Makefile", "debian", "src", "dependency_data")
    leaked = []
    for base in (share, os.path.join(share, "blends", BLEND)):
        leaked += [e for e in forbidden if os.path.exists(os.path.join(base, e))]
    check(not leaked, f"安装目录未混入构建系统/维护脚本（发现 {leaked}）")

    return finish()


def finish() -> int:
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
