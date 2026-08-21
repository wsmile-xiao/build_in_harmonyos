#!/usr/bin/env python3
"""Conan recipe — atomic_queue 1.9.2 (CMake, header-only).

A high-performance lock-free concurrent queue library for C++.
The library is header-only (INTERFACE target in CMake); no runtime library
is produced. Only the include/atomic_queue/ headers are packaged.

Upstream tests require Boost.Test and are not built here; the test_package
exercises the core API directly.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class AtomicQueueConan(ConanFile):
    name = "atomic_queue"
    version = "1.9.2"
    description = "C++ lock-free concurrent queue library"
    license = "MIT"
    homepage = "https://github.com/max0x7ba/atomic_queue"
    url = "https://github.com/max0x7ba/atomic_queue"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake needs a platform to detect compiler; force Linux on OHOS.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Disable upstream tests (require Boost.Test) and examples.
        tc.variables["ATOMIC_QUEUE_BUILD_TESTS"] = "OFF"
        tc.variables["ATOMIC_QUEUE_BUILD_EXAMPLES"] = "OFF"
        # Enable the CMake install target so we can use cmake.install().
        tc.variables["ATOMIC_QUEUE_ENABLE_INSTALL"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "atomic_queue")
        self.cpp_info.set_property("cmake_target_name", "atomic_queue::atomic_queue")
