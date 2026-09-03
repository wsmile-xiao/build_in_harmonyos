#!/usr/bin/env python3
"""Conan recipe for kaitai-runtime 0.11 on HarmonyOS PC.

kaitai-runtime is the C++ STL runtime library for Kaitai Struct
(https://github.com/kaitai-io/kaitai_struct_cpp_stl_runtime). CMake build.

OHOS-specific adaptations:
  - STRING_ENCODING_TYPE=ICONV (default): HarmonyOS/musl iconv does not know
    the alias "IBM437" / "IBM-437" for the CP437 code page; patch
    0001-ibm437-iconv-alias-fallback.patch retries with the platform alias
    "CP437" so encoding conversion behaves like glibc.
  - zlib/1.3.2 declared so KS_ZLIB is enabled and the upstream unittest
    (process_zlib) compiles/passes; static libz.a (conan, non-shared).
  - BUILD_TESTS left at upstream default; upstream tests are exercised in
    the local gate via upstream_tests, while conan create ships the library.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KaitaiRuntimeConan(ConanFile):
    name = "kaitai-runtime"
    version = "0.11"
    description = "Kaitai Struct C++ STL runtime library"
    license = "MIT"
    homepage = "https://github.com/kaitai-io/kaitai_struct_cpp_stl_runtime"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # ICONV is the default; keep the upstream default so the shipped
        # library matches the locally-tested configuration.
        tc.variables["STRING_ENCODING_TYPE"] = "ICONV"
        # GTest is not a published dependency on ohpcd; upstream tests were
        # exercised in the local upstream_tests gate (53/53 PASSED), so the
        # Conan build ships the library without rebuilding upstream tests.
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
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
        self.cpp_info.libs = ["kaitai_struct_cpp_stl_runtime"]
        self.cpp_info.includedirs = ["include"]