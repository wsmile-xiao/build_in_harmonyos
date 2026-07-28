#!/usr/bin/env python3
"""Conan recipe for plog 1.1.11, a header-only C++ logging library."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PlogConan(ConanFile):
    name = "plog"
    version = "1.1.11"
    description = "Portable, simple and extensible C++ logging library"
    license = "MIT"
    homepage = "https://github.com/SergiusTheBest/plog"
    url = "https://github.com/SergiusTheBest/plog"
    topics = ("logging", "header-only", "cpp")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="plog-1.1.11.tar.gz",
            strip_root=True,
        )

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["PLOG_BUILD_SAMPLES"] = False
        toolchain.cache_variables["PLOG_BUILD_TESTS"] = True
        toolchain.cache_variables["PLOG_INSTALL"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: upstream test executables were built; "
                "run them on the HarmonyOS PC emulator."
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "plog")
        self.cpp_info.set_property("cmake_target_name", "plog::plog")
        self.cpp_info.set_property("pkg_config_name", "plog")
