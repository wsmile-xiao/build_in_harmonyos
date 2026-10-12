#!/usr/bin/env python3
"""Conan consumer test for kea-dhcp6 3.0.3.

Three checks run against the packaged server:

* ``test_kea_dhcp6.py``  — consumer contract: version/version-report/config-report
  output, the syntax-check path on a valid and on two invalid inputs, and the
  option parser error path (proves the process loads its Kea runtime libraries
  and walks the whole server start-up code path);
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


class KeaDhcp6TestConan(ConanFile):
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
            self.output.info("cross-building: kea-dhcp6 consumer tests skipped")
            return

        kea_dhcp6 = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "kea-dhcp6")
        bindir = self.cpp.build.bindirs[0]

        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, kea_dhcp6),
                 env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, kea_dhcp6),
                 env="conanrun")

        test_script = os.path.join(self.source_folder, "test_kea_dhcp6.py")
        self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
