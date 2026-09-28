#!/usr/bin/env python3
"""Conan recipe for dslib 1.1 on HarmonyOS PC.

dslib is a small C data-structure library (https://github.com/jarun/dslib).
Upstream ships Makefile + CMakeLists.txt; the upstream CMakeLists.txt has
no install rules, so patch 0001 adds install(TARGETS ds) plus headers
under include/ds (matching the upstream INSTALL_INTERFACE include/ds).

OHOS adaptation notes:
  - No platform-specific source changes required; builds cleanly with clang.
  - Upstream tests: 6 test programs. 5 self-terminating suites pass
    (test_avl_1 / test_bst_1 / test_dlist_1 / test_queue_1 / test_stack_1).
    avl_Thread_Safe_Test is an interactive demo by design (50 threads +
    while(1) pause(), signal-driven) and is not batch-runnable.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DslibConan(ConanFile):
    name = "dslib"
    version = "1.1"
    description = "dslib 1.1 - generic data structures library in C"
    license = "MIT"
    homepage = "https://github.com/jarun/dslib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["ds"]
        self.cpp_info.includedirs = ["include/ds"]
