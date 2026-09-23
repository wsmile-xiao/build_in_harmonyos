#!/usr/bin/env python3
"""Conan recipe for blosc2 3.2.3 (CMake)."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class Blosc2Conan(ConanFile):
    name = "blosc2"
    version = "3.2.3"
    description = "Blosc2 blocking, shuffling and lossless compression library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Blosc/c-blosc2"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, filename="blosc2-3.2.3.tar.gz", **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BLOSC_DEPENDENCY_MODE"] = "BUNDLED"
        tc.cache_variables["BLOSC_ENABLE_ZFP"] = "OFF"
        tc.cache_variables["BUILD_STATIC"] = "ON" if not self.options.shared else "OFF"
        tc.cache_variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["BUILD_TESTS"] = "ON"
        tc.cache_variables["BUILD_FUZZERS"] = "OFF"
        tc.cache_variables["BUILD_BENCHMARKS"] = "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_PLUGINS"] = "OFF"
        tc.cache_variables["BLOSC_INSTALL"] = "ON"
        tc.cache_variables["PREFER_EXTERNAL_LZ4"] = "OFF"
        tc.cache_variables["PREFER_EXTERNAL_ZLIB"] = "OFF"
        tc.cache_variables["PREFER_EXTERNAL_ZSTD"] = "OFF"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["BLOSC_RUN_STDIO_TMPFILE_TEST"] = (
            "OFF" if str(self.settings.os) == "OHOS" else "ON"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])
        self.run("ctest --output-on-failure --timeout 120 -j1",
                 cwd=self.build_folder, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["blosc2"]
        self.cpp_info.set_property("cmake_file_name", "Blosc2")
        self.cpp_info.set_property("cmake_target_name", "Blosc2::blosc2")
        self.cpp_info.set_property("pkg_config_name", "blosc2")

