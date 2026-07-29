#!/usr/bin/env python3
"""Conan recipe — bento4 1.6.0-641 (CMake)"""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get


class Bento4Conan(ConanFile):
    name = "bento4"
    version = "1.6.0-641"
    license = "GPL-2.0-only"
    author = "axiomatic-systems"
    url = "https://github.com/axiomatic-systems/Bento4"
    homepage = "http://www.bento4.com"
    description = "C++ library and tools for reading and writing ISO-MP4 files"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # 上游测试由 CMake 处理，通过 CMakeToolchain 交叉编译
        tc.variables["BENTO4_BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试由 cmake.test() 触发，走 CMakeToolchain 交叉编译链路
        if can_run(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ap4"]
        self.cpp_info.bindirs = ["bin"]
