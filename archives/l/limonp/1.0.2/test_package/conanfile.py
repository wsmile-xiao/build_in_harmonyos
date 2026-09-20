#!/usr/bin/env python3
"""Compile and run a limonp consumer against the OHOS package.

limonp 是 header-only：消费者只需要 `-I<package_folder>/include`，没有库可链。
六组断言全部写在 test_limonp.cpp 里，失败以退出码 2..7 区分。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class LimonpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["limonp"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")

        source = os.path.join(self.source_folder, "test_limonp.cpp")
        executable = os.path.join(self.build_folder, "test_limonp")

        # -pthread：组 6 用 bionic 的 std::thread，需要线程库。
        self.run(
            '"{}" -std=c++17 -O1 -I"{}" "{}" -pthread -o "{}"'.format(
                cxx,
                os.path.join(pkg.package_folder, "include"),
                source,
                executable,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
