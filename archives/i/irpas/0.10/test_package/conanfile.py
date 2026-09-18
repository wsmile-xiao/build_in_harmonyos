#!/usr/bin/env python3
"""Conan test_package — irpas 0.10 L1 test.

消费者用例 (test_irpas): 模拟上层应用通过公开 CLI 调用 irpas 全部 16 个工具，
断言退出码与 usage 输出；鸿蒙专项用例 (ohos_test): 平台身份 + 原始套接字面 +
CLI 运行验证。两者均真实编译、链接、运行，禁止空壳测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IrpasTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _irpas_bin_dir(self):
        dep = self.dependencies["irpas"]
        # bindirs is relative to the package folder
        rel = dep.cpp_info.bindirs[0]
        return os.path.join(dep.package_folder, rel)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"IRPAS_BIN_DIR": self._irpas_bin_dir()})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # 直接运行二进制兜底（ctest 环境变量路径不生效时仍有证据）
        for t in ("test_irpas", "ohos_test"):
            bin_path = os.path.join(self.cpp.build.bindirs[0], t)
            if os.path.exists(bin_path):
                self.run(f"{bin_path} {self._irpas_bin_dir()}", env="conanrun")