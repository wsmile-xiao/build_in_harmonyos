#!/usr/bin/env python3
"""Conan recipe for nanobench 4.6.0."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class NanobenchConan(ConanFile):
    name = "nanobench"
    version = "4.6.0"
    description = "Simple, fast, accurate single-header microbenchmarking library for C++11 and newer."
    license = "MIT"
    homepage = "https://github.com/martinus/nanobench"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("benchmark", "microbenchmark", "header-only")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["NANOBENCH_BUILD_TEST"] = "ON"
        tc.variables["NB_cxx_standard"] = "11"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            self.run(os.path.join(self.build_folder, "nb"), env="conanrun")
        else:
            self.output.info("cross-building: nanobench upstream executable was compiled but not run")

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["nanobench"]
        self.cpp_info.set_property("cmake_file_name", "nanobench")
        self.cpp_info.set_property("cmake_target_name", "nanobench::nanobench")
