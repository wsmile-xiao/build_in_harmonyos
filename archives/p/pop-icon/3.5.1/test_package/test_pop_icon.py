#!/usr/bin/env python3
"""pop-icon 数据包验证脚本。

用法: python3 test_pop_icon.py <icons_root> <package_folder>

验证的是**图标主题本体**而不是"文件存在"：
  * 两套主题目录（Pop / Pop-Dark）必须各自带 index.theme —— 没有它，图标查找
    机制（gtk-update-icon-cache、XDG icon lookup）根本不会把目录当成主题；
  * `Pop/cursor.theme` 与 `Pop/cursors/`（296 个光标：140 个 .cur + 8 个 .ani +
    148 个无扩展名的 X11 光标）必须齐全，且逐个校验容器魔数；
  * 每个尺寸目录的文件数必须与上游一致（`16x16` 等目录少几个图标就是"部分图标
    消失"，比整包为空更难发现）；
  * 每一个 SVG 都必须是合法 XML 且根元素为 `svg`；
  * `index.theme` 的 `Directories=` 列表必须覆盖所有真正含图标的叶子目录
    （上游只漏了 `512x512/places` 与 `cursors` 两个，属于已知例外）；
  * 上游的渲染流水线（`src/`、`master-render.py`、`meson.build`、`debian/`）
    不得混进安装目录。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"

# 上游 tarball 内的条目总数（大小写敏感文件系统上的 tar 清单实测值）
UPSTREAM_ENTRIES = {"Pop": 6534, "Pop-Dark": 2262}

# 上游 tarball 里「大小写折叠后同名」的条目组（逐字取自 tar 清单）。
# OHOS /storage 用户区大小写不敏感：一组 n 个这样的名字只能落成 1 个目录项，
# 因此可交付条目数 = 上游条目数 − Σ(组内条目数 − 1) = 6534 − 8 = 6526。
# 每组给成 (主题内相对目录, 该组上游名字, 组内实体文件)；断言会验回每个名字
# 都还能被大小写不敏感地解析到、且内容与实体文件一致（别名语义没被丢掉）。
CASE_COLLISION_GROUPS = (
    *[(f"{d}/mimetypes", ("text-x-r.svg", "text-x-R.svg"), "text-x-r.svg")
      for d in ("16x16", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256")],
    ("scalable/apps",
     ("org.gnome.weather-symbolic.svg", "org.gnome.Weather-symbolic.svg"),
     "weather-symbolic.svg"),
)
COLLAPSED_ENTRIES = sum(len(names) - 1 for _d, names, _t in CASE_COLLISION_GROUPS)

# 每套主题：顶层目录 → 该目录下文件数（大小写不敏感文件系统上可交付的条目数）
EXPECTED_LAYOUT = {
    "Pop": {
        "8x8": 19, "16x16": 828, "24x24": 828, "32x32": 828, "48x48": 828,
        "64x64": 753, "128x128": 734, "256x256": 734, "512x512": 75,
        "scalable": 601, "cursors": 296,
    },
    "Pop-Dark": {"22x22": 1131, "24x24": 1130},
}
EXPECTED_FILES = {"Pop": 6526, "Pop-Dark": 2262}
EXPECTED_SVG = {"Pop": 6228, "Pop-Dark": 2261}
EXPECTED_CURSORS = {"cur": 140, "ani": 8, "no_extension": 148}
EXPECTED_DIRECTORIES_ENTRIES = 154
# 上游 index.theme 里唯一没覆盖到的两个叶子目录（已知例外，逐字固定）
UNLISTED_LEAF_EXCEPTIONS = {"512x512/places", "cursors"}
PIPELINE_ENTRIES = ("src", "meson.build", "meson", "master-render.py",
                    "debian", "svgo.config.js", "pop-icon-theme.spec",
                    "paper-icon-theme.doap", "index.theme.in",
                    "cursor.theme.in")

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def count_files(root):
    return sum(len(files) for _r, _d, files in os.walk(root))


def count_suffix(root, suffix):
    return sum(1 for _r, _d, files in os.walk(root) for f in files
               if f.endswith(suffix))


def scan_svgs(root):
    """返回 (解析失败列表, 根元素异常列表)，并统计 SVG 总数。"""
    bad_parse, bad_root, total = [], [], 0
    for base, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".svg"):
                continue
            total += 1
            path = os.path.join(base, name)
            try:
                elem = ET.parse(path).getroot()
            except ET.ParseError:
                bad_parse.append(os.path.relpath(path, root))
                continue
            if elem.tag != SVG_NS + "svg":
                bad_root.append(os.path.relpath(path, root))
    return total, bad_parse, bad_root


def is_cur(path):
    with open(path, "rb") as handle:
        head = handle.read(4)
    return len(head) == 4 and head[0] == 0 and head[1] == 0 and head[2] == 2


def is_ani(path):
    with open(path, "rb") as handle:
        head = handle.read(12)
    return len(head) == 12 and head[:4] == b"RIFF" and head[8:12] == b"ACON"


def casefold_index(dir_path):
    """目录项名（大小写折叠）→ 实际存储名。"""
    return {name.casefold(): name for name in os.listdir(dir_path)}


def check_case_collisions(theme_dir, rel_dirs):
    """验证大小写折叠同名组的别名语义。

    上游一组 n 个「大小写折叠后同名」的条目，在大小写不敏感的文件系统上只能
    落成 1 个目录项；这里逐个验证组内每个上游名字都仍能被大小写不敏感地解析
    到，并且内容与组内实体文件逐字节一致 —— 即别名代表的那张图标没有丢。
    """
    problems = []
    for rel_dir, names, target in CASE_COLLISION_GROUPS:
        if rel_dir not in rel_dirs:
            continue
        dir_path = os.path.join(theme_dir, rel_dir)
        if not os.path.isdir(dir_path):
            problems.append(f"{rel_dir}: 目录缺失")
            continue
        index = casefold_index(dir_path)
        stored_target = index.get(target.casefold())
        if stored_target is None:
            problems.append(f"{rel_dir}/{target}: 实体文件缺失")
            continue
        with open(os.path.join(dir_path, stored_target), "rb") as handle:
            target_bytes = handle.read()
        for name in names:
            stored = index.get(name.casefold())
            if stored is None:
                problems.append(f"{rel_dir}/{name}: 大小写不敏感查找不到")
                continue
            with open(os.path.join(dir_path, stored), "rb") as handle:
                if handle.read() != target_bytes:
                    problems.append(f"{rel_dir}/{name}: 内容与 {target} 不一致")
    return problems


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_pop_icon.py <icons_root> <package_folder>")
        return 2

    icons_root, package_folder = sys.argv[1], sys.argv[2]
    print(f"[test] icons_root = {icons_root}")
    check(os.path.isdir(icons_root), f"share/icons 目录存在 ({icons_root})")
    check(sorted(os.listdir(icons_root)) == ["Pop", "Pop-Dark"],
          f"share/icons 下只有两套主题（实际 {sorted(os.listdir(icons_root))}）")

    for theme, layout in EXPECTED_LAYOUT.items():
        theme_dir = os.path.join(icons_root, theme)
        if not check(os.path.isdir(theme_dir), f"{theme}/ 主题目录存在"):
            continue

        # index.theme 是"这个目录是不是一套主题"的唯一凭据
        index_path = os.path.join(theme_dir, "index.theme")
        if check(os.path.isfile(index_path), f"{theme}/index.theme 存在"):
            with open(index_path, encoding="utf-8", errors="replace") as handle:
                index_text = handle.read()
            check("[Icon Theme]" in index_text and "Name=" in index_text,
                  f"{theme}/index.theme 含 [Icon Theme] 段与 Name= 字段")
        else:
            index_text = ""

        # 顶层结构：目录集合必须与上游完全一致
        actual_dirs = sorted(d for d in os.listdir(theme_dir)
                             if os.path.isdir(os.path.join(theme_dir, d)))
        check(actual_dirs == sorted(layout),
              f"{theme}/ 顶层尺寸目录与上游一致（实际 {actual_dirs}）")

        per_dir = {d: count_files(os.path.join(theme_dir, d)) for d in actual_dirs}
        check(per_dir == layout,
              f"{theme}/ 各尺寸目录文件数与上游一致"
              f"（差异 {[(k, per_dir.get(k), layout.get(k)) for k in layout if per_dir.get(k) != layout[k]]}）")

        total = count_files(theme_dir)
        check(total == EXPECTED_FILES[theme],
              f"{theme}/ 文件总数 == {EXPECTED_FILES[theme]}（实际 {total}）")

        svg_total, bad_parse, bad_root = scan_svgs(theme_dir)
        check(svg_total == EXPECTED_SVG[theme],
              f"{theme}/ SVG 数量 == {EXPECTED_SVG[theme]}（实际 {svg_total}）")
        check(not bad_parse,
              f"{theme}/ 全部 SVG 均为合法 XML（失败 {bad_parse[:3]}）")
        check(not bad_root,
              f"{theme}/ 全部 SVG 根元素均为 svg（异常 {bad_root[:3]}）")

        # 尺寸目录必须留有 SVG（空的尺寸目录等于该尺寸的图标全丢）
        empty_dirs = [d for d in actual_dirs if d != "cursors"
                      and count_suffix(os.path.join(theme_dir, d), ".svg") == 0]
        check(not empty_dirs,
              f"{theme}/ 每个尺寸目录都含 SVG（空目录 {empty_dirs}）")

        if theme == "Pop":
            # 光标：cursor.theme + cursors/ 三种文件形态
            cursor_theme = os.path.join(theme_dir, "cursor.theme")
            check(os.path.isfile(cursor_theme)
                  and "[Icon Theme]" in open(cursor_theme, encoding="utf-8",
                                             errors="replace").read(),
                  "Pop/cursor.theme 存在且声明 [Icon Theme]")

            cursors_dir = os.path.join(theme_dir, "cursors")
            cur_files = [f for f in os.listdir(cursors_dir) if f.endswith(".cur")]
            ani_files = [f for f in os.listdir(cursors_dir) if f.endswith(".ani")]
            plain = [f for f in os.listdir(cursors_dir)
                     if "." not in f]
            check({"cur": len(cur_files), "ani": len(ani_files),
                   "no_extension": len(plain)} == EXPECTED_CURSORS,
                  f"Pop/cursors 的三种光标形态数量与上游一致"
                  f"（.cur {len(cur_files)} / .ani {len(ani_files)} / 无扩展名 {len(plain)}）")
            bad_cur = [f for f in cur_files
                       if not is_cur(os.path.join(cursors_dir, f))]
            check(not bad_cur,
                  f"全部 .cur 都是合法 CUR 容器（异常 {bad_cur[:3]}）")
            bad_ani = [f for f in ani_files
                       if not is_ani(os.path.join(cursors_dir, f))]
            check(not bad_ani,
                  f"全部 .ani 都是合法 RIFF/ACON 容器（异常 {bad_ani[:3]}）")

            # index.theme 的 Directories= 必须覆盖所有真正含图标的叶子目录
            match = re.search(r"^Directories=(.*)$", index_text, re.M)
            listed = {d.strip() for d in match.group(1).split(",")} if match else set()
            check(len(listed) == EXPECTED_DIRECTORIES_ENTRIES,
                  f"index.theme 的 Directories= 列 {EXPECTED_DIRECTORIES_ENTRIES} 项"
                  f"（实际 {len(listed)}）")

            leaves = set()
            for base, _dirs, files in os.walk(theme_dir):
                rel = os.path.relpath(base, theme_dir)
                if rel == ".":
                    continue
                if any(f.endswith((".svg", ".png", ".cur", ".ani")) for f in files):
                    leaves.add(rel)
            unlisted = sorted(leaves - listed)
            check(set(unlisted) == UNLISTED_LEAF_EXCEPTIONS,
                  f"含图标的叶子目录除已知例外外都被 index.theme 收录"
                  f"（未被收录 {unlisted}）")
            check(bool(leaves & listed),
                  f"index.theme 与真实目录有交集（{len(leaves)} 个叶子目录）")

            # 大小写折叠同名条目：可交付条目数 = 上游条目数 − 被折叠掉的名字数
            check(EXPECTED_FILES["Pop"] == UPSTREAM_ENTRIES["Pop"] - COLLAPSED_ENTRIES,
                  f"Pop/ 可交付条目数 = 上游 {UPSTREAM_ENTRIES['Pop']} 条 − 大小写折叠同名 "
                  f"{COLLAPSED_ENTRIES} 条 = {UPSTREAM_ENTRIES['Pop'] - COLLAPSED_ENTRIES}")

            mime_problems = check_case_collisions(
                theme_dir, {d for d, _n, _t in CASE_COLLISION_GROUPS
                            if d.endswith("/mimetypes")})
            check(not mime_problems,
                  f"7 个 Pop/<N>x<N>/mimetypes 的大小写别名（text-x-R.svg）仍可解析"
                  f"且与实体 text-x-r.svg 一致（问题 {mime_problems[:3]}）")

            apps_problems = check_case_collisions(theme_dir, {"scalable/apps"})
            check(not apps_problems,
                  f"Pop/scalable/apps 的两条 GNOME 大小写别名仍可解析"
                  f"且与 weather-symbolic.svg 一致（问题 {apps_problems[:3]}）")

    # ── 渲染流水线不得混进安装目录 ──────────────────────────────────────
    leaked = []
    for theme in EXPECTED_LAYOUT:
        theme_dir = os.path.join(icons_root, theme)
        leaked += [f"{theme}/{e}" for e in PIPELINE_ENTRIES
                   if os.path.exists(os.path.join(theme_dir, e))]
    check(not leaked,
          f"安装目录未混入上游渲染流水线（发现 {leaked}）")
    check(not os.path.exists(os.path.join(icons_root, "src")),
          "上游 src/（SVG 源稿）未安装")

    # ── 许可证 ─────────────────────────────────────────────────────────
    lic_dir = os.path.join(package_folder, "licenses")
    lic_files = sorted(os.listdir(lic_dir)) if os.path.isdir(lic_dir) else []
    check(lic_files == ["AUTHORS", "COPYING", "LICENSE"],
          f"licenses/ 含 AUTHORS + COPYING + LICENSE（实际 {lic_files}）")

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
