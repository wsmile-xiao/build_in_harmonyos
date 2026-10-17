#!/usr/bin/env python3
"""Conan recipe for semver 1.0.1.

semver is a header-only C++17 library for Semantic Versioning 2.0.0.
Upstream ships doctest-based tests in test/. We compile the full upstream
main test target (test.cpp provides the doctest main; 8 suite files carry
the 98 TEST_CASEs) and run it.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SemverConan(ConanFile):
    name = "semver"
    version = "1.0.1"
    description = "Header-only C++17 library for Semantic Versioning 2.0.0"
    license = "MIT"
    homepage = "https://github.com/Neargye/semver"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/s/semver/1.0.1"
    topics = ("semver", "versioning", "header-only", "cpp17")
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
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            return
        if not can_run(self):
            self.output.info("Cross-building: skip upstream test execution")
            return

        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = exes.get("cpp") or "clang++"
        sf = self.source_folder
        inc = os.path.join(sf, "include")
        tp = os.path.join(sf, "test", "3rdparty", "doctest")
        flags = "-std=c++17 -O2"

        # Upstream main test target (test/CMakeLists.txt SOURCES): test.cpp
        # provides the doctest main; the 8 suite files carry the 98 TEST_CASEs.
        # test_config.cpp needs a SEMVER_CONFIG_FILE override (separate target)
        # and test_windows_minmax.cpp is MSVC-frontend-only: both excluded.
        suite = [
            "test.cpp",
            "test_operators.cpp",
            "test_parse.cpp",
            "test_ranges.cpp",
            "test_to_string.cpp",
            "test_validation.cpp",
            "test_api.cpp",
            "test_advanced_ranges.cpp",
            "test_edge_cases.cpp",
        ]
        srcs = " ".join('"%s"' % os.path.join(sf, "test", s) for s in suite)
        out = os.path.join(self.build_folder, "semver_tests")
        self.output.info("Compiling upstream doctest suite (%d files)" % len(suite))
        self.run(f'"{cxx}" {flags} -DDOCTEST_CONFIG_USE_STD_HEADERS -I"{inc}" -I"{tp}" {srcs} -o "{out}"', env="conanbuild")
        self.output.info("Running upstream test suite")
        self.run(f'"{out}"', env="conanbuild")

    def package(self):
        copy(self, "semver.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "semver::semver")
