#!/usr/bin/env python3
"""Conan consumer test for kea-dhcp4 3.0.3.

Three checks run against the packaged server:

* ``test_dhcp4.py``      — consumer contract: version / extended-version /
  configuration-report output, the command-line error paths and the
  configuration-check mode (-t) accepting a minimal DHCPv4 configuration and
  rejecting broken ones (proves the process loads its Kea runtime libraries
  and walks the whole configuration path without opening sockets);
* ``test_ohos_platform`` — HarmonyOS-specific: the packaged executable carries
  the OHOS aarch64 / musl / libc++ platform ABI signature;
* ``test_ohos_runtime``  — HarmonyOS-specific: the packaged Kea runtime closure
  (libkea-*.so*) is resolvable by the OHOS loader and the server runs.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaDhcp4TestConan(ConanFile):
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
            self.output.info("cross-building: kea-dhcp4 consumer tests skipped")
            return

        kea_dhcp4 = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "kea-dhcp4")
        bindir = self.cpp.build.bindirs[0]

        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, kea_dhcp4),
                 env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, kea_dhcp4),
                 env="conanrun")

        test_script = os.path.join(self.source_folder, "test_dhcp4.py")
        self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
