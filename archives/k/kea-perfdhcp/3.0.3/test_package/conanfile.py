#!/usr/bin/env python3
"""Conan consumer test for kea-perfdhcp 3.0.3.

Three checks run against the packaged client:

* ``test_perfdhcp.py``   — consumer contract: version/usage output, the option
  parser error path and one real DHCPv6 exchange attempt (proves the process
  loads its Kea runtime libraries and walks the whole benchmark code path);
* ``test_ohos_platform`` — HarmonyOS-specific: the packaged executable carries
  the OHOS aarch64 / musl / libc++ platform ABI signature;
* ``test_ohos_runtime``  — HarmonyOS-specific: the packaged Kea runtime closure
  (libkea-*.so*) is resolvable by the OHOS loader and the client runs.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaPerfdhcpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        if not can_run(self):
            self.output.info("cross-building: perfdhcp consumer tests skipped")
            return

        perfdhcp = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "perfdhcp")
        bindir = self.cpp.build.bindirs[0]

        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, perfdhcp),
                 env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, perfdhcp),
                 env="conanrun")

        test_script = os.path.join(self.source_folder, "test_perfdhcp.py")
        self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
