# -*- coding: utf-8 -*-
"""v12.21 构建系统普查落地验证：headeronly 模板/分类器/文档四节"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from ohc.recipe_search import _features_from_conanfile  # noqa: E402

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def test_template():
    t = REPO / "templates" / "conanfile-headeronly.py.tmpl"
    check("模板存在", t.is_file())
    if t.is_file():
        v = t.read_text(encoding="utf-8")
        check("三变体注释块", all(x in v for x in ["变体 A", "变体 B", "变体 C"]))
        check("package_id 清空", "self.info.clear()" in v)
        check("R34/R51 提示", "R34" in v and "R51" in v)
        check("占位符齐全", all(x in v for x in ["{NAME}", "{name}", "{version}"]))


def test_registered():
    for f, marker in [("conan_recipe.py", '"headeronly": "conanfile-headeronly.py.tmpl"'),
                      ("init_archive.py", '"headeronly": "conanfile-headeronly.py"')]:
        v = (REPO / "scripts" / "ohc" / f).read_text(encoding="utf-8")
        check(f"{f} 注册", marker in v)


def test_classifier():
    headeronly = 'from conan import ConanFile\n\nclass X(ConanFile):\n    def package_id(self):\n        self.info.clear()\n'
    copy_pkg = 'from conan import ConanFile\n\nclass X(ConanFile):\n    def package(self):\n        copy(self, "*.ttf")\n'
    cmake = 'from conan.tools.cmake import CMake\n'
    raw_make = 'class X(ConanFile):\n    def build(self):\n        self.run("make -j8")\n'
    check("headeronly 分类", _features_from_conanfile(headeronly)["build_system"] == "headeronly")
    check("copy 分类", _features_from_conanfile(copy_pkg)["build_system"] == "copy")
    check("cmake 不受影响", _features_from_conanfile(cmake)["build_system"] == "cmake")
    check("裸 make 仍 unknown（不误吞）",
          _features_from_conanfile(raw_make)["build_system"] == "unknown")


def test_catalog():
    rows = [l.split("\t") for l in
            (REPO / "knowledge/recipes/catalog.tsv").read_text(encoding="utf-8").splitlines()
            if not l.startswith("#") and l.strip()]
    bs = [r[2] for r in rows if len(r) == 7]
    check("catalog 含 headeronly", bs.count("headeronly") >= 100)
    check("catalog 含 copy", bs.count("copy") >= 300)


def test_docs():
    v = (REPO / "knowledge/operations/build-systems.md").read_text(encoding="utf-8")
    check("四节在位", all(x in v for x in
          ["## 11. Meson 适配详解", "## 12. 无构建/打包族",
           "## 13. QMake", "## 14. Python C 扩展"]))
    check("§1 表格补行", "无构建/打包族" in v and "Python C 扩展" in v)
    sk = (REPO / "SKILL.md").read_text(encoding="utf-8")
    check("SKILL v12.21 日志", "*SKILL.md v12.21 — 2026-09-03" in sk)
    ct = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    check("CONTRIBUTING 对齐 v12.21", ct.count("v12.21") == 3)


if __name__ == "__main__":
    for fn in (test_template, test_registered, test_classifier, test_catalog, test_docs):
        print(f"== {fn.__name__} ==")
        fn()
    print(f"\nv12.21 build-system tests: {PASS} pass, {FAIL} fail")
    sys.exit(1 if FAIL else 0)
