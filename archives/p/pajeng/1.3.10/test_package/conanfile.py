#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

Consumer test for pajeng: links libpaje (PajeColor API assertions) and runs
the packaged pj_dump tool against a bundled upstream trace sample.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PajengTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        dep = self.dependencies["pajeng"]
        cmake.configure(variables={"PJ_DUMP_BIN": os.path.join(
            dep.cpp_info.bindirs[0], "pj_dump")})
        cmake.build()

    def test(self):
        # 直接执行消费者测试程序；musl 忽略 DT_RUNPATH，运行前显式补
        # libpaje 库路径（conanrunenv 之外再兜底一层）
        dep = self.dependencies["pajeng"]
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            [dep.cpp_info.libdirs[0]] + ([prev] if prev else []))
        self.run(os.path.join(self.build_folder, "test_pajeng"))
