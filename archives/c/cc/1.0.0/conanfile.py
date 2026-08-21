#!/usr/bin/env python3
"""Conan recipe for cc 1.0.0 on HarmonyOS PC.

cc (Convenient Containers) is a single-header C library providing
generic containers (vector/list/map/set/omap/oset/string) via macro
templates. Header-only, zero external deps — package just cc.h.

Upstream ships tests/unit_tests.c (C unit tests for each container)
and tests/tests_against_stl.cpp (C++/STL parity) — the C unit tests
are compiled and run in test_package for real (R34/L0c).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class CcConan(ConanFile):
    name = "cc"
    version = "1.0.0"
    package_type = "header-library"
    license = "MIT"
    homepage = "https://github.com/JacksonAllan/CC"
    url = "https://github.com/JacksonAllan/CC"
    description = ("Convenient Containers — single-header generic C "
                   "containers (vector/list/map/set)")
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        # header-only：无编译（测试在 test_package 编译运行）
        pass

    def package(self):
        copy(self, "cc.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
