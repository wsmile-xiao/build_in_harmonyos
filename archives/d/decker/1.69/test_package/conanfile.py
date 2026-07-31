#!/usr/bin/env python3
"""Conan test_package for Decker — verifies lilt binary runs correctly.

Tests that the lilt standalone interpreter binary was properly installed
and can execute a basic Lil script.

Path resolution: decker is an application package (cpp_info.bindirs=["bin"]).
We pass the bindir to CMake in two complementary ways:
  1. CMakeToolchain defines `DECKER_BIN_DIRS` (from cpp_info.bindirs) so
     CMakeLists.txt can bake LILT_DEFAULT_BIN into the test binary.
  2. At test() time we set the LILT_BIN environment variable so the test
     binary can also read it at runtime (belt-and-suspenders).
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class DeckerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeToolchain must always be generated so cmake.configure() works.
        tc = CMakeToolchain(self)
        # Hand the decker bindir to CMake as a plain variable so CMakeLists.txt
        # can turn it into the LILT_DEFAULT_BIN compile-time macro.
        decker = self.dependencies["decker"]
        bin_dirs = decker.cpp_info.aggregated_components().bindirs
        if bin_dirs:
            tc.variables["DECKER_BIN_DIRS"] = bin_dirs[0]
        tc.generate()

        # R34: emit LILT_BIN into a dedicated env script so self.run() in
        # test() automatically picks it up via the env file list argument.
        # Conan 2.x self.run(env=...) takes a list of env *file names*, not
        # a dict; Environment() + vars(self).save_script() is the canonical
        # way to emit custom env vars into those env files.
        lilt_path = os.path.join(bin_dirs[0], "lilt") if bin_dirs else "lilt"
        env = Environment()
        env.define("LILT_BIN", lilt_path)
        env.vars(self).save_script("lilt_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: run the compiled test binary directly with self.run().
        # Pass env=["lilt_env", "conanrun"] so both the LILT_BIN emitted above
        # and the conanrun env (PATH etc.) are applied to the subprocess.
        # Conan 2.x requires env to be a list of env *file names*, not a dict.
        test_bin = os.path.join(self.cpp.build.bindir, "test_decker")
        self.run(f'"{test_bin}"', env=["lilt_env", "conanrun"], scope="run")
