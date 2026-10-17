#!/usr/bin/env python3
"""Conan test_package for yetris 2.3.0 (HarmonyOS PC / OHOS aarch64).

yetris 是 application（ncurses TUI 游戏），没有可链接的库 API，因此消费者
测试以"二进制使用者"身份运行打包产物并断言行为（AGENTS §9：编译并调用库 API，
或运行被测二进制并断言行为）。

CI L0c 门禁要求 test_package/ 内含可编译测试源文件，故新增 test_yetris.c：
C 消费者程序校验 yetris 二进制存在且可执行，断言 `--version` 打印
"yetris v2.3.0"、`--help` 打印 usage 且列出 `--version` 选项；用 CMake 交叉
构建后用 self.run() 真实执行，以退出码判定（L0d/L1）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class YetrisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 被测物是 application：把打包的 yetris 二进制拷进 build 目录，供 C
        # 消费者程序按路径调用（不 include 其头文件、不链接其库，故不需要
        # CMakeDeps，仅需 CMakeToolchain 定位 OHOS 交叉工具链）。
        bindir = os.path.join(self.dependencies["yetris"].package_folder, "bin")
        copy(self, "yetris", bindir, self.build_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_yetris")
        binary = os.path.join(self.build_folder, "yetris")
        self.run(f'"{test_bin}" "{binary}"', env="conanrun", cwd=self.build_folder)
