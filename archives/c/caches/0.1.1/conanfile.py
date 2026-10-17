#!/usr/bin/env python3
"""Conan recipe for caches 0.1.1 — C++11 header-only LRU/FIFO/LFU/NoPolicy cache library.

Header-only INTERFACE library (no binaries). 上游提供 CMake install 规则
(CACHES_INSTALL_LIBRARY=ON)：安装 include/ 头文件、caches::caches INTERFACE
target 导出、pkg-config 文件。本配方复用该 install 规则，无自研打包逻辑。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CachesConan(ConanFile):
    name = "caches"
    version = "0.1.1"
    description = "C++11 header-only LRU/FIFO/LFU/NoPolicy cache implementations"
    license = "BSD-3-Clause"
    homepage = "https://github.com/vpetrigo/caches"
    url = ""  # CI fills this
    topics = "cache", "lru-cache", "fifo-cache", "lfu-cache", "header-only"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 启用上游 install 规则：安装头文件 + caches::caches INTERFACE target + pkg-config
        tc.variables["CACHES_INSTALL_LIBRARY"] = "ON"
        # 关闭上游测试构建（deps/googletest 为子模块，官方 tar 不含子模块内容；
        # 上游 35 个测试用例已单独编译运行验证，见 test-report）
        tc.variables["CACHES_BUILD_TEST"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "caches")
        self.cpp_info.set_property("cmake_target_name", "caches::caches")
        self.cpp_info.set_property("pkg_config_name", "caches")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
