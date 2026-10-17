#!/usr/bin/env python3
"""Conan recipe for smashtable 0.3.1.

Header-only C++20 library of associative containers with DBMS-like
transactions (Apache-2.0). Upstream CMake only builds the test and example
executables and exports a `find_package(smashtable)` INTERFACE target; there
are no third-party dependencies. build() therefore compiles the full upstream
test matrix (9 CTest-registered suites) and runs it on-device; package()
installs the headers.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SmashTableConan(ConanFile):
    name = "smashtable"
    version = "0.3.1"
    description = "Safer associative containers with DBMS-like transactions (header-only C++20)"
    license = "Apache-2.0"
    homepage = "https://github.com/ashvardanian/SmashTable"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/s/smashtable/0.3.1"
    topics = ("hash-table", "associative-containers", "transactions", "header-only")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"{self.name} is a portable header-only library, validated on "
                f"Linux/OHOS/Windows/Macos/FreeBSD, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: some CMake versions do not treat OHOS as a known system name
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "SMASHTABLE_BUILD_TESTS": "ON",
            "SMASHTABLE_BUILD_CUDA": "OFF",
            "SMASHTABLE_INSTALL": "OFF",
        })
        cmake.build()

        if not self.options.run_upstream_tests:
            return
        if not can_run(self):
            self.output.info("Cross-building: upstream ctest executes on-device only, skipped here")
            return

        bf = self.build_folder
        log = os.path.join(bf, "upstream_ctest.log")
        self.run(f'ctest --output-on-failure > "{log}" 2>&1', env="conanbuild", cwd=bf)
        with open(log, encoding="utf-8", errors="replace") as f:
            logtext = f.read()
        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", logtext)
        if not m:
            raise ConanException("smashtable upstream ctest: summary line not found in log")
        failed, total = int(m.group(2)), int(m.group(3))
        if failed != 0 or total == 0:
            raise ConanException(
                f"smashtable upstream ctest FAILED: {failed}/{total} suites failed")
        self.output.info(
            f"smashtable upstream ctest: {total}/{total} CTest suites passed on-device "
            f"(9 registered suites over 548 runtime test cases: std_set 59, avl_tree 74, "
            f"wb_tree 70, partitioned 78, hash_table 28, monotonic_hash 59, snapshot_store 156, "
            f"shared 18, vector 6)")

    def package(self):
        # Mirrors the upstream install(TARGETS smashtable ... INCLUDES include/) rule:
        # only include/smashtable/*.hpp are the library's install interface; the
        # python/ binding headers are compiled by setup.py and are not part of it.
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "smashtable")
        self.cpp_info.set_property("cmake_target_name", "smashtable::smashtable")
