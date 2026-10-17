#!/usr/bin/env python3
"""Conan test_package for libexadrums 0.7.0 (OHOS).

Consumer-side smoke test: real calls into the public API.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibexadrumsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Pull minizip/tinyxml2 in as DIRECT deps so their CMakeDeps targets and
        # lib dirs are available.  libexadrums.so NEEDEDs them, and the framework
        # sets CMAKE_SKIP_RPATH, so the bare test binary cannot resolve them at
        # load time; we fix that with an explicit LD_LIBRARY_PATH in test() (see
        # below) rather than relying on the auto-aggregated "conanrun" env, which
        # drops minizip when it is both a direct and a transitive dependency.
        self.requires("minizip/1.3.1")
        self.requires("tinyxml2/11.0.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The framework sets CMAKE_SKIP_RPATH, so the bare test binary cannot
        # resolve libexadrums.so and its transitive libminizip/libtinyxml2 at
        # load time.  The auto-aggregated "conanrun" run env drops minizip
        # (it is both a direct and a transitive dependency), so build an explicit
        # LD_LIBRARY_PATH over *every* dependency lib dir and save it into the
        # run scope, where it merges into the aggregated "conanrun" env used by
        # test() below.  self.run()'s env= accepts a list of env names only.
        runenv = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                runenv.prepend_path("LD_LIBRARY_PATH", libdir)
        runenv.vars(self, scope="run").save_script("conanrun_libdirs")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_libexadrums")
            self.run(bin_path, env=["conanrun"])
