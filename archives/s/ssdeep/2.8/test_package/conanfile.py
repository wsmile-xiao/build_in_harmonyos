#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/ssdeep/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SsdeepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # 注入被测包 CLI 路径（bin/ssdeep）给 HarmonyOS 专项测试
        # ssdeep-ohos-test.c（CMakeLists 通过 SSDEEP_CLI 传入 argv[1]）。
        cli_path = ""
        dep = self.dependencies.get("ssdeep")
        if dep and dep.package_folder:
            candidate = os.path.join(dep.package_folder, "bin", "ssdeep")
            if os.path.exists(candidate):
                cli_path = candidate
        cmake.configure(variables={"SSDEEP_CLI": cli_path})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_ssdeep')}", env="conanrun")
