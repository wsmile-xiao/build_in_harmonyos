#!/usr/bin/env python3
"""Conan recipe for concurrencpp 0.1.7 (CMake, C++20).

concurrencpp is a C++20 concurrency library (executors, coroutine-friendly
results, timers).  Built with CMake; only dependency is Threads (system).
Adapted for HarmonyOS PC (arm64, aarch64-linux-ohos).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ConcurrencppConan(ConanFile):
    name = "concurrencpp"
    version = "0.1.7"
    description = "C++20 concurrency library (concurrencpp 0.1.7)"
    license = "MIT"
    homepage = "https://github.com/David-Haim/concurrencpp"
    url = "https://github.com/David-Haim/concurrencpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # concurrencpp has no third-party runtime dependency (Threads is system)
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 默认静态链接，避免与共享库环境歧义（R26 仅适用于系统同名库，本包非系统同名）
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
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
        self.cpp_info.libs = ["concurrencpp"]
        # 上游把公共头安装到 include/concurrencpp-0.1.7/ 子目录（INSTALL_INTERFACE
        # 未导出 include 路径），配方显式声明 include 根，使 #include <concurrencpp/...>
        # 在消费者 CMakeDeps 中可解析。
        self.cpp_info.includedirs = ["include/concurrencpp-0.1.7"]
        self.cpp_info.set_property("cmake_file_name", "concurrencpp")
        self.cpp_info.set_property("cmake_target_name", "concurrencpp::concurrencpp")
