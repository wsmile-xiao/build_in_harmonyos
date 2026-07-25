#!/usr/bin/env python3
"""Conan recipe for iir1 1.10.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rmdir,
    save,
)


class Iir1Conan(ConanFile):
    name = "iir1"
    version = "1.10.0"
    description = "Realtime C++ IIR filter library"
    license = "MIT"
    homepage = "https://github.com/berndporr/iir1"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        platform_modules = os.path.join(self.build_folder, "_cmake_modules")
        save(
            self,
            os.path.join(platform_modules, "Platform", "HarmonyOS.cmake"),
            "include(Platform/Linux)\n",
        )

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_MODULE_PATH"] = platform_modules
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        tc.variables["IIR1_BUILD_TESTING"] = True
        tc.variables["IIR1_BUILD_DEMO"] = False
        tc.variables["IIR1_INSTALL_STATIC"] = False
        tc.generate()

    def build(self):
        build_source = os.path.join(self.build_folder, "_source")
        rmdir(self, build_source)
        copy(self, "*", src=self.source_folder, dst=build_source)

        # Upstream forces the main target to SHARED and separately builds a
        # static test target. Modify only this build folder's source copy so
        # shared and static package IDs cannot contaminate each other.
        replace_in_file(
            self,
            os.path.join(build_source, "CMakeLists.txt"),
            "add_library(iir SHARED ${LIBSRC})",
            "add_library(iir ${LIBSRC})",
        )
        if self.settings.os == "OHOS":
            # HMDFS rejects CMake's version symlink chain. Conan already
            # versions the package, so keep one real ELF with an unversioned
            # SONAME on OHOS.
            replace_in_file(
                self,
                os.path.join(build_source, "CMakeLists.txt"),
                "  SOVERSION 1\n  VERSION ${PROJECT_VERSION}\n",
                "",
            )

        cmake = CMake(self)
        cmake.configure(build_script_folder=build_source)
        cmake.build()
        if can_run(self):
            cmake.ctest(cli_args=["--output-on-failure"])
        else:
            self.output.warning(
                "Cross build: all eight upstream tests were compiled but "
                "cannot execute on the build host."
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["iir"]
        self.cpp_info.set_property("cmake_file_name", "iir")
        self.cpp_info.set_property("cmake_target_name", "iir::iir")
        self.cpp_info.set_property("pkg_config_name", "iir")
