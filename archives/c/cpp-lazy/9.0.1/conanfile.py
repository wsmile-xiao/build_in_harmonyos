#!/usr/bin/env python3
"""Conan recipe for cpp-lazy 9.0.1 on HarmonyOS PC."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CppLazyConan(ConanFile):
    name = "cpp-lazy"
    version = "9.0.1"
    description = "Fast header-only library for lazy evaluation and iterator tools"
    license = "MIT"
    homepage = "https://github.com/Kaaserne/cpp-lazy"
    url = "https://github.com/Kaaserne/cpp-lazy"
    topics = ("lazy-evaluation", "iterators", "ranges", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    # The registry publishes the OHOS shared package for this profile. Pin the
    # supported option so clean workers download it instead of rebuilding the
    # unavailable static variant from GitHub sources.
    default_options = {"fmt/*:shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream enables formatting by default and exposes fmt through its
        # INTERFACE target. Keep that public behavior for Conan consumers.
        self.requires("fmt/12.2.0")

    def build_requirements(self):
        # Test-only dependency used by all 47 upstream test translation units.
        # 2.4.11 is API-compatible with upstream's requested 2.4.12; doctest
        # 2.5.x adds the same volatile-pointer specialization as this suite.
        self.test_requires("doctest/2.4.11")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        check_min_cppstd(self, 11)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = str(self.settings.compiler.cppstd or 17)
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.cache_variables["CPP_LAZY_USE_STANDALONE"] = False
        tc.cache_variables["CPP_LAZY_USE_INSTALLED_FMT"] = True
        tc.cache_variables["CPP_LAZY_FMT_DEP_VERSION"] = "12.2.0"
        tc.cache_variables["CPP_LAZY_USE_MODULES"] = False
        tc.cache_variables["CPP_LAZY_DEBUG_ASSERTIONS"] = False
        tc.cache_variables["CPP_LAZY_INSTALL"] = True
        tc.cache_variables["TEST_INSTALLED_VERSION"] = False

        if self.settings.os == "OHOS":
            # Use CMake's Platform/OHOS.cmake while retaining Conan's OHOS
            # compiler selection and aarch64 target triple.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"

            # The SDK injects --gcc-toolchain although the OHOS driver does
            # not consume it. Clang 15 also predates an upstream warning flag.
            # Silence only these driver/version diagnostics so upstream's
            # strict -Werror test policy remains otherwise intact.
            tc.extra_cxxflags.extend([
                "-Wno-unused-command-line-argument",
                "-Wno-unknown-warning-option",
            ])

            if cross_building(self):
                qemu = shutil.which("qemu-aarch64")
                if not qemu:
                    raise ConanInvalidConfiguration(
                        "qemu-aarch64 is required to run the cpp-lazy upstream tests"
                    )
                tc.cache_variables["CMAKE_CROSSCOMPILING_EMULATOR"] = qemu

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "tests"))
        cmake.build(build_tool_args=["-j1"])
        self.run(
            "ctest --test-dir . --output-on-failure --no-tests=error",
            cwd=self.build_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpp-lazy")
        self.cpp_info.set_property("cmake_target_name", "cpp-lazy::cpp-lazy")
        self.cpp_info.set_property("pkg_config_name", "cpp-lazy")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
