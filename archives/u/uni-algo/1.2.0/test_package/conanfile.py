#!/usr/bin/env python3
"""test_package — uni-algo 1.2.0 消费者验证 + 鸿蒙专项测试。

编译并运行两个探针，二者都链接被测包的 libuni-algo.a 并包含其公开头文件：
- consumer_probe：消费者验证用例，覆盖转换 / 严格校验 / 大小写 / locale 映射 /
  有案与忽略案排序 / 归一化 / 码点属性 / Script / 范围视图 / 字素与词断句。
- ohos_probe：鸿蒙专项测试，只放换平台可能变的断言（OHOS 宏与 LP64/wchar_t ABI、
  musl codeset、una::locale::system()、含组合序列的文件名在鸿蒙文件系统上的原始字节
  保持、98304 字节大缓冲往返）。

上游官方测试套件不在这里——它由 conanfile.py 的 build() 用上游自己的
`cmake -S test && ctest` 真实执行，本目录只做「包能不能被正常消费」的验证。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake


class UniAlgoTestPkg(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualBuildEnv", "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "consumer.cpp", "test_ohos.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译 + 链接")
            return
        # 静态库交付，运行期无额外依赖；conanrun 里带上包目录即可。
        for exe in ("consumer_probe", "ohos_probe"):
            self.run("./%s" % exe, cwd=self.build_folder, env="conanrun")
        self.output.info("test_package 两个探针全部退出码 0")
