#!/usr/bin/env python3
"""test_package/conanfile.py — unittest-cpp 2.0.0 消费者测试驱动。

编译 test.cpp（真实链接 unittest-cpp::unittest-cpp 静态库并调用公开 API），
经 ctest 执行：A1 runner 路径 / A2 SignalTranslator 崩溃翻译反向验证 /
A3 MemoryOutStream / A4 TestResults 失败语义。任一失败 ⇒ ctest 非零 ⇒ L1 失败。
"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UnittestCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()  # ctest: consumer_assertions（A1-A4 任一失败即非零退出）
        # 再以退出码直跑一次被测程序（L0d 显式执行路径，与 ctest 同源断言）
        import os
        import shutil
        exe = os.path.join(self.cpp.build.bindirs[0], "test_unittest_cpp")
        if shutil.which(exe) or os.path.isfile(exe):
            self.run(f'"{exe}"', env="conanrun")
