#!/usr/bin/env python3
"""Conan recipe for boost-ext-ut 2.3.1.

boost.ext/UT is a C++20 single-header micro unit-test framework
(include/boost/ut.hpp, 3.3k lines, complete implementation). The C++23
module wrapper (ut.cppm) is disabled: BOOST_UT_DISABLE_MODULE=ON keeps the
pure header mode (module mode needs CMake >= 4.0). Zero dependencies; the
upstream test suite (test/ut + test/ft + examples, all registered through
ut_add_custom_command_or_test -> add_test) runs fully offline.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.scm import Version


class BoostExtUtConan(ConanFile):
    name = "boost-ext-ut"
    version = "2.3.1"
    description = "UT: C++20 single header/module micro unit-test framework"
    license = "BSL-1.0"
    homepage = "https://github.com/boost-ext/ut"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/b/boost-ext-ut/2.3.1"
    topics = ("unit-testing", "header-only", "cpp20", "testing", "tdd")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "run_upstream_tests": [True, False],
        "build_upstream_examples": [True, False],
    }
    default_options = {
        "run_upstream_tests": True,
        "build_upstream_examples": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def configure(self):
        # header-only: package compatibility does not depend on cppstd;
        # consumers get C++20 through the Boost::ut target compile features.
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")
        if self.settings.compiler in ("clang", "gcc") and \
                Version(self.settings.compiler.version) < "9":
            raise ConanInvalidConfiguration(
                f"{self.ref} requires clang >= 9 or gcc >= 9 (upstream README)")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # pure header mode: the C++23 module wrapper needs CMake >= 4.0
        tc.cache_variables["BOOST_UT_DISABLE_MODULE"] = True
        # upstream CI sets this to NO everywhere: POST_BUILD runs artifacts by bare
        # name (POSIX sh does not search cwd -> Error 127); use ctest instead
        tc.cache_variables["BOOST_UT_ENABLE_RUN_AFTER_BUILD"] = False
        tc.cache_variables["BOOST_UT_BUILD_TESTS"] = bool(self.options.run_upstream_tests)
        tc.cache_variables["BOOST_UT_BUILD_EXAMPLES"] = bool(self.options.build_upstream_examples)
        tc.cache_variables["BOOST_UT_BUILD_BENCHMARKS"] = False
        tc.cache_variables["BOOST_UT_ENABLE_INSTALL"] = False
        tc.cache_variables["BOOST_UT_USE_WARNINGS_AS_ERORS"] = False
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.options.run_upstream_tests:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            if can_run(self):
                cmake.test()

    def package(self):
        copy(self, "ut.hpp", src=os.path.join(self.source_folder, "include", "boost"),
             dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "ut")
        self.cpp_info.set_property("cmake_target_name", "Boost::ut")
