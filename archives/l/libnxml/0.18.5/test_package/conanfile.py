#!/usr/bin/env python3
"""Conan test_package — libnxml 0.18.5 (XML parse/write API)

消费者验证：必须使用 Conan 安装后的公共头文件（include/nxml.h）与库
（lib/libnxml.so），真实调用公开 API 完成 XML 解析并校验结果。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibnxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 公共头 nxml.h #include <curl/curl.h>（公开 API 透传 curl 类型），
        # 消费者编译必须能拿到 curl 头。
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.build()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libnxml")
        self.run(bin_path, env="conanrun")
