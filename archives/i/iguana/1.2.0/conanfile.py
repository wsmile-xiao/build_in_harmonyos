#!/usr/bin/env python3
"""Conan recipe for iguana 1.2.0 (header-only, upstream v1.2.0).

iguana is a universal serialization engine: a reflection-based C++ library that
(de)serializes plain structs to/from JSON, XML and YAML without hand-written
mapping code. The library is header-only and has no external dependencies.

The package ships ``include/iguana`` plus the vendored ``frozen`` headers that
``iguana/field_reflection.hpp`` includes. The build step configures the upstream
CMake tree and executes the upstream doctest suite through ctest, so the OHOS
package is validated by the upstream test suite itself.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs, can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class IguanaConan(ConanFile):
    name = "iguana"
    version = "1.2.0"
    package_type = "header-library"
    description = ("universal serialization engine: reflection based JSON/XML/YAML "
                   "(de)serialization for plain C++ structs")
    license = "Apache-2.0"
    homepage = "https://github.com/qicosmos/iguana"
    url = ("https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/i/iguana/1.2.0")
    topics = ("serialization", "reflection", "json", "xml", "yaml", "header-only")

    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.cache_variables["BUILD_UNIT_TESTS"] = bool(self.options.run_upstream_tests)
        # The upstream tree also builds its benchmark targets by default; keep
        # them at low optimisation so the validation build stays fast.
        tc.cache_variables["IGUANA_FAST_BENCHMARK_COMPILE"] = True
        tc.cache_variables["LINKLIBC++"] = (
            "ON" if self.settings.compiler.get_safe("libcxx") == "libc++" else "OFF")
        if self.settings.os in ("Linux", "OHOS"):
            # E092: CMake does not ship a Platform/HarmonyOS module, so pin the
            # generic Linux platform for the OHOS toolchain.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests and can_run(self):
            # Conan's CMake.test() forwards cli_args to the native build tool
            # (make/ninja) instead of ctest, so call ctest directly to keep
            # --output-on-failure meaningful for the upstream suite.
            self.run("ctest --output-on-failure -j%s" % build_jobs(self),
                     cwd=self.build_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Header-only: ship the public iguana headers and the vendored frozen
        # headers that field_reflection.hpp pulls in. Layout keeps the include
        # root so that "iguana/..." and "frozen/..." both resolve.
        for pattern in ("*.h", "*.hpp", "*.hxx", "*.inl", "*.ipp"):
            copy(self, pattern, src=os.path.join(self.source_folder, "iguana"),
                 dst=os.path.join(self.package_folder, "include", "iguana"), keep_path=True)
            copy(self, pattern, src=os.path.join(self.source_folder, "frozen"),
                 dst=os.path.join(self.package_folder, "include", "frozen"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "iguana")
        self.cpp_info.set_property("cmake_target_name", "iguana::iguana")
