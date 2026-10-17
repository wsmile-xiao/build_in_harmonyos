#!/usr/bin/env python3
"""Conan test_package for libheif-dav1d 1.23.0 — 消费者契约测试。

test() 真跑被测产物：直接执行链接了 libheif::libheif 的 C 程序，
由它 heif_init() 后断言 dav1d 插件已被 dlopen、AV1 解码能力可用。

插件产物路径不从 CMake 导入目标猜（实测 IMPORTED_LOCATION_RELEASE 取不到值，
会退化成 "/libheif/libheif-dav1d.so" 这种假路径），而是由本 conanfile 用
被测包的真实 package_folder 拼出来注入 CMake —— 与消费者实际拿到的安装树一致。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibheifDav1dTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        dep = self.dependencies[self.tested_reference_str]
        tc.cache_variables["HEIF_PLUGIN_FILE"] = os.path.join(
            dep.package_folder, "lib", "libheif", "libheif-dav1d.so")
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # env="conanrun" 提供 libheif/libdav1d 的运行时库搜索路径，以及配方
        # package_info() 导出的 LIBHEIF_PLUGIN_PATH；测试程序会断言该变量
        # 确实指向产物所在目录。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libheif_dav1d"),
                 env="conanrun")
