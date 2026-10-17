#!/usr/bin/env python3
"""Conan recipe — range-v3 0.12.0 (CMake header-only / INTERFACE library).

Reference: archives/r/robin-map/1.4.1/ (header-only CMake pattern).

Downstream expects:
  find_package(range-v3 REQUIRED)
  target_link_libraries(... PRIVATE range-v3::range-v3)
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class RangeV3Conan(ConanFile):
    name = "range-v3"
    version = "0.12.0"
    description = "Experimental range library for C++14/17/20"
    license = "BSL-1.0"
    homepage = "https://github.com/ericniebler/range-v3"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: CMake may not recognize OHOS as a known system name
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["RANGE_V3_TESTS"] = "OFF"
        tc.cache_variables["RANGE_V3_EXAMPLES"] = "OFF"
        tc.cache_variables["RANGE_V3_PERF"] = "OFF"
        tc.cache_variables["RANGE_V3_DOCS"] = "OFF"
        tc.cache_variables["RANGE_V3_HEADER_CHECKS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Main build: header-only, just configure for install
        cmake = CMake(self)
        cmake.configure()

        # Build upstream tests in an isolated temporary directory
        test_build_dir = tempfile.mkdtemp(prefix="range-v3-tests-")
        try:
            toolchain = os.path.join(
                self.generators_folder, "conan_toolchain.cmake"
            ).replace("\\", "/")
            cmake_cmd = [
                "cmake", self.source_folder,
                "-G", "Unix Makefiles",
                "-DCMAKE_TOOLCHAIN_FILE=" + toolchain,
                "-DRANGE_V3_TESTS=ON",
                "-DRANGE_V3_EXAMPLES=OFF",
                "-DRANGE_V3_PERF=OFF",
                "-DRANGE_V3_DOCS=OFF",
                "-DRANGE_V3_HEADER_CHECKS=OFF",
            ]
            # OHOS-specific flags: match the pattern in generate()
            if self.settings.os in ("Linux", "OHOS"):
                cmake_cmd.append("-DCMAKE_SYSTEM_NAME=Linux")
            if self.settings.os == "OHOS":
                cmake_cmd.append("-DCMAKE_SYSTEM_PROCESSOR=aarch64")
                cmake_cmd.append(
                    "-DCMAKE_CXX_FLAGS=-stdlib=libc++ "
                    "-Wno-disabled-macro-expansion -Wno-deprecated"
                )
                cmake_cmd.append("-DCMAKE_EXE_LINKER_FLAGS=-static")
                # When cross-compiling (e.g. x86_64 host → aarch64 OHOS), set
                # the CTest emulator so that aarch64 test binaries run under qemu.
                if cross_building(self):
                    qemu = shutil.which("qemu-aarch64")
                    if not qemu:
                        raise ConanInvalidConfiguration(
                            "qemu-aarch64 is required to run upstream OHOS tests"
                        )
                    cmake_cmd.append("-DCMAKE_CROSSCOMPILING_EMULATOR=" + qemu)
            subprocess.check_call(cmake_cmd, cwd=test_build_dir)
            subprocess.check_call(
                ["make", "-j20", "-k"],
                cwd=test_build_dir,
            )
            # Run upstream tests (CTest uses CMAKE_CROSSCOMPILING_EMULATOR
            # when set, so no manual qemu wrapping is needed here)
            subprocess.check_call(
                ["ctest", "--output-on-failure", "-j20"],
                cwd=test_build_dir,
            )
        finally:
            # Clean up temp build dir
            shutil.rmtree(test_build_dir, ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no link libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]

        self.cpp_info.set_property("cmake_file_name", "range-v3")
        self.cpp_info.set_property("cmake_target_name", "range-v3::range-v3")
        self.cpp_info.set_property("pkg_config_name", "range-v3")

        # Components mirroring upstream CMake structure
        self.cpp_info.components["meta"].set_property("cmake_target_name", "range-v3::meta")
        self.cpp_info.components["meta"].includedirs = ["include"]
        self.cpp_info.components["concepts"].set_property("cmake_target_name", "range-v3::concepts")
        self.cpp_info.components["concepts"].includedirs = ["include"]
        self.cpp_info.components["concepts"].requires = ["meta"]
