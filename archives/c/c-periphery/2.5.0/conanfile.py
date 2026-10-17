#!/usr/bin/env python3
"""Conan recipe for c-periphery 2.5.0 — CMake >=3.19, pure C99, zero dependencies.

上游 tests/*.c 为 8 个需真实外设硬件（串口/GPIO/I2C/SPI/PWM/LED/MMIO 设备文件）
的测试程序，CMake 未注册 CTest（自定义 tests 目标）：build() 只编译链接全部
测试程序作为编译级证据，不执行、不伪造通过；执行验证需真实设备，逐文件
申报于 test_package/MANIFEST.yml，结果经 HMBS_UPSTREAM_TEST_RESULT 如实上报。
"""
import glob
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CPeripheryConan(ConanFile):
    name = "c-periphery"
    version = "2.5.0"
    description = ("C library for GPIO, LED, PWM, SPI, I2C, MMIO and Serial "
                   "peripheral I/O interface access in userspace Linux")
    license = "MIT"
    homepage = "https://github.com/vsergeev/c-periphery"
    url = "https://github.com/vsergeev/c-periphery"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # 零外部依赖：仅标准 C 库 + Linux 内核接口

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.build(target="tests")
        self._emit_hmbs_upstream_marker()

    def _emit_hmbs_upstream_marker(self):
        discovered = len(glob.glob(os.path.join(self.source_folder, "tests", "*.c")))
        marker = {
            "status": "skipped" if discovered > 0 else "failed",
            "framework": "c-periphery-upstream-tests",
            "command": f"cmake --build {self.build_folder} --target tests",
            "discovered": discovered,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": discovered,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["periphery"]
        self.cpp_info.set_property("cmake_file_name", "c-periphery")
        self.cpp_info.set_property("cmake_target_name", "c-periphery::c-periphery")
        self.cpp_info.set_property("pkg_config_name", "libperiphery")
