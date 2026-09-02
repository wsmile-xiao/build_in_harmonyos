#!/usr/bin/env python3
"""Conan recipe for hat-trie 0.7.1, a header-only HAT-trie library."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class HatTrieConan(ConanFile):
    name = "hat-trie"
    version = "0.7.1"
    description = "Fast and memory-efficient HAT-trie for strings (header-only)"
    license = "MIT"
    homepage = "https://github.com/Tessil/hat-trie"
    url = "https://github.com/Tessil/hat-trie"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    # The test-only Boost source is large; build directly from Conan's source
    # folder instead of copying the complete source tree into the build folder.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "11")

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
        boost_include = os.path.join(self.source_folder, "_test_deps", "boost")
        tc.extra_cxxflags.append(f"-isystem{boost_include}")
        tc.extra_cxxflags.append("-DBOOST_DISABLE_THREADS")
        if self.settings.os in ("Linux", "OHOS"):
            # Some CMake versions do not recognize OHOS as a system name.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Configure/build the header-only upstream target first.
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

        # The upstream test CMake project unconditionally finds and links the
        # compiled Boost.Test library. Compile its same three translation units
        # directly instead, using header-only Boost.Test after the main.cpp
        # patch. This keeps the upstream cases and assertions unchanged while
        # avoiding a test-only Conan dependency and fragile CMake context.
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}
        ).get("cpp", "clang++")
        test_sources = [
            os.path.join(self.source_folder, "tests", "main.cpp"),
            os.path.join(self.source_folder, "tests", "trie_map_tests.cpp"),
            os.path.join(self.source_folder, "tests", "trie_set_tests.cpp"),
        ]
        boost_include = os.path.join(self.source_folder, "_test_deps", "boost")
        test_binary = os.path.join(self.build_folder, "tsl_hat_trie_tests")
        command = "{} -std=c++11 -O3 -Werror -Wall -Wextra " \
            "-Wold-style-cast -DTSL_DEBUG -DBOOST_DISABLE_THREADS " \
            "-isystem {} -I {} {} -o {}".format(
                shlex.quote(str(compiler)),
                shlex.quote(boost_include),
                shlex.quote(os.path.join(self.source_folder, "include")),
                " ".join(shlex.quote(path) for path in test_sources),
                shlex.quote(test_binary),
            )
        self.run(command)
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run upstream OHOS tests"
                )
            self.run(f'"{qemu}" "{test_binary}" --log_level=test_suite')
        else:
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

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "tsl-hat-trie")
        self.cpp_info.set_property("cmake_target_name", "tsl::hat_trie")
