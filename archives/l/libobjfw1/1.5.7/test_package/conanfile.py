#!/usr/bin/env python3
"""Conan consumer test for libobjfw1 1.5.7 — ObjFW runtime API 冒烟（纯 C）.

L0c 门禁要求 test_package 含 .c 测试源；ObjFW 框架的 ObjC 类用例
（test_objfw.m）需 -fobjc（OHOS clang 不认），故消费者验证用纯 C
runtime API（ObjFWRT.h，libobjfw1 包随附）。
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libobjfw1"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_objfw_c.c")
        # objc_* runtime 符号在 libobjfwrt.a（libobjfw1 包 --enable-runtime 随装），
        # 需先链 -lobjfwrt 再 -lobjfw（CI #49736 undefined symbol 修复）
        self.run(
            f"{cc} -std=c11 -o test_objfw_c {src} "
            f"-I{pkg}/include -L{pkg}/lib -lobjfwrt -lobjfw -lm -lpthread -ldl",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_objfw_c", env="conanrun")
