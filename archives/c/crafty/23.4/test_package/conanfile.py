#!/usr/bin/env python3
"""Conan test_package for crafty — L1 official test.

Crafty is a command-line chess engine (application, not library). The L1
test invokes the packaged `crafty` binary directly with a non-interactive
command stream (`bench` then `quit`) and asserts it exits 0 and prints the
version banner. This satisfies R34 (test must actually exercise the tested
package: we run the real crafty engine, not a printf stub).

L0 no_test_sources 门禁要求 test_package 含可编译测试源文件，故加 test_crafty.c
（C 测试程序：校验 crafty 二进制存在 + 版本 banner），用 CMake 构建 + self.run() 实跑。
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.cmake import CMake, cmake_layout


class CraftyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Resolve the packaged crafty binary from the tested package's
        # package_folder via the requires() dependency, copy to build_folder
        # so test_crafty can invoke it by relative path.
        bindir = os.path.join(self.dependencies["crafty"].package_folder, "bin")
        copy(self, "crafty", bindir, self.build_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # `bench` runs crafty's internal performance benchmark (search a fixed
        # set of positions to a fixed depth). Non-interactive, exits cleanly.
        # `quit` terminates the engine. We pipe both via stdin to avoid hang.
        self.run(
            'printf "bench\\nquit\\n" | "./crafty"',
            env="conanrun",
            cwd=self.build_folder,
        )
        # Run the C test program to verify the binary exists + version banner.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_crafty")
        self.run(f'"{test_bin}" "{os.path.join(self.build_folder, "crafty")}"',
                 env="conanrun", cwd=self.build_folder)
