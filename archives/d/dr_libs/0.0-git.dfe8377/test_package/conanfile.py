#!/usr/bin/env python3
"""Conan test_package — dr_libs 0.0-git.dfe8377 (consumer smoke test).

消费者测试：在同一翻译单元编译三个头的实现段（三头共存编译验证），
并用 dr_wav 做内存写读往返断言（写 8kHz/1ch/16-bit/440 帧 ramp →
读回校验格式参数与样本值）。纯内存操作，无文件系统/设备依赖。
非空壳、非仅 include。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DrLibsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2 precedent).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_dr_libs")
            self.run(f'"{executable}"', env="conanrun")
