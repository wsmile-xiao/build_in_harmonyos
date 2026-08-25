#!/usr/bin/env python3
"""Conan recipe for z3 4.15.4 — OpenHarmony PC (aarch64) adaptation.

z3 is a high-performance theorem prover (SMT solver).
Build system: CMake (z3's Python configure script does not support HarmonyOS).
Source: https://github.com/Z3Prover/z3/releases/download/z3-4.15.4/z3_solver-4.15.4.0.tar.gz
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Z3Conan(ConanFile):
    name = "z3"
    version = "4.15.4"
    description = "The Z3 Theorem Prover (SMT solver)"
    license = "MIT"
    homepage = "https://github.com/Z3Prover/z3"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # z3 4.15.4 requires C++20
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        tc.variables["Z3_USE_LIB_GMP"] = False
        tc.variables["Z3_SINGLE_THREADED"] = False
        tc.variables["Z3_BUILD_LIBZ3_SHARED"] = self.options.shared
        tc.variables["Z3_INCLUDE_GIT_HASH"] = False
        tc.variables["Z3_INCLUDE_GIT_DESCRIBE"] = False
        tc.variables["Z3_ENABLE_EXAMPLE_TARGETS"] = False
        tc.variables["Z3_BUILD_DOCUMENTATION"] = False
        tc.variables["Z3_BUILD_PYTHON_BINDINGS"] = False
        tc.variables["Z3_BUILD_DOTNET_BINDINGS"] = False
        tc.variables["Z3_BUILD_JAVA_BINDINGS"] = False
        tc.variables["Z3_BUILD_EXECUTABLE"] = True
        tc.variables["Z3_BUILD_TEST_EXECUTABLES"] = False
        # Set stdlib for Clang on OHOS/Linux to fix linker errors
        if self.settings.os in ("Linux", "OHOS") and self.settings.compiler == "clang":
            stdlib = f" -stdlib={self.settings.compiler.libcxx}".rstrip("1")
            tc.variables["CMAKE_CXX_FLAGS"] = tc.variables.get("CMAKE_CXX_FLAGS", "") + stdlib
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # z3 4.15.4: CMakeLists.txt is in the core/ subdirectory
        build_script_folder = os.path.join(self.source_folder, "core")
        cmake.configure(build_script_folder=build_script_folder)
        cmake.build()

    def package(self):
        # Copy LICENSE.txt from core/ directory
        copy(self, "LICENSE.txt", os.path.join(self.source_folder, "core"),
             os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Z3")
        self.cpp_info.set_property("cmake_target_name", "z3::libz3")

        self.cpp_info.components["libz3"].libs = ["libz3" if self.settings.os == "Windows" else "z3"]
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.components["libz3"].system_libs.extend(["pthread", "m"])

        self.cpp_info.components["libz3"].set_property("cmake_target_name", "z3::libz3")
