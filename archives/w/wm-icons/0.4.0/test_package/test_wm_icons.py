#!/usr/bin/env python3
"""wm-icons 数据包验证脚本。

用法: python3 test_wm_icons.py <data_dir> <package_folder>

验证的是**图标资源本体**而不是"文件存在"：

  * `names.lst` 是上游的**标准化图标名清单**（84 个名字）——31 个图标集各自
    实现它的一个子集。断言三件事：清单本身无重复、**所有集合的并集覆盖全部
    84 个名字**（否则整类的图标在系统里都没有对应实现）、`16x16-kde` 这一个
    集合完整实现全部 84 个名字（上游最全的集合，用来发现整体被裁剪）；
  * 每个集合的文件数与上游**逐字一致**（31 个集合的 `{目录: 文件数}` 映射）；
  * 每个集合都带自己的 `_symlinks.lst`（语义名 → 具体文件的软链定义）；
  * 828 个 PNG 逐个校验 PNG 魔数；1210 个 XPM 逐个校验 `/* XPM */` 头；
  * 安装目录里不能混进构建系统（`Makefile.am` / `configure` / `config.guess`）
    或面向其它窗口管理器的 `etc/` rc 模板。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import os
import sys

# 31 个图标集 → 文件数（上游固定值，含各集合自己的 _symlinks.lst）
EXPECTED_SETS = {
    "01x01-template": 2, "14x14-general": 83, "16x16-aquafusion": 71,
    "16x16-crystalclear": 85, "16x16-general": 83, "16x16-gnome": 73,
    "16x16-kde": 85, "17x14-3dpixmaps": 71, "20x20-martys": 30,
    "20x20-martys2": 21, "21x18-3dpixmaps": 71, "22x22-aquafusion": 71,
    "22x22-gartoon": 77, "24x24-infox": 66, "32x32-aquafusion": 71,
    "32x32-gant": 81, "32x32-kde": 79, "32x32-kde2": 79,
    "44x52-penguins": 57, "48x48-aquafusion": 71, "48x48-crystalclear": 84,
    "48x48-gartoon": 77, "48x48-general": 68, "48x48-gnome": 69,
    "48x48-infox": 66, "48x48-kde2": 64, "56x46-3dpixmaps": 71,
    "56x56-martys": 46, "56x56-martys2": 46, "64x64-aquafusion": 71,
    "64x64-gant": 80,
}
EXPECTED_NAMES = 84
EXPECTED_TOTAL_FILES = 2069
EXPECTED_PNG = 828
EXPECTED_XPM = 1210
# 完整实现全部 84 个标准名的集合
COMPLETE_SET = "16x16-kde"
FORBIDDEN_IN_DATA = ("Makefile.am", "Makefile.in", "configure", "configure.in",
                     "config.guess", "config.sub", "aclocal.m4", "etc", "bin",
                     "rpm", "devel")

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def read_names(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return [line.strip() for line in handle
                if line.strip() and not line.startswith("#")]


def is_png(path):
    with open(path, "rb") as handle:
        return handle.read(8) == b"\x89PNG\r\n\x1a\n"


def is_xpm(path):
    with open(path, "rb") as handle:
        return handle.read(9) == b"/* XPM */"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_wm_icons.py <data_dir> <package_folder>")
        return 2

    data_dir, package_folder = sys.argv[1], sys.argv[2]
    print(f"[test] data_dir = {data_dir}")
    check(os.path.isdir(data_dir), f"share/wm-icons 目录存在 ({data_dir})")

    # ── 1. 图标集集合与逐集文件数 ───────────────────────────────────────
    actual_sets = {d: len(os.listdir(os.path.join(data_dir, d)))
                   for d in os.listdir(data_dir)
                   if os.path.isdir(os.path.join(data_dir, d))}
    check(sorted(actual_sets) == sorted(EXPECTED_SETS),
          f"图标集目录集合与上游一致（{len(actual_sets)} 个）")
    diff = [(k, actual_sets.get(k), EXPECTED_SETS[k]) for k in EXPECTED_SETS
            if actual_sets.get(k) != EXPECTED_SETS[k]]
    check(not diff,
          f"每个图标集的文件数与上游逐字一致（差异 {diff[:4]}）")
    total_files = sum(actual_sets.values())
    check(total_files == EXPECTED_TOTAL_FILES,
          f"图标集文件总数 == {EXPECTED_TOTAL_FILES}（实际 {total_files}）")

    # ── 2. 每集自带 _symlinks.lst ──────────────────────────────────────
    missing_links = [s for s in EXPECTED_SETS
                     if not os.path.isfile(os.path.join(data_dir, s, "_symlinks.lst"))]
    check(not missing_links,
          f"每个图标集都带 _symlinks.lst（缺失 {missing_links[:4]}）")

    # ── 3. 标准化图标名清单 ────────────────────────────────────────────
    names_path = os.path.join(data_dir, "names.lst")
    if not check(os.path.isfile(names_path), "names.lst 存在"):
        names = []
    else:
        names = read_names(names_path)
        check(len(names) == EXPECTED_NAMES,
              f"names.lst 列出 {EXPECTED_NAMES} 个标准图标名（实际 {len(names)}）")
        check(len(set(names)) == len(names), "标准图标名无重复")
        check(all("." not in n for n in names),
              "标准图标名不带扩展名（扩展名由各集合自行选择 PNG/XPM）")

    # ── 4. 并集覆盖 + 完整集合 ─────────────────────────────────────────
    union = set()
    for s in EXPECTED_SETS:
        directory = os.path.join(data_dir, s)
        if os.path.isdir(directory):
            union |= {os.path.splitext(f)[0] for f in os.listdir(directory)}
    uncovered = [n for n in names if n not in union]
    check(not uncovered,
          f"所有集合的并集覆盖全部标准图标名（未覆盖 {uncovered[:5]}）")

    complete_dir = os.path.join(data_dir, COMPLETE_SET)
    if os.path.isdir(complete_dir):
        have = {os.path.splitext(f)[0] for f in os.listdir(complete_dir)}
        missing = [n for n in names if n not in have]
        check(not missing,
              f"{COMPLETE_SET} 完整实现全部 {EXPECTED_NAMES} 个标准名"
              f"（缺 {missing[:5]}）")

    # ── 5. 逐个图像的容器魔数 ──────────────────────────────────────────
    pngs, xpms, bad = [], [], []
    for s in EXPECTED_SETS:
        directory = os.path.join(data_dir, s)
        if not os.path.isdir(directory):
            continue
        for entry in os.listdir(directory):
            path = os.path.join(directory, entry)
            if entry.endswith(".png"):
                pngs.append(path)
                if not is_png(path):
                    bad.append(f"{s}/{entry}")
            elif entry.endswith(".xpm"):
                xpms.append(path)
                if not is_xpm(path):
                    bad.append(f"{s}/{entry}")
            elif not entry.endswith(".lst"):
                bad.append(f"{s}/{entry}")
    check(len(pngs) == EXPECTED_PNG,
          f"PNG 数量 == {EXPECTED_PNG}（实际 {len(pngs)}）")
    check(len(xpms) == EXPECTED_XPM,
          f"XPM 数量 == {EXPECTED_XPM}（实际 {len(xpms)}）")
    check(not bad,
          f"全部图像的容器头合法（PNG 魔数 / XPM '/* XPM */'），且无第三种文件（异常 {bad[:3]}）")

    # ── 6. 文档与许可 ──────────────────────────────────────────────────
    docs_dir = os.path.join(package_folder, "share", "doc", "wm-icons")
    docs = sorted(os.listdir(docs_dir)) if os.path.isdir(docs_dir) else []
    check("FAQ" in docs and "icons.lst" in docs and any(d.startswith("README") for d in docs),
          f"share/doc/wm-icons 随包发布（{docs}）")
    lic_dir = os.path.join(package_folder, "licenses")
    lic = os.path.join(lic_dir, "COPYING")
    check(os.path.isfile(lic) and b"GNU GENERAL PUBLIC LICENSE" in open(lic, "rb").read(4096),
          "licenses/COPYING 已发布且写明 GPL")

    # ── 7. 安装纯净性 ──────────────────────────────────────────────────
    leaked = [e for e in FORBIDDEN_IN_DATA if os.path.exists(os.path.join(data_dir, e))]
    check(not leaked,
          f"安装目录未混入构建系统 / 其它 WM 的 rc 模板（发现 {leaked}）")
    others = sorted(e for e in os.listdir(data_dir)
                    if e != "names.lst" and not os.path.isdir(os.path.join(data_dir, e)))
    check(not others,
          f"share/wm-icons 下只有图标集目录与 names.lst（发现 {others}）")

    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        print("FAILED assertions:")
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
