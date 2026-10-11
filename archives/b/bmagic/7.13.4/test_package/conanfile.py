#!/usr/bin/env python3
"""Conan test_package — bmagic 7.13.4 (消费者验证)

E225: 使用 cmake_layout(build_folder="$TMP") 让 Conan 管理每次调用唯一临时构建根，
并在 generate() 关闭 user_presets_path，阻止 CMakeToolchain 向 source 写入
CMakeUserPresets.json（零 source 生成物，标准 conan create 可直接运行）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BmagicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        # Ninja 直接派生编译命令，绕开 HMMAC 对 CMake "Unix Makefiles"
        # try-compile 中 /bin/sh exec 的拒绝（同仓 physunits-ct/0.1.0 先例）。
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        tc = CMakeToolchain(self)
        # 设备 CMake 4.1 不识别 OHOS 适配版 Conan 映射出的 HarmonyOS 系统名，
        # Linux 平台语义一致（同仓 physunits-ct/0.1.0 先例）。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # 直接运行 CMake 构建出的消费者测试二进制（真实执行被测 API 断言）
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_bmagic"),
                     env="conanrun")
