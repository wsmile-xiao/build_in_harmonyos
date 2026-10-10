#!/usr/bin/env python3
"""ooxml 1.13.1 交付形态自检（M，非上游用例）。

校验 TEA 布局与纯净性：lib/ooxml1.13.1/ 下的运行期脚本 + pkgIndex.tcl、
pkgIndex 注册版本 1.13.1、ooxml.tcl 非空壳、license.terms、无 bin/
（纯 Tcl 无可执行文件 → 无需 commands.json）、无 usr/ 前缀、无构建中间
产物、无隐藏文件（JC5）、未夹带上游 tests/ 与 doc/。
"""
import os
import sys

failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS %s" % name)
    else:
        failures.append(name)
        print("FAIL %s %s" % (name, detail))


def main(pkg_root):
    tea = os.path.join(pkg_root, "lib", "ooxml1.13.1")
    check("M1  TEA 目录存在", os.path.isdir(tea), tea)

    for name in ("ooxml.tcl", "ooxml-docx.tcl", "ooxml-docx-lib.tcl",
                 "ooxml-docx-math.tcl", "pkgIndex.tcl"):
        path = os.path.join(tea, name)
        ok = os.path.isfile(path) and os.path.getsize(path) > 0
        check("M2  %s 非空" % name, ok)

    with open(os.path.join(tea, "pkgIndex.tcl"), encoding="utf-8") as fh:
        idx = fh.read()
    check("M3  pkgIndex 注册 1.13.1", "package ifneeded ooxml 1.13.1" in idx)
    check("M4  pkgIndex 注册 docx 0.6", "ooxml::docx 0.6" in idx)
    check("M5  pkgIndex 无模板占位符", "@PACKAGE_" not in idx)

    with open(os.path.join(tea, "ooxml.tcl"), encoding="utf-8") as fh:
        lib = fh.read()
    check("M6  ooxml.tcl 实质内容（xl_write/xl_read）",
          "oo::class create ooxml::xl_write" in lib and "proc ::ooxml::xl_read" in lib)

    check("M7  license.terms", os.path.isfile(os.path.join(pkg_root, "licenses", "license.terms")))
    check("M8  无 bin/（无 commands.json 义务）", not os.path.isdir(os.path.join(pkg_root, "bin")))
    check("M9  无 usr/ 前缀泄漏", not os.path.exists(os.path.join(pkg_root, "usr")))

    allowed_top = {"lib", "licenses", "conaninfo.txt", "conanmanifest.txt"}  # conan 元数据文件
    top = set(os.listdir(pkg_root))
    check("M10 顶层只有 lib/ licenses/", top <= allowed_top, str(top - allowed_top))

    for dirpath, dirnames, filenames in os.walk(pkg_root):
        for fn in filenames:
            if fn.startswith("."):
                failures.append("M11 隐藏文件 %s" % fn)
                print("FAIL M11 隐藏文件 %s" % os.path.join(dirpath, fn))
    check("M11 无隐藏文件", not any(f.startswith("M11") for f in failures))

    check("M12 未夹带上游 tests/", not any("tests" in os.path.relpath(
        os.path.join(d, f), pkg_root).split(os.sep)
        for d, _, fs in os.walk(pkg_root) for f in fs))

    print("----")
    if failures:
        print("layout-test: failed=%d" % len(failures))
        sys.exit(1)
    print("layout-test: all checks passed")
    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
