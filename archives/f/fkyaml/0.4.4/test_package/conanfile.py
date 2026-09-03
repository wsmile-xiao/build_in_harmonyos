#!/usr/bin/env python3
"""test_package for fkyaml 0.4.4 — real consumer (CMake + fkYAML::fkYAML)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class FkYamlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # Real consumer binary: deserialize/iterate/serialize/exception paths.
            self.run(os.path.join(self.cpp.build.bindir, "test_package"), env="conanrun")
            # HarmonyOS 专项测试：独立可执行 target，单独运行（与 test_package 分离）。
            self.run(os.path.join(self.cpp.build.bindir, "ohos_specific_test"), env="conanrun")