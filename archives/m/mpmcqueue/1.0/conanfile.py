#!/usr/bin/env python3
"""Conan recipe — mpmcqueue 1.0 (CMake header-only library).

rigtorp/MPMCQueue 是一个无锁有界多生产者多消费者队列的 header-only C++ 库
（CMake INTERFACE library），无编译产物、无运行时依赖（仅测试用 pthread）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MpmcqueueConan(ConanFile):
    name = "mpmcqueue"
    version = "1.0"
    description = "A bounded multi-producer multi-consumer concurrent queue for C++ (header-only, lock-free)"
    license = "MIT"
    homepage = "https://github.com/rigtorp/MPMCQueue"
    url = ""  # CI fills this
    topics = ("mpmc", "queue", "header-only", "lock-free", "concurrency")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 上游 CMakeLists 声明 cmake_minimum_required(3.2)，CMake 4.x 需策略回退
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 仅构建测试目标（示例与测试由 test_package/消费者验证覆盖）
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mpmcqueue")
        self.cpp_info.set_property("cmake_target_name", "mpmcqueue::mpmcqueue")
        self.cpp_info.libs = []
