#!/usr/bin/env python3
"""Conan test_package — libpar2 L1 消费者测试。

compiles and links a real consumer executable against the installed
libpar2 public API (CommandLine / Par2Creator / Par2Repairer) and runs
a PAR2 create+verify round-trip.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Libpar2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # libpar2 公开头文件（par2repairer.h 等）include <sigc++/sigc++.h>。
        # ohpcd 预编译 libsigc 二进制的 CMakeDeps 数据中 INCLUDE_DIRS 为空
        # （实测 libsigc_INCLUDE_DIRS_RELEASE 为空，尽管配方声明了 includedirs），
        # 导致消费者编译报 sigc++/sigc++.h not found。这里通过依赖 cpp_info
        # 标准接口显式注入 libsigc 的实际 include 路径（不硬编码缓存路径）。
        if "libsigc" in self.dependencies:
            dep = self.dependencies["libsigc"]
            pf = getattr(dep, "package_folder", None) or ""
            incs = []
            for _i in dep.cpp_info.includedirs:
                incs.append(_i if os.path.isabs(_i) else os.path.join(pf, _i))
            tc.variables["LIBSIGC_INCLUDE_DIRS"] = ";".join(incs)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        self.run("./test_libpar2", env="conanrun")