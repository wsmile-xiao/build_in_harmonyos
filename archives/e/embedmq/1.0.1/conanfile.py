#!/usr/bin/env python3
"""Conan recipe — embedmq 1.0.1 (CMake)

embedmq is a lightweight, zero-dependency message dispatch library for
embedded Linux / RTOS (C core + C++ wrapper). Upstream builds with CMake
and ships a static library only (add_library(embedmq STATIC ...)) with a
Linux PAL backend based on pthread + POSIX semaphores. No third-party
dependencies; the upstream test suite (tests/test_embedmq.c and
tests/test_embedmq_cpp.cpp, 16 independent cases across 2 executables) is
built and run via CTest inside build() so CI records real upstream results.

R38 check: the deliverable is a pure static library (no bin/ executables),
so no commands.json is needed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class EmbedmqConan(ConanFile):
    name = "embedmq"
    version = "1.0.1"
    description = "embedmq 1.0.1 — embedded message queue dispatch library (C/C++, zero-dependency)"
    license = "MIT"
    homepage = "https://github.com/w4ysonch/embedmq"
    author = "w4ysonch"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout = cmake_layout(self)
        return basic_layout

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["EMBEDMQ_BUILD_TESTS"] = "ON"
        tc.cache_variables["EMBEDMQ_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream CTest suite inside the recipe build (real evidence).
        if self.settings.os in ("Linux", "OHOS"):
            cmake.ctest()

    def package(self):
        # Upstream CMakeLists.txt has no install() rules, so cmake.install()
        # installs nothing. Copy the built static library and public headers
        # into the package manually.
        cmake = CMake(self)
        cmake.install()
        copy(self, "libembedmq.a", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder, keep_path=False)
        copy(self, "libembedmq.so*", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder, keep_path=False)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"), keep_path=False)
        copy(self, "*.hpp", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["embedmq"]
        self.cpp_info.set_property("cmake_file_name", "embedmq")
        self.cpp_info.set_property("cmake_target_name", "embedmq::embedmq")
        self.cpp_info.includedirs = ["include"]