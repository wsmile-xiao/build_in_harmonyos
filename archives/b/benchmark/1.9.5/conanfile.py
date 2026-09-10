#!/usr/bin/env python3
"""Conan recipe for Google Benchmark 1.9.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


required_conan_version = ">=2.0"


class BenchmarkConan(ConanFile):
    name = "benchmark"
    version = "1.9.5"
    package_type = "library"

    description = "A microbenchmark support library for C++"
    homepage = "https://github.com/google/benchmark"
    license = "Apache-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
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

    def requirements(self):
        # Google Benchmark's GTest suite is built during the recipe build only.
        # gtest/1.17.0.1 exports the GTest::gmock_main component used by the
        # upstream CMakeLists.txt; it must not become a consumer dependency.
        self.test_requires("gtest/1.17.0.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream calls find_package(GTest CONFIG REQUIRED). Keep the config
        # filename's case aligned with the component recipe on OHOS/HMDFS.
        deps.set_property("gtest", "cmake_file_name", "GTest")
        deps.generate()

        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Conan's generic OHOS mapping is HarmonyOS, while the installed
            # CMake platform module is named OHOS.cmake. Also make the target
            # architecture explicit for benchmark's assembly-test gate.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values[
                "cmake_system_processor"
            ] = "aarch64"

        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BENCHMARK_ENABLE_TESTING"] = True
        tc.variables["BENCHMARK_ENABLE_GTEST_TESTS"] = True
        tc.variables["BENCHMARK_USE_BUNDLED_GTEST"] = False
        tc.variables["BENCHMARK_DOWNLOAD_DEPENDENCIES"] = False
        tc.variables["BENCHMARK_ENABLE_ASSEMBLY_TESTS"] = False
        tc.variables["BENCHMARK_ENABLE_DOXYGEN"] = False
        tc.variables["BENCHMARK_INSTALL_DOCS"] = False
        tc.variables["BENCHMARK_INSTALL_TOOLS"] = False
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        # CMakeDeps writes GTestConfig.cmake in this directory. The explicit
        # hint avoids falling back to CMake's module-mode FindGTest on OHOS.
        tc.variables["GTest_DIR"] = self.generators_folder
        tc.generate()

        # This is needed when the shared option is selected so ctest can load
        # libbenchmark.so from the Conan build tree.
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder)
        else:
            self.output.info(
                "cross-building: upstream CTest binaries were built but not run"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "benchmark")

        benchmark = self.cpp_info.components["benchmark"]
        benchmark.libs = ["benchmark"]
        benchmark.set_property("cmake_target_name", "benchmark::benchmark")
        benchmark.set_property("pkg_config_name", "benchmark")

        benchmark_main = self.cpp_info.components["benchmark_main"]
        benchmark_main.libs = ["benchmark_main"]
        benchmark_main.requires = ["benchmark"]
        benchmark_main.set_property(
            "cmake_target_name", "benchmark::benchmark_main"
        )
        benchmark_main.set_property("pkg_config_name", "benchmark_main")

        if not self.options.shared:
            benchmark.defines = ["BENCHMARK_STATIC_DEFINE"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            benchmark.system_libs = ["pthread"]
