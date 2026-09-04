#!/usr/bin/env python3
"""Conan recipe for the header-only Tessil sparse-map library."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SparseMapConan(ConanFile):
    name = "sparse-map"
    version = "0.7.0"
    description = "C++ implementation of a memory-efficient hash map and hash set"
    license = "MIT"
    homepage = "https://github.com/Tessil/sparse-map"
    url = "https://github.com/Tessil/sparse-map"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost.Test is a large test-only source tree; avoid copying it into a
    # second Conan build tree.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["test_sources"]["boost"],
            destination=os.path.join(self.source_folder, "_test_deps", "boost"),
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # CMake does not recognize OHOS as a built-in system name on the
            # device, while the Conan compiler target remains OHOS.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

        # The upstream CMake test project links Boost::unit_test_framework.
        # OHOS has no compatible Conan binary for that library, so compile the
        # unchanged six test translation units with Boost.Test's header-only
        # entry point.  The generated main.cpp is kept in the build folder.
        test_build = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(test_build, exist_ok=True)
        upstream_main = os.path.join(self.source_folder, "tests", "main.cpp")
        generated_main = os.path.join(test_build, "main.cpp")
        with open(upstream_main, encoding="utf-8") as source_file:
            main_text = source_file.read()
        main_text = main_text.replace(
            "<boost/test/unit_test.hpp>",
            "<boost/test/included/unit_test.hpp>",
        )
        with open(generated_main, "w", encoding="utf-8") as generated_file:
            generated_file.write(main_text)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        ) or {}
        cxx = compiler_executables.get("cpp", "clang++")
        boost_include = os.path.join(self.source_folder, "_test_deps", "boost")
        sparse_include = os.path.join(self.source_folder, "include")
        test_sources = [
            "custom_allocator_tests.cpp",
            "policy_tests.cpp",
            "popcount_tests.cpp",
            "sparse_map_tests.cpp",
            "sparse_set_tests.cpp",
        ]
        test_paths = [
            os.path.join(self.source_folder, "tests", filename)
            for filename in test_sources
        ]
        test_binary = os.path.join(test_build, "sparse_map_tests")
        compile_args = [
            cxx,
            "-std=c++17",
            "-O0",
            "-DTSL_DEBUG",
            "-UNDEBUG",
            "-DBOOST_DISABLE_THREADS",
            "-Wall",
            "-Wextra",
            "-Wold-style-cast",
            "-Werror",
            f"-isystem{boost_include}",
            f"-I{sparse_include}",
            generated_main,
            *test_paths,
            "-o",
            test_binary,
            "-pthread",
        ]
        self.run(" ".join(shlex.quote(str(arg)) for arg in compile_args))

        test_command = (
            f"{shlex.quote(test_binary)} --log_level=test_suite "
            "--color_output=no"
        )
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run cross-compiled upstream tests"
                )
            self.run(f"{shlex.quote(qemu)} {test_command}")
        else:
            self.run(test_command)

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
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "tsl-sparse-map")
        self.cpp_info.set_property("cmake_target_name", "tsl::sparse_map")
        self.cpp_info.builddirs.append(
            os.path.join("share", "cmake", "tsl-sparse-map")
        )
