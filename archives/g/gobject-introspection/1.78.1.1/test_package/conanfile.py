#!/usr/bin/env python3
"""Conan test_package for gobject-introspection — GI 基础设施验证（L1）。

调用独立测试源 test_gi.py（L0c 要求）校验 .typelib 与 g-ir 工具链，
并实际运行 g-ir-compiler。用 self.run（L0d 要求）。
"""
import os

from conan import ConanFile


class GobjectIntrospectionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["gobject-introspection"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        test_gi = os.path.join(os.path.dirname(__file__), "test_gi.py")
        # 1) 独立测试源（test_gi.py）校验 typelib + 工具链
        self.run(f"python3 '{test_gi}' '{pkg}'")
        # 2) g-ir-compiler 实际运行（--version 消费库）——运行时需 glib+libintl
        #    libdir 在 LD_LIBRARY_PATH（g-ir-compiler 链 gobject/glib；libintl 置首位
        #    兼容双符号）
        glib_lib = ""
        intl_lib = ""
        import glob
        for _dep in self.dependencies.values():
            if _dep.package_folder and str(_dep.ref).startswith("glib/"):
                glib_lib = os.path.join(_dep.package_folder, "lib")
            elif _dep.package_folder and str(_dep.ref).startswith("libintl/"):
                intl_lib = os.path.join(_dep.package_folder, "lib")
        ldd = ":".join(x for x in (intl_lib, os.path.join(pkg, "lib"), glib_lib) if x)
        self.run(f"LD_LIBRARY_PATH='{ldd}' '{bin_dir}/g-ir-compiler' --version")
        self.output.info("[PASS] g-ir-compiler runs")
