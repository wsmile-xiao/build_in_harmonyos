#!/usr/bin/env python3
"""Conan test_package — libpar2 0.4 (消费者闭环测试)

用 CMake (CMakeDeps + CMakeToolchain) 消费被测包，编译器由 Conan toolchain
提供，不裸用 shell 环境变量 (R33)。libsigc 为传递依赖，由 CMakeDeps 自动
注入 include 路径与链接库。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class Libpar2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libpar2 的公开头文件 include <sigc++/sigc++.h>，消费者必须能解析
        # libsigc 头。CMakeDeps 对传递依赖生成的 data 文件在部分场景下
        # INCLUDE_DIRS 为空，显式声明为直接依赖保证 include 路径注入
        # （与 libsigc 自身 test_package 相同的已验证机制）。
        self.requires("libsigc/2.10.8")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        # 共享库运行期需要 LD_LIBRARY_PATH
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 bash 包一层执行二进制
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # libpar2(静态) 链接 libsigc-2.0.so，运行期需要其 libdir
        lib_dirs = []
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                lib_dirs.append(libdir)
        ld_path = ":".join(lib_dirs)
        self.run(f"LD_LIBRARY_PATH={ld_path} {bash} -c './test_libpar2'")
