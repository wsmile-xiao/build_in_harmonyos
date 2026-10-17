#!/usr/bin/env python3
"""Conan recipe for libdart 1.4.0 — header-only C++14 JSON library with optional C ABI.

libdart (Dart) is a wire-level binary JSON protocol library with a header-only
C++14 interface and an ABI-stable C89 binding layer. The public headers depend
on Microsoft GSL (gsl::span); RapidJSON and libyaml enable optional JSON/YAML
connector features plus their upstream tests.

The upstream CMake project declares cmake_minimum_required(3.1.0), which modern
CMake (>=4.0) rejects without CMAKE_POLICY_VERSION_MINIMUM; the recipe injects
the policy override and dependency include paths so the full upstream test
suite (unit_tests / json_test / yaml_test / abi_tests) builds and runs under
the OHOS toolchain. Upstream tests execute inside build() so conan create
produces HMBS upstream-test evidence on every run.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibdartConan(ConanFile):
    name = "libdart"
    version = "1.4.0"
    description = "A high performance, network optimized, binary JSON protocol and C++ library"
    license = "MIT"
    homepage = "https://github.com/target/libdart"
    url = "https://github.com/target/libdart"
    topics = ("json", "binary-json", "serialization", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libdart supports Linux/OHOS only")
        check_min_cppstd(self, 14)

    def requirements(self):
        # Public headers include <gsl/span> (Microsoft GSL header-only).
        self.requires("ms-gsl/4.2.1")

    def build_requirements(self):
        # Test-time only: rapidjson (json_test) and libyaml (yaml_test).
        self.test_requires("rapidjson/1.1.0")
        self.test_requires("libyaml/0.2.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream requires CMake >= 3.1; CMake >= 4.0 dropped <3.5 compatibility.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Full upstream test/ABI configuration.
        tc.variables["test"] = "ON"
        tc.variables["build_abi"] = "ON"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Let find_path/find_library see the conan-provided headers/libs.
        inc_dirs = []
        lib_dirs = []
        for dep_name in ("ms-gsl", "rapidjson", "libyaml"):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                continue
            for d in dep.cpp_info.includedirs:
                inc_dirs.append(os.path.join(dep.package_folder, d))
            for d in dep.cpp_info.libdirs:
                lib_dirs.append(os.path.join(dep.package_folder, d))
        if inc_dirs:
            tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(inc_dirs)
            # yaml.h is included by include/dart/common.h when DART_HAS_YAML is on,
            # so the include dir must also reach the compiler command line.
            tc.variables["CMAKE_CXX_FLAGS"] = " ".join("-I" + d for d in inc_dirs)
            tc.variables["CMAKE_C_FLAGS"] = " ".join("-I" + d for d in inc_dirs)
        if lib_dirs:
            tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join("-L" + d for d in lib_dirs)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the full upstream suite: dart_unit_tests/json/yaml/abi (243 cases).
        self.run(f"ctest --test-dir {self.build_folder} --output-on-failure",
                 ignore_errors=False)

    def package(self):
        copy(self, "dart.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "dart"),
             dst=os.path.join(self.package_folder, "include", "dart"))
        copy(self, "*.tcc",
             src=os.path.join(self.source_folder, "include", "dart"),
             dst=os.path.join(self.package_folder, "include", "dart"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdart")
        self.cpp_info.set_property("cmake_target_name", "libdart::libdart")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only: nothing to link.
        self.cpp_info.libs = []
