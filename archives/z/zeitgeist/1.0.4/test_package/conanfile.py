#!/usr/bin/env python3
"""Test package for zeitgeist — verifies headers and library presence."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run
import os


class ZeitgeistTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # test_zeitgeist.c 直接 #include <glib.h>——test_package 必须自己
    # requires glib（仅 requires zeitgeist 时，CMakeDeps 不为 test 生成
    # glib 的完整 target/INTERFACE_INCLUDE_DIRECTORIES，编译报
    # "glib.h file not found"）。
    requires = "zeitgeist/1.0.4", "glib/2.84.0.1"
    # CMakeToolchain 不放 generators 属性——generate() 里显式实例化以注入
    # GLIB_LIBINTL 变量（放属性里再实例化会报 "declared in the generators
    # attribute, but was instantiated in the generate() method too"）。
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS 上 glib 的 libglib-2.0.so/libgio-2.0.so 引用 g_libintl_*
        # 符号，由 glib 包内的 libintl 代理库（libintl.so）提供——但
        # CMakeDeps 的 glib::glib target 的 INTERFACE_LINK_LIBRARIES 不
        # 含它，test 链接可执行文件时报 undefined reference g_libintl_*。
        # 显式把 glib 包内 libintl.so 传给 CMake，由 CMakeLists 链上。
        toolchain = CMakeToolchain(self)
        glib_folder = self.dependencies["glib"].package_folder
        libintl = os.path.join(glib_folder, "lib", "libintl.so")
        if os.path.isfile(libintl):
            toolchain.variables["GLIB_LIBINTL"] = libintl.replace("\\", "/")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # CMake 默认把可执行文件放构建根目录（非 bin/ 子目录）——
            # 用 cpp.build.bindirs 解析实际输出目录（dee test_package 同款）。
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_zeitgeist")
            self.run(test_bin, env="conanrun")
