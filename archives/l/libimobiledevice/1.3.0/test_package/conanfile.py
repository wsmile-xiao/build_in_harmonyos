#!/usr/bin/env python3
"""Conan test_package for libimobiledevice — verifies the C API links.

Calls idevice_get_device_list(); on OHOS (no usbmuxd daemon / iOS device)
it returns an error or empty list, which still proves the library links
and the API symbols resolve (R34: substantive use of the tested API).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibimobiledeviceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libimobiledevice.h 公共头 include <plist/plist.h>，需 libplist 的 include 路径
        self.requires("libplist/2.3.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libimobiledevice")
        self.run(bin_path, env="conanrun")
