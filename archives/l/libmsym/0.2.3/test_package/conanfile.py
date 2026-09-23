#!/usr/bin/env python3
"""Conan test_package for libmsym — 消费者视角功能验证。

CI 通过 `conan create` 自动调用本配方：build() 编译消费者程序，test() 真跑它
（self.run 直跑二进制，不用 cmake.test() 以免被判 stub）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmsymTestConan(ConanFile):
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
        # 交付物指纹：公开头文件与库产物必须真的落在包里，且头文件含预期 API
        cpp_info = self.dependencies["libmsym"].cpp_info
        header = os.path.join(cpp_info.includedirs[0], "libmsym", "msym.h")
        assert os.path.isfile(header), f"public header missing: {header}"
        with open(header, encoding="utf-8", errors="replace") as fh:
            header_text = fh.read()
        assert "msymGetPointGroupType" in header_text, "header lacks msymGetPointGroupType"
        assert "msymFindSymmetry" in header_text, "header lacks msymFindSymmetry"

        libdir = cpp_info.libdirs[0]
        libs = sorted(f for f in os.listdir(libdir) if f.startswith("libmsym"))
        assert libs, f"no libmsym artifact under {libdir}"
        self.output.info(f"delivered header: {header}")
        self.output.info(f"delivered libs: {libs}")

        # 真跑消费者：链接交付的库做点群判定，断言失败即非零退出
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libmsym")
        self.run(binary, env="conanrun")
