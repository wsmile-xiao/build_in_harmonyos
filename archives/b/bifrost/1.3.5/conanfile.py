#!/usr/bin/env python3
"""Conan recipe for bifrost 1.3.5 — CMake build system.

Bifrost: highly parallel construction and indexing of colored and
compacted de Bruijn graphs (CLI tool + static/shared library).

Adaptation notes (OHOS aarch64):
- Upstream CMakeLists defaults COMPILATION_ARCH=native and ENABLE_AVX2=ON,
  which are x86-64 oriented; disabled for the OHOS arm64 target so the
  toolchain does not emit unsupported -march=native / AVX2 code.
- zlib is a REQUIRED dependency (find_package(ZLIB REQUIRED)); provided
  through the conan registry (R36 pre-published).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BifrostConan(ConanFile):
    name = "bifrost"
    version = "1.3.5"
    description = "Bifrost: highly parallel construction and indexing of colored and compacted de Bruijn graphs"
    license = "BSD-2-Clause"
    homepage = "https://github.com/pmelsted/bifrost"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static keeps the CLI self-contained on OHOS (R26-style default).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS arm64: disable x86-64 native arch tuning and AVX2.
        tc.variables["COMPILATION_ARCH"] = "OFF"
        tc.variables["ENABLE_AVX2"] = "OFF"
        # Upstream declares cmake_minimum_required(2.8.12); CMake >= 4.x
        # removed pre-3.5 policy compatibility, so relax the policy floor.
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
        self.cpp_info.set_property("cmake_file_name", "bifrost")
        self.cpp_info.set_property("cmake_target_name", "bifrost::bifrost")
        self.cpp_info.set_property("pkg_config_name", "bifrost")
        self.cpp_info.libs = ["bifrost"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.bindirs = ["bin"]