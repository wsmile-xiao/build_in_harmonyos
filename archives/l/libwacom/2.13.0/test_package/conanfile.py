#!/usr/bin/env python3
"""Conan test_package for libwacom 2.13.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibwacomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeDeps synthesizes the libwacomConfig.cmake from package_info
        # (the upstream meson build does not install cmake config files).
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Bake the installed database dir into the CTest definition at
        # configure time (plain cmake variable, not $ENV{} which is only
        # expanded if the var is set when cmake configures).
        pkg = self.dependencies["libwacom"].package_folder
        tc.variables["LIBWACOM_DATA_DIR"] = os.path.join(pkg, "share", "libwacom")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # test_libwacom takes the database directory as argv[1] (baked
        # into the CTest definition via the LIBWACOM_DATA_DIR toolchain
        # variable) and links against libwacom.so.9 from the package
        # folder; inject the loader path for the ctest child process.
        pkg = self.dependencies["libwacom"].package_folder
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run("ctest --test-dir . --output-on-failure --no-tests=error")
