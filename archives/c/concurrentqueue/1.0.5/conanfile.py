#!/usr/bin/env python3
"""Conan recipe — concurrentqueue 1.0.5 (CMake header-only library).

concurrentqueue 是 moodycamel 的工业级无锁队列，单头文件 header-only C++11 库。
CMake INTERFACE library，无任何第三方依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ConcurrentQueueConan(ConanFile):
    name = "concurrentqueue"
    version = "1.0.5"
    description = "An industrial-strength lock-free queue for C++ (moodycamel::ConcurrentQueue), single-header header-only C++11 implementation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/cameron314/concurrentqueue"
    url = ""  # CI fills this
    topics = ("concurrent", "queue", "lock-free", "header-only", "cpp11")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        # 上游安装头文件到 include/concurrentqueue/moodycamel/，下游 include "moodycamel/concurrentqueue.h"
        self.cpp_info.set_property("cmake_file_name", "concurrentqueue")
        self.cpp_info.set_property("cmake_target_name", "concurrentqueue::concurrentqueue")
        self.cpp_info.includedirs = ["include/concurrentqueue"]
        self.cpp_info.libs = []
