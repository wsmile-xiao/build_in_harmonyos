#!/usr/bin/env python3
"""Conan test_package — neovim-qt 0.2.19 L1 test.

L1 test:
1. 编译并运行 test.cpp——链接 Qt5Core/Network/Widgets（nvim-qt 的 Qt5
   依赖面）验证 Qt5 运行时可用；
2. QT_QPA_PLATFORM=offscreen 运行 nvim-qt --version 验证应用可执行
   （鸿蒙无 X11/Wayland，offscreen 平台规避显示服务器需求）。
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block


class NeovimQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt5Config.cmake 位于 qtbase 包 lib/cmake/Qt5/（CMakeDeps 不生成
        # 聚合 Qt5 config），声明 qtbase 以在 generate() 中取包路径
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # 与主配方一致：CMake 无 Platform/HarmonyOS.cmake，呈现为 Linux
        # 并置 CMAKE_CROSSCOMPILING=FALSE（鸿蒙 clang 驱动仍目标
        # aarch64-linux-ohos）。
        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock

        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        qtsvg_pkg = self.dependencies["qt5-qtsvg"].package_folder
        tc.cache_variables.update(
            {
                # 上游 find_package(QT NAMES Qt5) 需要 qtbase 包的
                # Qt5Config.cmake 聚合配置 + qtsvg 包的 Qt5Svg
                "CMAKE_PREFIX_PATH": f"{qtbase_pkg};{qtsvg_pkg}",
            }
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # C++ 消费者测试：Qt5 Core/Network/Widgets 链接 + 运行时初始化
        test_exe = os.path.join(self.cpp.build.bindir, "test_neovim_qt")
        self.run(f"QT_QPA_PLATFORM=offscreen {test_exe}", env="conanrun")
        # 应用验证：nvim-qt --version（offscreen 平台）
        nvim_qt = os.path.join(
            self.dependencies["neovim-qt"].package_folder, "bin", "nvim-qt")
        self.run(f"test -x {nvim_qt}")
        self.run(f"QT_QPA_PLATFORM=offscreen {nvim_qt} --version", env="conanrun")
