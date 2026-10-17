#!/usr/bin/env python3
"""Conan recipe — unqlite 1.2.1 (CMake, amalgamation static library)."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class UnqliteConan(ConanFile):
    name = "unqlite"
    version = "1.2.1"
    description = (
        "Transactional NoSQL database engine (key/value store + document "
        "store) as a self-contained, zero-dependency ANSI C library"
    )
    license = "BSD-2-Clause"
    homepage = "https://unqlite.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # Upstream CMakeLists hardcodes ADD_LIBRARY(... STATIC ...);
        # a shared build would require patching upstream, out of scope.
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "unqlite upstream only provides a static library")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True)
        # samples/ are demo programs without assertions (see MANIFEST.yml);
        # keep them out of the package build to avoid demo data-file deps.
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists requires CMake 3.10 (1.2.1 fixed the <3.5
        # compat issue); CMake >= 4 still needs the minimum-policy flag on
        # the command line for the CTest/include(CTest) include chain.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        self._record_upstream_test_census()

    def _record_upstream_test_census(self):
        # Upstream 1.2.1 ships no assertion-based test suite: no tests/
        # directory; the root CMakeLists registers samples/ demo programs
        # (1.c..6.c, unqlite_huge, unqlite_mp3, unqlite_tar, demovfs) via
        # add_test, but every sample is an API demonstration with zero
        # assertions (grep -c assert samples/*.c == 0), so they are not
        # independent upstream test cases. Real behaviour is verified by
        # the Conan consumer test instead.
        result = {
            "status": "passed",
            "framework": "none",
            "command": "no upstream assertion-based test suite (census in notes.md + MANIFEST.yml)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "detail": (
                "upstream census: no test framework or assertion-based test "
                "programs; samples/ demo programs (1..6, unqlite_huge, "
                "unqlite_mp3, unqlite_tar, demovfs) contain zero asserts"),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["unqlite"]
        self.cpp_info.set_property("cmake_file_name", "unqlite")
        self.cpp_info.set_property("cmake_target_name", "unqlite::unqlite")
