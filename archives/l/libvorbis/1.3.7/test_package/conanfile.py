#!/usr/bin/env python3
"""Consumer smoke test for libvorbis."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibvorbisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        smoke_binary = os.path.join(
            self.build_folder,
            self.cpp.build.bindir,
            "test_libvorbis",
        )
        self.run(smoke_binary, env="conanrun")

        upstream_binary = os.path.join(
            self.build_folder,
            self.cpp.build.bindir,
            "libvorbis_upstream_test",
        )
        runtime_dir = os.path.join(self.build_folder, "upstream-test-runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        self.run(upstream_binary, cwd=runtime_dir, env="conanrun")
