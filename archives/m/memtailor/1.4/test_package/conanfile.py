#!/usr/bin/env python3
"""Compile and run a memtailor consumer against the OHOS package.

memtailor 是普通静态库：消费者需要 `-I<include 根>`（伞头文件 memtailor.h 与
memtailor/ 目录树在同一根下）加 `-L<lib> -lmemtailor`，并链接 pthread
（上游 `target_link_libraries(memtailor Threads::Threads)`）。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class MemtailorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["memtailor"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")

        source = os.path.join(self.source_folder, "test_memtailor.cpp")
        executable = os.path.join(self.build_folder, "test_memtailor")

        self.run(
            '"{}" -std=c++17 -O1 -I"{}" "{}" -L"{}" -lmemtailor -pthread -o "{}"'.format(
                cxx,
                os.path.join(pkg.package_folder, "include"),
                source,
                os.path.join(pkg.package_folder, "lib"),
                executable,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
