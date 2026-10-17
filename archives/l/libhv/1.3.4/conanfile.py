#!/usr/bin/env python3
"""Conan recipe — libhv 1.3.4 (CMake build, HarmonyOS OHOS aarch64).

libhv is a C/C++ network library (event loop, HTTP, WebSocket, TLS).
Official build system is CMake (upstream also ships a custom `configure`
shell script, but CMake is the canonical build entry per BUILD.md).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibhvConan(ConanFile):
    name = "libhv"
    version = "1.3.4"
    description = "C/C++ network library for developing TCP/UDP/SSL/HTTP/WebSocket client and server"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ithewei/libhv"
    url = "https://github.com/ithewei/libhv"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 默认静态：OHOS 设备动态加载器对自建未签名 .so 的符号加载受限
    # （见 SKILL §7 ELF 签名陷阱），静态库 libhv_static.a 保证消费者直接链接可用。
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # HarmonyOS PC: CMake cross-compile target is aarch64-linux-ohos via clang triplet.
        # libhv's CMakeLists checks UNIX-like platforms through CMAKE_SYSTEM_NAME;
        # Conan's OHOS profile already maps os=OHOS -> triplet aarch64-linux-ohos.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Deterministic library products for the OHOS archive:
        #   - static libhv (default, R26-safe: not a system-name lib, no /lib pollution risk
        #     either way, but archive consumers link statically on device)
        #   - shared libhv.so
        if not self.options.shared:
            tc.variables["BUILD_SHARED"] = "OFF"
            tc.variables["BUILD_STATIC"] = "ON"
        else:
            tc.variables["BUILD_SHARED"] = "ON"
            tc.variables["BUILD_STATIC"] = "ON"
        # Disable example binaries / unit-test binaries inside the package (kept out of
        # the archive binary set; upstream tests are covered by the test ledger and the
        # package-level test_package consumer test below).
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_UNITTEST"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.set_property("cmake_file_name", "libhv")
        self.cpp_info.set_property("cmake_target_name", "libhv::libhv")
        libs = []
        if self.options.shared:
            libs.append("hv")
        else:
            libs.append("hv_static")
        self.cpp_info.libs = libs
        self.cpp_info.includedirs = ["include"]  # headers installed under include/hv/, consumer uses #include "hv/xxx.h"