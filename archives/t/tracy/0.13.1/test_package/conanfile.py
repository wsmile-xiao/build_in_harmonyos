#!/usr/bin/env python3
"""Conan test_package for tracy 0.13.1 — consumes the client library as a
downstream project would: CMakeDeps provides the `tracy::tracy` target, the
transitive `TRACY_ENABLE` definition and the `include/tracy` header root.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TracyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The test binary is an aarch64 OHOS executable. When the recipe is built
        # from a desktop host (Windows/Linux x86_64) it cannot be executed here,
        # so it is only run by CI on the native OHOS worker.
        if cross_building(self):
            self.output.warning(
                "cross build (build != host): test_tracy was compiled and linked "
                "against the packaged library, but execution is deferred to the "
                "native OHOS CI worker"
            )
            return

        self.run(os.path.join(self.cpp.build.bindir, "test_tracy"), env="conanrun")
