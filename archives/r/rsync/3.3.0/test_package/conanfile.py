#!/usr/bin/env python3
"""Conan test_package — rsync 3.3.0.

rsync is a command-line tool. The L1 test verifies the installed binary
runs correctly by checking `rsync --version` output.

R34: test.c calls rsync --version via popen() and verifies "version 3.3.0"
is in the output. The rsync binary path is passed via RSYNC_BIN CMake variable,
which CTest sets as RSYNC_PATH env var for the test binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RsyncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Configure and build are deferred to test() where RSYNC_BIN is available
        pass

    def test(self):
        cmake = CMake(self)
        # Pass rsync binary path to CMake so CTest can set RSYNC_PATH env var
        rsync = os.path.join(self.dependencies["rsync"].package_folder, "bin", "rsync")
        cmake.configure(variables={"RSYNC_BIN": rsync})
        cmake.build()
        cmake.test()
        # Also verify rsync binary runs directly
        if os.path.exists(rsync):
            self.run(f'"{rsync}" --version')
        else:
            self.run("rsync --version", env=["conanrun"])
