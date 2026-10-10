#!/usr/bin/env python3
"""Conan recipe — loguru 2.1.0 (emilk/loguru, C++11 header-only logging).

emilk/loguru 以两文件分发：loguru.hpp（声明）+ loguru.cpp（实现）。
上游无构建系统（无根 CMakeLists）——官方 README 分发方式即"拷贝两文件，
消费者 #include <loguru.cpp> 或编译链接 loguru.cpp"。故 package_type=
header-library，package() 打包两文件到 include/（E257 先例：no-op build
满足 G1 recipe-completeness 门禁）。

注意与 main 中已有的 loguru/0.7.3（Delgan/loguru，纯 Python 日志库）
为同名不同项目——本件为 emilk C++ 版。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LoguruConan(ConanFile):
    name = "loguru"
    version = "2.1.0"
    package_type = "header-library"

    description = "Robust and efficient logging library for C++ (emilk/loguru)"
    license = "Unlicense"
    homepage = "https://github.com/emilk/loguru"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("logging", "header-only", "cpp11", "utilities")

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Header-only 库（hpp+cpp 两文件分发模式），无独立构建系统：
        # build() no-op 以满足 G1 门禁（E257：bshoshany-thread-pool 先例）。
        pass

    def package(self):
        # 官方分发 = loguru.hpp + loguru.cpp 两个文件（README: "Just two
        # files: loguru.hpp and loguru.cpp"），全部放进 include/ 供消费者
        # #include <loguru.cpp> 或单独编译链接。
        copy(self, "loguru.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "loguru.cpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "loguru")
        self.cpp_info.set_property("cmake_target_name", "loguru::loguru")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only：无预编译产物；消费者包含/编译 loguru.cpp 时需链
        # pthread + dl（stacktrace 用 backtrace/dladdr，非 Windows 平台）。
        self.cpp_info.libs = []
