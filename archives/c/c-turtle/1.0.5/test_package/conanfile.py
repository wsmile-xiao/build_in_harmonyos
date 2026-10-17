#!/usr/bin/env python3
"""Conan test_package — c-turtle 1.0.5 消费者验证（HarmonyOS L1 测试）。

消费者以业务上层组件视角使用 c-turtle：仅通过已安装的公开头 CTurtle.hpp
调用公开 API（TurtleScreen/Turtle/forward/right/xcor/ycor/write/bye），
headless 模式画正方形并验证 GIF 输出文件（R34：真实调用被测物，非空壳）。
"""
import os
from glob import glob

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CTurtleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def configure(self):
        self.settings.rm_safe("os.version")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.15"
        tc.generate()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        if self.settings.os == "OHOS":
            # C++ 测试二进制链接 libc++_shared.so，位于 OHOS native SDK 而非任何 conan 包
            sdk_lib = os.environ.get("OHOS_SDK_LIB")
            if not sdk_lib:
                candidates = glob(
                    "/data/service/hnp/ohos-sdk.org/*/"
                    "ohos/native/llvm/lib/aarch64-linux-ohos"
                )
                if candidates:
                    sdk_lib = candidates[0]
            if sdk_lib:
                os.environ["LD_LIBRARY_PATH"] = (
                    sdk_lib
                    + os.pathsep
                    + os.environ.get("LD_LIBRARY_PATH", "")
                )
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cturtle"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_fractal"), env="conanrun")