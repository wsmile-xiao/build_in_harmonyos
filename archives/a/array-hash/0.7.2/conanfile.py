#!/usr/bin/env python3
"""Conan recipe for array-hash 0.7.2, a header-only string hash map/set."""

import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ArrayHashConan(ConanFile):
    name = "array-hash"
    version = "0.7.2"
    description = "Fast and memory-efficient hash map and set specialized for strings"
    license = "MIT"
    homepage = "https://github.com/Tessil/array-hash"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The upstream suite uses Boost.Test.  The header-only entry point
        # means only Boost headers are needed; no Boost library is linked.
        self.tool_requires("boost/1.90.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.compiler.cppstd:
            from conan.tools.build import check_min_cppstd

            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "11"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        if self.settings.os in ("Linux", "OHOS"):
            # Keep CMake's platform logic usable with the OHOS Conan profile.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Configure the upstream install target.  The project is INTERFACE
        # only, so this validates its CMake package configuration without
        # inventing a library build.
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

        # The upstream tests link Boost::unit_test_framework.  The OHOS
        # Boost package is consumed for headers only, and the patch changes
        # main.cpp to the header-only Boost.Test entry point.  Compile the
        # exact upstream translation units directly so all upstream cases run.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        compiler = compiler_executables.get("cpp") or "c++"
        boost_package = self.dependencies.build["boost"].package_folder
        boost_include = os.path.join(boost_package, "include")
        include_dir = os.path.join(self.source_folder, "include")
        test_dir = os.path.join(self.source_folder, "tests")
        test_binary = os.path.join(self.build_folder, "tsl_array_hash_tests")
        test_sources = [
            os.path.join(test_dir, "main.cpp"),
            os.path.join(test_dir, "array_bucket_test.cpp"),
            os.path.join(test_dir, "array_map_tests.cpp"),
            os.path.join(test_dir, "array_set_tests.cpp"),
            os.path.join(test_dir, "policy_tests.cpp"),
        ]
        link_flags = "-static" if self.settings.os == "OHOS" else ""
        command = "{} -std=c++11 -O3 -Werror -Wall -Wextra " \
            "-Wold-style-cast -DTSL_DEBUG -DBOOST_DISABLE_THREADS " \
            "-isystem {} -I {} {} {} -o {}".format(
                shlex.quote(str(compiler)),
                shlex.quote(boost_include),
                shlex.quote(include_dir),
                " ".join(shlex.quote(path) for path in test_sources),
                link_flags,
                shlex.quote(test_binary),
            )
        self.run(command)
        self.run(f'"{test_binary}" --log_level=test_suite')

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "tsl-array-hash")
        self.cpp_info.set_property("cmake_target_name", "tsl::array_hash")
