#!/usr/bin/env python3
"""Conan recipe for Catch2 3.8.1 on HarmonyOS PC."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get, export_conandata_patches


class Catch2Conan(ConanFile):
    name = "catch2"
    version = "3.8.1"
    description = "A modern, C++-native test framework"
    license = "BSL-1.0"
    homepage = "https://github.com/catchorg/Catch2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.cache_variables["BUILD_TESTING"] = True
        tc.cache_variables["CATCH_DEVELOPMENT_BUILD"] = True
        tc.cache_variables["CATCH_BUILD_TESTING"] = True
        tc.cache_variables["CATCH_BUILD_EXTRA_TESTS"] = True
        tc.cache_variables["CATCH_BUILD_EXAMPLES"] = False
        tc.cache_variables["CATCH_BUILD_FUZZERS"] = False
        tc.cache_variables["CATCH_INSTALL_DOCS"] = False
        tc.cache_variables["CATCH_INSTALL_EXTRAS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_dir = self.build_folder
        self.run(
            f'ctest --test-dir "{test_dir}" -N | grep -q "Total Tests: 113"',
            env="conanbuild",
        )
        self.run(
            f'ctest --test-dir "{test_dir}" --output-on-failure',
            env="conanbuild",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Catch2")

        catch2 = self.cpp_info.components["Catch2"]
        catch2.libs = ["Catch2"]
        catch2.set_property("cmake_target_name", "Catch2::Catch2")

        main = self.cpp_info.components["Catch2WithMain"]
        main.libs = ["Catch2Main"]
        main.requires = ["Catch2"]
        main.set_property("cmake_target_name", "Catch2::Catch2WithMain")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
