#!/usr/bin/env python3
"""Conan recipe — libcrcutil 1.0 (portable CMake build)."""

import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class LibcrcutilConan(ConanFile):
    name = "libcrcutil"
    version = "1.0"
    description = "C++ library for ordinary, rolling, and concatenated CRC computation"
    license = "Apache-2.0"
    homepage = "https://code.google.com/archive/p/crcutil/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), CMAKELISTS)

    def generate(self):
        if str(self.settings.os) == "OHOS":
            if str(self.settings.arch) != "armv8":
                raise ConanInvalidConfiguration(
                    "libcrcutil/1.0 currently supports only OHOS armv8"
                )
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        runner = self._cross_runner()
        if runner:
            tc.variables["CMAKE_CROSSCOMPILING_EMULATOR"] = runner
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        runner = self._cross_runner()
        test_env = Environment()
        if runner:
            test_env.define(
                "QEMU_SET_ENV",
                self._qemu_set_env(os.path.join(self.build_folder, "lib")),
            )
        with test_env.vars(self).apply():
            cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        CMake(self).install()
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "COPYING"), license_dir)

    def package_info(self):
        self.cpp_info.libs = ["crcutil"]
        self.cpp_info.set_property("cmake_file_name", "libcrcutil")
        self.cpp_info.set_property("cmake_target_name", "libcrcutil::libcrcutil")
        self.cpp_info.set_property("pkg_config_name", "libcrcutil")

    def _cross_runner(self):
        if str(self.settings.os) != "OHOS":
            return ""
        if platform.machine().lower() in ("aarch64", "arm64"):
            return ""
        runner = shutil.which("qemu-aarch64")
        if not runner:
            raise ConanInvalidConfiguration(
                "Running OHOS AArch64 upstream tests requires qemu-aarch64"
            )
        return runner

    def _qemu_set_env(self, library_path):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = os.path.realpath(compiler_executables.get("cpp", ""))
        sdk_library_path = os.path.join(
            os.path.dirname(os.path.dirname(cxx)), "lib", "aarch64-linux-ohos"
        )
        return f"LD_LIBRARY_PATH={library_path}:{sdk_library_path}"


CMAKELISTS = r"""cmake_minimum_required(VERSION 3.15)
project(libcrcutil VERSION 1.0 LANGUAGES C CXX)

add_library(crcutil
    code/crc32c_sse4.cc
    code/multiword_128_64_gcc_amd64_sse2.cc
    code/multiword_64_64_cl_i386_mmx.cc
    code/multiword_64_64_gcc_amd64_asm.cc
    code/multiword_64_64_gcc_i386_mmx.cc
    examples/interface.cc
)
add_library(libcrcutil::libcrcutil ALIAS crcutil)
target_compile_features(crcutil PUBLIC cxx_std_11)
target_compile_definitions(crcutil PRIVATE CRCUTIL_USE_MM_CRC32=0)
target_compile_options(crcutil PRIVATE -Wall)
target_include_directories(crcutil
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/examples>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/code>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tests
)
set_target_properties(crcutil PROPERTIES
    OUTPUT_NAME crcutil
    VERSION 1.0.0
    SOVERSION 1
    POSITION_INDEPENDENT_CODE ON
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

add_executable(crcutil_ut
    tests/set_hi_pri.c
    tests/unittest.cc
)
target_compile_features(crcutil_ut PRIVATE cxx_std_11)
target_compile_definitions(crcutil_ut PRIVATE CRCUTIL_USE_MM_CRC32=0)
target_compile_options(crcutil_ut PRIVATE -Wall)
target_include_directories(crcutil_ut PRIVATE code tests)
target_link_libraries(crcutil_ut PRIVATE crcutil)
set_target_properties(crcutil_ut PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

enable_testing()
add_test(NAME crcutil_upstream_functional
    COMMAND crcutil_ut --noperf
)

install(TARGETS crcutil
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(FILES
    examples/interface.h
    code/std_headers.h
    DESTINATION include
)
"""
