#!/usr/bin/env python3
"""Conan test_package for tinyalsa 2.0.0 —— 消费者视角验证（层 2）。

编译一个真正链接已安装 libtinyalsa 的小程序，断言：
  * 安装的头文件 <tinyalsa/asoundlib.h> 可用、版本宏与包版本一致；
  * 纯计算 API（pcm_format_to_bits / mixer_ctl_get_type_string）行为与上游一致；
  * 不存在声卡的负向路径（pcm_open 卡 1000）在 OHOS 上语义与上游一致；
  * 空指针安全 API 不崩溃。

断言数 = 10，与 test_package/MANIFEST.yml 的 assertion_count 及 PR 正文
「鸿蒙特有测试」行一致（不进上游用例分母）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TinyalsaTestConan(ConanFile):
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
        # cwd 显式指到 build 目录：ctest 的 CTestTestfile.cmake 就在那里
        self.run("ctest --output-on-failure", env="conanrun", cwd=self.build_folder)
