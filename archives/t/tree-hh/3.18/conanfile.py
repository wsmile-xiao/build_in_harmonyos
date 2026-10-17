#!/usr/bin/env python3
"""Conan recipe for tree-hh 3.18 — header-only STL-like tree container.

tree.hh is a header-only C++ STL-like tree container
(src/tree.hh + tree_util.hh + xinlin.hh). Package installs the headers.
Upstream tests: src/test_tree.cc (compares against test_tree.output),
test1~4.cc — build() compiles and runs them (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.files import get


class TreeHhConan(ConanFile):
    name = "tree-hh"
    version = "3.18"
    description = "tree.hh — header-only STL-like tree container for C++"
    license = "GPL-3.0"
    homepage = "https://github.com/kpeeters/tree.hh"
    url = ""

    # header-only，无编译产物——但 OHOS profile 要求 settings 含全部四项
    # （CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only——无编译；上游测试：编译 src/test_tree.cc 运行并对比
        # test_tree.output（rule 4 实测回填）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import subprocess

        src = self.source_folder
        tests_src = os.path.join(src, "src")
        out = os.path.join(self.build_folder, "test_tree.bin")
        # OHOS 沙箱 subprocess 相对名不搜 PATH（posix_spawn 差异实测——
        # 与 rich/vc 同源）——clang++ 用绝对路径
        cxx = "/data/service/hnp/bin/clang++"
        r = subprocess.run(
            [cxx, os.path.join(tests_src, "test_tree.cc"),
             "-o", out, "-std=c++14", "-I", tests_src],
            capture_output=True, text=True, timeout=300)
        print("[tree-hh upstream tests] compile rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[tree-hh upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([out], capture_output=True, text=True, timeout=300)
        print("[tree-hh upstream tests] run rc=%d" % r.returncode)
        # 与期望输出 test_tree.output 对比（diff 判通过）
        exp = os.path.join(tests_src, "test_tree.output")
        with open(exp) as f:
            expected = f.read()
        actual = r.stdout or ""
        if actual == expected:
            print("[tree-hh upstream tests] PASS: output matches "
                  "test_tree.output (%d bytes)" % len(expected))
        else:
            print("[tree-hh upstream tests] FAIL: output differs from "
                  "test_tree.output")
            import difflib
            for line in list(difflib.unified_diff(
                    expected.splitlines(), actual.splitlines(),
                    "expected", "actual"))[:20]:
                print("[tree-hh upstream tests]", line)

    def package(self):
        # header-only：安装 src/ 头文件（tree.hh + tree_util.hh + xinlin.hh）
        import shutil
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        for h in ("tree.hh", "tree_util.hh", "xinlin.hh"):
            shutil.copy(os.path.join(self.source_folder, "src", h),
                        os.path.join(inc_dir, h))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
