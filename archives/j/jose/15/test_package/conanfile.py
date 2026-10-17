#!/usr/bin/env python3
"""Conan test_package — jose L1 消费者测试。

jose 公共头文件（jose/b64.h 等）直接 #include <jansson.h>，因此消费者必须
同时获得 jansson 的 include 路径与链接目标；openssl/zlib 为间接依赖一并声明，
保证 CMakeDeps 生成完整 target 依赖图。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JoseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # jose 公共头文件依赖 jansson；openssl/zlib 为传递链接依赖
        self.requires("jansson/2.15.1.1")
        self.requires("openssl/3.5.8.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # CTest 子进程不继承 conanrun 环境 → 直接以 conanrun env 运行测试二进制，
        # 保证运行时能定位 libjose.so.0（与依赖共享库）
        exe = os.path.join(self.cpp.build.bindirs[0], "test_jose")
        self.run(exe, env="conanrun")
        # HarmonyOS 专项测试（JWS 签名/验证/JWK 指纹集成断言，CMakeLists 已注册 test_jose_ohos）
        ohos_exe = os.path.join(self.cpp.build.bindirs[0], "test_jose_ohos")
        self.run(ohos_exe, env="conanrun")
