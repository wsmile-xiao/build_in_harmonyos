#!/usr/bin/env python3
"""Conan recipe — tsl-ordered-map 1.1.0 (CMake header-only / INTERFACE library).

Downstream expects (upstream CMake export):
  find_package(tsl-ordered-map REQUIRED)
  target_link_libraries(... PRIVATE tsl::ordered_map)

Reference: archives/r/robin-map/1.4.1/ (same-family Tessil header-only CMake pattern).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TslOrderedMapConan(ConanFile):
    name = "tsl-ordered-map"
    version = "1.1.0"
    description = "C++ implementation of a fast hash map and hash set with deterministic key ordering"
    license = "MIT"
    homepage = "https://github.com/Tessil/ordered-map"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

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
        # Upstream declares cmake_minimum_required(VERSION 3.1); newer CMake
        # (>= 3.5) removed compatibility with < 3.5, so opt back in.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        boost_include = os.path.join(self.source_folder, "_test_deps", "boost")
        tc.extra_cxxflags.append(f"-isystem{boost_include}")
        tc.extra_cxxflags.append("-DBOOST_DISABLE_THREADS")
        # R32: platform check must accept OHOS
        if self.settings.os in ("Linux", "OHOS"):
            # E092: some CMake versions do not treat OHOS as a known system name
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            # Conan arch is "armv8"; CMake expects "aarch64" (E092)
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Static executables can run under qemu-user without a full OHOS rootfs.
            tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Isolate upstream tests from the main library build tree.
        main_build = self.folders.build
        self.folders.build = os.path.join(main_build, "upstream-tests")
        try:
            toolchain = os.path.join(
                self.generators_folder, "conan_toolchain.cmake"
            ).replace("\\", "/")
            upstream_tests = CMake(self)
            upstream_tests.configure(
                build_script_folder="tests",
                variables={"CMAKE_TOOLCHAIN_FILE": toolchain},
            )
            upstream_tests.build()
        finally:
            self.folders.build = main_build

        test_binary = os.path.join(
            self.build_folder, "upstream-tests", "tsl_ordered_map_tests"
        )
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
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Header-only: no link libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]

        # Prefer upstream Config.cmake so find_package(tsl-ordered-map) matches
        # the upstream CMake project name and tsl::ordered_map target.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "tsl-ordered-map")
        self.cpp_info.set_property("cmake_target_name", "tsl::ordered_map")
        # GNUInstallDirs DATAROOTDIR layout from upstream CMakeLists.txt
        self.cpp_info.builddirs.append(os.path.join("share", "cmake", "tsl-ordered-map"))