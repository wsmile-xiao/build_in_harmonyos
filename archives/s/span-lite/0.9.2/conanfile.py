#!/usr/bin/env python3
"""Conan recipe for span-lite 0.9.2.

span-lite is a header-only C++ library providing std::span-like functionality
for C++98/11/14/17/20. Upstream tests use the vendored lest framework.
We compile and run the upstream test suite in build().
"""
import os, glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SpanLiteConan(ConanFile):
    name = "span-lite"
    version = "0.9.2"
    description = "A C++20-like span for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/span-lite"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/s/span-lite/0.9.2"
    topics = ("span", "header-only", "cpp")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": False}

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
        tp = os.path.join(sf, "test", "lest")
        flags = "-std=c++11 -O2 -Dspan_FEATURE_MAKE_SPAN_TO_STD=99 -Dspan_FEATURE_WITH_CONTAINER_TO_STD=99"

        # Compile span-main.t.cpp (has lest main) + span.t.cpp into one executable
        test_dir = os.path.join(sf, "test")
        main_cpp = os.path.join(test_dir, "span-main.t.cpp")
        test_cpp = os.path.join(test_dir, "span.t.cpp")
        out = os.path.join(self.build_folder, "span_lite_tests")
        self.output.info("Compiling upstream test suite")
        tn = os.path.join(sf, "test", "nonstd")
        self.run(f'"{cxx}" {flags} -I"{inc}" -I"{tp}" -I"{tn}" -I"{os.path.join(sf, "test")}" -Dlest_FEATURE_AUTO_REGISTER=1 "{main_cpp}" "{test_cpp}" -o "{out}"', env="conanbuild")
        self.output.info("Running upstream test suite")
        self.run(f'"{out}"', env="conanbuild")

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "nonstd::span-lite")
