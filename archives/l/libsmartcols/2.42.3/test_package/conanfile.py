#!/usr/bin/env python3
"""Test package for libsmartcols 2.42.3 on HarmonyOS PC.

Consumer verification (R34): compile a C program that really exercises
the libsmartcols table API (scols_new_table / scols_table_new_column /
scols_table_new_line / scols_line_sprintf / scols_print_table), then
run it and check the rendered output contains the expected cells.
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["libsmartcols"].package_folder
        src = os.path.join(os.path.dirname(__file__), "test_smartcols.c")
        exe = "/data/storage/el2/base/cache/smartcols-tp-test"
        self.run(
            f"/data/service/hnp/bin/clang '{src}' "
            f"-I'{pkg}/include' -L'{pkg}/lib' -lsmartcols -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
