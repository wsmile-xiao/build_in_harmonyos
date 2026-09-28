#!/usr/bin/env python3
"""Conan test_package — AusweisApp 2.5.4 鸿蒙特有测试 (R34: 真实执行目标程序).

AusweisApp 是 Qt6 GUI 应用 (package_type = "application")，不导出可被消费者
链接的 C 库 API，因此 test_package 编译一个 test_ausweisapp 宿主程序，由它
真实执行打包产物 `AusweisApp --version` 并校验退出码/版本输出
（详见 test.c，R34 实质测试，非空壳 printf）。

注意：不在 CMake 中 find_package(ausweisapp)。AusweisApp 的 Qt 依赖
（qtbase/qtwebsockets 等）均为 cmake_find_mode=none，CMakeDeps 生成的
config 会对每个传递依赖调用 find_dependency()，导致 qtwebsockets 等解析
失败（CI #59589 即因此失败）。故只编译宿主测试程序，经 configure variable
传入产物路径。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class AusweisappTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 把打包产物路径传给 test.c (AUSWEISAPP_BIN 宏)。
        pkg = self.dependencies["ausweisapp"].package_folder
        cmake = CMake(self)
        cmake.configure(variables={
            "AUSWEISAPP_BIN": os.path.join(pkg, "bin", "AusweisApp"),
        })
        cmake.build()

    def test(self):
        # 真实测试（非桩）：运行宿主测试程序，其内部 popen 执行
        # AusweisApp --version 并验证退出码 0 且输出含版本号。
        # env="conanrun" 注入依赖运行库路径 (VirtualRunEnv)。
        #
        # QT_QPA_PLATFORM=offscreen：AusweisApp 是 Qt6 GUI 应用，其 main()
        # 在解析 --version 前就会构造 QGuiApplication；CI 沙箱无显示且无
        # xcb/wayland 平台插件，必须用 offscreen 平台才能无头启动
        # （与主配方 antest 的 ctest 环境一致，CI #60057 即因缺此变量
        # 导致 QGuiApplication 初始化失败、--version 非 0 退出）。
        test_env = Environment()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ausweisapp")
        with test_env.vars(self).apply():
            self.run(test_bin, env="conanrun")
