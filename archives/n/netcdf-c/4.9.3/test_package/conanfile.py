#!/usr/bin/env python3
"""Conan test_package — netcdf-c 4.9.3 L1 consumer test.

Creates a tiny netCDF file through the public C API (nc_create /
nc_def_dim / nc_def_var / nc_enddef / nc_put_var / nc_close) and then
reopens it to verify the data round-trips. Exercises the installed
public headers and the shared library as an external consumer.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class NetcdfCTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building：验证编译+链接通过")
        # 实际运行消费者测试与鸿蒙专项测试（L0d：test() 内真实 self.run 调用）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c 'cd {self.build_folder} && ./test_netcdf-c'", env="conanrun")
        self.run(f"{bash} -c 'cd {self.build_folder} && ./ohos_specific_test'", env="conanrun")