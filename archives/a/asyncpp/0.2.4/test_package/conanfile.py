#!/usr/bin/env python3
"""test_package — asyncpp 0.2.4 消费者测试（鸿蒙特有测试行）。

消费者只用**已安装的包**（不碰上游源码树）：一个 TU 一次性包含全部 23 个公开头
（等价于消费端最坏包含形态），再对 task/generator/event/mutex/shared_mutex/
semaphore/sleep/rc_ptr 逐条断言，程序自报 `asyncpp consumer checks: N run, M failed`，
任一失败即退出码非 0。另显式调用 testing::path::dump()——它落在 src/testing/
interleaver.o（std::format 所在目标），用来验证 package_info 下发的
c++experimental 链接口对消费者真实可用。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AsyncppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # asyncpp 公开头使用协程/concepts，消费者必须按 C++20 编译
        # （OHOS profile 的 compiler.cppstd=17 同样在此覆盖为 20）。
        tc.blocks["cppstd"].values["cppstd"] = "20"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip consumer runtime test")
            return
        consumer = os.path.join(self.cpp.build.bindirs[0], "test_asyncpp")
        self.run('"%s"' % consumer)
