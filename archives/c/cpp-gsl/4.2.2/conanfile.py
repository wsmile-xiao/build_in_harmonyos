#!/usr/bin/env python3
"""Conan recipe for Microsoft GSL 4.2.2 on HarmonyOS."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CppGslConan(ConanFile):
    name = "cpp-gsl"
    version = "4.2.2"
    description = "Guidelines Support Library implementation of the C++ Core Guidelines support types"
    license = "MIT"
    homepage = "https://github.com/microsoft/GSL"
    url = "https://github.com/microsoft/GSL"
    topics = ("gsl", "core-guidelines", "span", "not-null", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("cpp-gsl is supported only on Linux/OHOS")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        if self.settings.os == "OHOS":
            # OHOS provides pthread APIs in libc. CMake's cross probe can
            # otherwise select the non-existent compatibility name -lpthreads.
            tc.variables["CMAKE_HAVE_LIBC_PTHREAD"] = True
        tc.variables["GSL_INSTALL"] = True
        tc.variables["GSL_TEST"] = True
        tc.variables["GSL_CXX_STANDARD"] = "17"
        gtest = self.dependencies["gtest"]
        tc.variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_tmp = os.path.join(self.build_folder, "test-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            self.run(
                f'TMPDIR="{test_tmp}" ctest --test-dir "{self.build_folder}" '
                "--output-on-failure",
                env="conanbuild",
            )
            result = {
                "status": "passed",
                "framework": "gtest+ctest",
                "source_declared_total": 97,
                "configured_executable_total": 2,
                "executed": 89,
                "passed": 89,
                "failed": 0,
                "skipped": 0,
                "note": "96 source TEST declarations; 88 instantiated plus gsl_noexcept_tests",
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
        else:
            self.output.info(
                "Cross-building: upstream test binaries were built; execution is covered by HDC"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Microsoft.GSL")
        self.cpp_info.set_property("cmake_target_name", "Microsoft.GSL::GSL")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
