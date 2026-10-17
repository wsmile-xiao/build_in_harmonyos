#!/usr/bin/env python3
"""Conan test_package — wildmidi 0.5.0 L1 smoke test.

Consumer-perspective verification: links against the packaged library
(shared or static) and drives the full public API lifecycle with the
built-in OPL3 FM synthesizer — no GUS patch set or SoundFont needed
(config string "@opl3", see upstream docs/OPL3.md).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class WildmidiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary natively (build host == OHOS aarch64 device).
        # conanrun env provides library paths; dependency libdirs are
        # prepended so shared deps resolve without global installs.
        libpaths = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    libpaths.append(libdir)
        env = os.environ.copy()
        if libpaths:
            env["LD_LIBRARY_PATH"] = ":".join(libpaths) + ":" + env.get("LD_LIBRARY_PATH", "")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_wildmidi"),
                 env="conanrun")
