#!/usr/bin/env python3
"""Conan test_package — iproute2 6.11.0 (L1 official test).

iproute2 is a command-line tool set (not a library). The L1 test therefore
verifies the installed `ip` binary runs and reports the expected version,
rather than linking a library.

R34: test.c calls `ip -V` via popen() and checks the output contains
"iproute2-6.11.0". The binary path is passed via the IP_BIN CMake variable,
which CTest exposes to the test binary as the IP_PATH env var.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Iproute2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Deferred to test() where the dependency package_folder is available.
        pass

    def test(self):
        cmake = CMake(self)
        ip = os.path.join(self.dependencies["iproute2"].package_folder, "bin", "ip")
        cmake.configure(variables={"IP_BIN": ip})
        cmake.build()
        cmake.test()
        # Also verify the binary runs directly.
        if os.path.exists(ip):
            self.run(f'"{ip}" -V')
        else:
            self.run("ip -V", env=["conanrun"])
