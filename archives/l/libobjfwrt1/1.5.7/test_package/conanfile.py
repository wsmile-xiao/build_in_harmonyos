#!/usr/bin/env python3
"""Conan consumer test for libobjfwrt1 1.5.7 — ObjFW runtime objc_* API 冒烟。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libobjfwrt1"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_objfwrt.c")
        # ObjFW runtime 是纯 C API（ObjFWRT.h），无需 -fobjc（OHOS clang 不认）
        self.run(
            f"{cc} -std=c11 -o test_objfwrt {src} "
            f"-I{pkg}/include -L{pkg}/lib -lobjfwrt -lm -lpthread -ldl",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_objfwrt", env="conanrun")
