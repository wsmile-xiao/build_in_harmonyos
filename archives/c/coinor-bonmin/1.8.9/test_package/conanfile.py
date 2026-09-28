#!/usr/bin/env python3
"""Conan test_package — coinor-bonmin 1.8.9（conan create 内联的 L1 消费者测试）

两个消费者程序都真实链接已安装的 libbonmin.a 与依赖闭包：
  bonmin_smoke      —— 纯消费者视角：公开 API 跑完整 B-BB 并断言最优值
  bonmin_ohos_test  —— HarmonyOS 专项：安装头版本自报 + Ipopt 运行时初始化
                       + 完整求解链断言（见各自源文件头注释）
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CoinorBonminTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

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
        # 直接执行消费者二进制（非 cmake.test()）：conanrun 注入的
        # LD_LIBRARY_PATH 使 libipopt.so 在 OHOS 运行时可解析
        # （coinor-ipopt 的 runenv_info 同时前置干净 /system/lib64）。
        for name in ("bonmin_smoke", "bonmin_ohos_test"):
            bin_path = os.path.join(self.cpp.build.bindirs[0], name)
            self.run(bin_path, env="conanrun")
