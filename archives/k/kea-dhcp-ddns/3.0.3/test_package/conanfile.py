#!/usr/bin/env python3
"""Conan consumer test for kea-dhcp-ddns 3.0.3.

Three checks run against the packaged daemon:

* ``test_kea_dhcp_ddns.py`` — consumer contract: version output, the three
  configuration syntax-check paths exercised by upstream's own process test
  suite (valid / syntactically broken / out-of-range value), and one real
  daemon lifecycle end to end (start with -c, DCTL_CONFIG_COMPLETE in its log,
  SIGTERM, DCTL_SHUTDOWN) proving the process loads its Kea runtime libraries
  and runs the whole controller/queue-manager code path;
* ``test_ohos_platform`` — HarmonyOS-specific: the packaged executable carries
  the OHOS aarch64 / musl / libc++ platform ABI signature;
* ``test_ohos_runtime``  — HarmonyOS-specific: the packaged Kea runtime closure
  (libkea-*.so*) is resolvable by the OHOS loader and the daemon runs.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaDhcpDdnsTestConan(ConanFile):
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
            self.output.info("cross-building: kea-dhcp-ddns consumer tests skipped")
            return

        daemon = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "kea-dhcp-ddns")
        bindir = self.cpp.build.bindirs[0]

        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, daemon),
                 env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, daemon),
                 env="conanrun")

        test_script = os.path.join(self.source_folder, "test_kea_dhcp_ddns.py")
        self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
