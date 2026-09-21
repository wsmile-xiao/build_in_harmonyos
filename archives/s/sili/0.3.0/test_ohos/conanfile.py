#!/usr/bin/env python3
# HarmonyOS-specific test runner — sili/0.3.0
#
# Independent of test_package (library API): builds ohos_test.c against the
# FINAL Conan package through CMakeDeps (like a downstream project would),
# then runs the binary on the target. Validates OHOS delivery paths:
# thread create/run/join, time APIs, environment-variable round-trip,
# CPU count, and string conversion/trimming.
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestOHOS(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        tested = getattr(self, "tested_reference", None)
        if tested is None:
            # conan test <path> <ref> injects the reference; when it is not
            # available during graph computation, the recipe's declared
            # fallback below is used.
            tested = "sili/0.3.0@ohpcd/stable"
        self.requires(tested)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanException("test_ohos must run on the OHOS profile")
        # 绝对路径运行：cmake_layout 下可执行文件位于 build_folder 顶层，
        # 不能依赖 PATH/相对路径（conanrun 环境的 sh 找不到裸文件名）。
        exe = Path(self.build_folder) / "test_ohos_sili"
        self.run(f'"{exe}"', env="conanrun")
