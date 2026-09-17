#!/usr/bin/env python3
"""Conan recipe — libopencad 0.2.0 (C++11 CAD file reading library).

libopencad provides a uniform API to read CAD (DWG/DXF) files.  This
recipe builds the static/shared library with CMake.

Notes:
- The upstream project() name is "opencad", but the conan package name
  is "libopencad" (mapped in this recipe).
- The upstream CMakeLists hardcodes `-std=c++11`; we let the OHOS-adapted
  CMakeToolchain (compiler.cppstd=17 from the ohos-aarch64 profile)
  manage the standard instead, which is fine as the codebase is C++11.
- Library body has no external dependencies (C++11 stdlib only).  GTest
  is only required by upstream tests, not by the package itself.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class LibopencadConan(ConanFile):
    name = "libopencad"
    version = "0.2.0"
    description = "OpenSource library to read/write CAD (DWG/DXF/DXFB) files"
    license = "MIT"
    homepage = "https://github.com/nextgis-borsch/lib_opencad"
    url = "https://github.com/nextgis-borsch/lib_opencad"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream project() name is "opencad"; force it to libopencad so
        # the produced artifact name matches the conan package.
        tc.variables["PROJECT_NAME"] = "libopencad"
        # libopencad builds either opencad (shared) or opencadstatic
        # (static) based on BUILD_SHARED_LIBS; we always emit static,
        # built as "opencadstatic" -> keep BUILD_SHARED_LIBS off here and
        # rename the target below via package().
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Disable optional apps (cadinfo CLI) and tests in the main recipe;
        # tests are exercised separately via test_package / upstream.
        tc.variables["BUILD_APPS"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        # Upstream declares cmake_minimum_required(2.8.12); modern CMake
        # removed <3.5 compatibility, so lower the policy floor instead of
        # patching the upstream file.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream declares cmake_minimum_required(2.8.12); modern CMake
        # removed <3.5 compatibility, so pass the policy floor on the CLI
        # (toolchain variables are not read early enough for this one).
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        # cmake.install() already installs the static library
        # (liblibopencadstatic.a) and all public headers under
        # include/opencad/ (see lib/CMakeLists.txt install rules).
        cmake.install()
        # Ship the upstream DWG sample in res/ so test_package can open a
        # real file without storing binaries in the git repo (PR diffs
        # cannot carry binary patch data).
        copy(self, "1arc.dwg",
             src=os.path.join(self.source_folder, "tests", "data", "r2000"),
             dst=os.path.join(self.package_folder, "res", "r2000"))

    def package_info(self):
        # Upstream lib/CMakeLists.txt names the static target
        # ${PROJECT_NAME}static; with PROJECT_NAME forced to libopencad the
        # actual artifact is liblibopencadstatic.a, so link against
        # "libopencadstatic" (conan prepends lib/). The public headers are
        # installed under include/opencad/.
        self.cpp_info.libs = ["libopencadstatic"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libopencad")
        self.cpp_info.set_property("cmake_target_name", "libopencad::libopencad")
