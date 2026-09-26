#!/usr/bin/env python3
"""lurlparser 1.1 消费者测试（Conan L1）。

CI 通过 `conan create` 自动运行 test_package：
- test.cpp：消费者视角，仅经公开头 LUrlParser.h + 公开 API
  (LUrlParser::ParseURL::parseURL / scheme_ / host_ / port_ / path_ /
  query_ / fragment_ / isValid / getPort) 解析真实 URL 并核验各字段；
- ohos_test.cpp：HarmonyOS 专项测试：-Werror 严格编译 + IPv6 主机名、
  user:password 权威段、端口范围校验（getPort 1..65535 边界）等
  OHOS 平台相关 URL 解析行为。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LurlparserTestConan(ConanFile):
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
        # L0d: test() 必须通过 self.run() 实际执行测试二进制（真实运行，非空壳）。
        bindir = os.path.join(self.cpp.build.bindirs[0])
        self.run(os.path.join(bindir, "test_lurlparser"), env="conanrun")
        self.run(os.path.join(bindir, "test_lurlparser_ohos"), env="conanrun")
