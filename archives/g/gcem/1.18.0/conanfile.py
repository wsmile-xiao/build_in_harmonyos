#!/usr/bin/env python3
"""Conan recipe for gcem 1.18.0 — header-only C++11 math library."""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GcemConan(ConanFile):
    name = "gcem"
    version = "1.18.0"
    description = "C++11 constexpr mathematical functions library (header-only)"
    license = "Apache-2.0"
    homepage = "https://github.com/kthohr/gcem"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GCEM only includes the C++ standard library and has no third-party
        # Conan dependencies.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: keep the recipe valid for Linux and OHOS profiles.  The OHOS
        # CMake platform module expects the aarch64 processor spelling.
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(
                self.settings.os
            )
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = (
                    "aarch64"
                )

        # CMake 4 no longer accepts projects whose minimum is below 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["GCEM_BUILD_TESTS"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="gcem_tests")

        # The upstream tests/CMakeLists.txt creates 46 standalone executables,
        # but does not call enable_testing()/add_test().  Run every executable
        # explicitly so the full upstream suite is part of conan create.
        test_binaries = sorted(
            glob.glob(os.path.join(self.build_folder, "tests", "*.test"))
        )
        if not test_binaries:
            raise RuntimeError("GCEM_BUILD_TESTS produced no upstream test binaries")
        expected_test_count = 46
        if len(test_binaries) != expected_test_count:
            raise RuntimeError(
                "Expected %d upstream test binaries, found %d"
                % (expected_test_count, len(test_binaries))
            )
        self.output.info(
            "GCEM_UPSTREAM_TESTS_REGISTERED=%d" % len(test_binaries)
        )
        for index, test_binary in enumerate(test_binaries, 1):
            self.output.info(
                "GCEM_UPSTREAM_TEST[%d/%d]=%s"
                % (index, len(test_binaries), os.path.basename(test_binary))
            )
            self.run('"%s"' % test_binary, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "gcem")
        self.cpp_info.set_property("cmake_target_name", "gcem::gcem")
