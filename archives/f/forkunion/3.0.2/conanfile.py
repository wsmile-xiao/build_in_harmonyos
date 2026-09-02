#!/usr/bin/env python3
"""Conan recipe for ForkUnion 3.0.2."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ForkunionConan(ConanFile):
    name = "forkunion"
    version = "3.0.2"
    description = (
        "Low-latency NUMA-aware fork-join thread pool for C, C++, Rust, and Zig"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/ashvardanian/ForkUnion"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("thread-pool", "fork-join", "numa", "parallelism", "c++17")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["FORKUNION_INSTALL"] = "ON"
        tc.variables["FORKUNION_BUILD_TESTS"] = "ON"
        tc.variables["FORKUNION_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["FORKUNION_TEST_SKIP_STRESS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            tc.variables["FORKUNION_WITH_PLACE_THREADS_BY_AFFINITY"] = "OFF"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = [
            "forkunion_shared" if self.options.shared else "forkunion_static"
        ]
        self.cpp_info.set_property("cmake_file_name", "forkunion")
        self.cpp_info.set_property("pkg_config_name", "forkunion")

        header = self.cpp_info.components["header"]
        header.includedirs = ["include"]
        header.libdirs = []
        header.bindirs = []
        header.libs = []
        header.system_libs = ["pthread"]
        if self.settings.os == "OHOS":
            header.defines = ["FU_WITH_PLACE_THREADS_BY_AFFINITY=0"]
        header.set_property("cmake_target_name", "forkunion::header")

        static = self.cpp_info.components["static"]
        static.libs = ["forkunion_static"]
        static.requires = ["header"]
        static.set_property("cmake_target_name", "forkunion::static")

        shared = self.cpp_info.components["shared"]
        shared.libs = ["forkunion_shared"]
        shared.requires = ["header"]
        shared.set_property("cmake_target_name", "forkunion::shared")
