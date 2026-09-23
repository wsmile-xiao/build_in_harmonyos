#!/usr/bin/env python3
"""Conan test_package for cotila 1.2.1 — consumer-side verification of the
header-only library.  CI runs this automatically via `conan create`."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CotilaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS profile carries os.version; the header-only test needs no
        # version-specific packaging ID (repo rang/mdurl pattern).
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS: CMake does not know the OHOS platform; map to Linux
        # (repo rang/range-v3 pattern) and force libc++ (OHOS clang
        # only ships libc++).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.extra_cxxflags.append("-stdlib=libc++")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        # 1) 消费者测试：constexpr static_assert + 运行期断言
        self.run(os.path.join(bindir, "test_cotila"), env="conanrun")
        # 2) 上游官方测试套件（76 条编译期 static_assert，编译即通过；
        #    运行打印确认）——上游测试零修改
        self.run(os.path.join(bindir, "cotila_upstream_tests"),
                 env="conanrun")
