#!/usr/bin/env python3
"""Conan test_package — miniz 3.1.2 消费者测试。

链接 Conan 包内 libminiz.a（miniz::miniz，静态）。
L1e 破坏性反向验证 (R34)：移走包 lib/include 后此测试必须失败——
test.c 实质调用 mz_compress/mz_uncompress 等符号，真依赖 miniz。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MinizTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 显式运行消费者二进制（静态库，无需 LD_LIBRARY_PATH）。
        # L0d 门禁要求 test() 含 self.run()；L1e 破坏性反向验证 (R34)
        # 移走包 lib/include 后此调用必失败——test.c 实质调用 mz_ 符号，真依赖 miniz。
        test_bin = self.cpp.build.bindirs[0]
        self.run(f'"{test_bin}/test_miniz"', env="conanrun")
