#!/usr/bin/env python3
"""Yubico PAM 模块 test_package —— 消费者视角验证。

test(): ① dlopen lib/security/pam_yubico.so 并校验 PAM 入口符号
（pam_sm_authenticate/pam_sm_setcred）——模拟 PAM 运行时加载模块的真实路径；
② 运行 ykpamcfg 工具冒烟（-v 正常退出即证明工具链完整）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YubicoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "PAM_MODULE_DIR": os.path.join(
                self.dependencies["yubico"].package_folder, "lib", "security"),
        })
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # CLI 工具冒烟（R34 实质执行被测包二进制）：无 YubiKey 硬件时
        # ykpamcfg 报 "no yubikey present" 且退出码 1——以输出内容断言
        # 二进制可正常运行（能加载依赖库并执行到设备探测逻辑）
        self.run(
            "out=$(ykpamcfg -v 2>&1); echo \"$out\" | grep -q 'no yubikey present'",
            env="conanrun")
