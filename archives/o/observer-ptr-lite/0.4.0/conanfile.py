#!/usr/bin/env python3
"""Conan recipe for observer-ptr-lite 0.4.0.

observer-ptr-lite is a header-only C++ library providing a non-owning
observer pointer (std::experimental::observer_ptr-like) for C++98/11 and later.
Upstream ships a lest-based test suite. We compile and run it in build();
verified to pass (37 tests) on OHOS/aarch64.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ObserverPtrLiteConan(ConanFile):
    name = "observer-ptr-lite"
    version = "0.4.0"
    description = "A C++17-like observer_ptr (non-owning pointer) for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/observer-ptr-lite"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/observer-ptr-lite/0.4.0"
    topics = ("observer_ptr", "header-only", "cpp")
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
        tp = os.path.join(sf, "test")
        flags = "-std=c++11 -O2"

        # Compile the lest test suite (main + tests) into one executable.
        main_cpp = os.path.join(tp, "observer-ptr-main.t.cpp")
        test_cpp = os.path.join(tp, "observer-ptr.t.cpp")
        out = os.path.join(self.build_folder, "observer_ptr_tests")
        self.output.info("Compiling upstream lest test suite")
        self.run(f'"{cxx}" {flags} -I"{inc}" -I"{tp}" -Dlest_FEATURE_AUTO_REGISTER=1 "{main_cpp}" "{test_cpp}" -o "{out}"', env="conanbuild")
        self.output.info("Running upstream lest test suite")
        self.run(f'"{out}" --pass', env="conanbuild")

    def package(self):
        copy(self, "observer_ptr.hpp", src=os.path.join(self.source_folder, "include", "nonstd"),
             dst=os.path.join(self.package_folder, "include", "nonstd"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "nonstd::observer-ptr-lite")
