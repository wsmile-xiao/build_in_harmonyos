#!/usr/bin/env python3
"""Conan recipe for Intel Instrumentation and Tracing Technology API 3.28.2."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class IttapiConan(ConanFile):
    name = "ittapi"
    version = "3.28.2"
    description = "Intel Instrumentation and Tracing Technology API"
    license = "(BSD-3-Clause OR GPL-2.0-only)"
    homepage = "https://github.com/intel/ittapi"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    _upstream_tests = (
        "test_string_handle",
        "test_domain",
        "test_task",
        "test_region",
        "test_frame",
        "test_collection_control",
        "test_thread_naming",
        "test_ittapi",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ittapi supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ITT_API_IPT_SUPPORT"] = False
        toolchain.variables["ITT_API_FORTRAN_SUPPORT"] = False
        toolchain.variables["ITT_API_CPP_SUPPORT"] = True
        toolchain.variables["ITT_API_REFERENCE_COLLECTOR"] = False
        toolchain.variables["ITT_API_INSTALL"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        test_destination = os.path.join(
            self.package_folder, "share", "ittapi", "upstream-tests"
        )
        for test_name in self._upstream_tests:
            copy(
                self,
                test_name,
                src=os.path.join(self.build_folder, "cpp"),
                dst=test_destination,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["ittnotify", "jitprofiling"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "ittapi")
        self.cpp_info.set_property("cmake_target_name", "ittapi::ittapi")
