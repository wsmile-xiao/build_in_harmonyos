#!/usr/bin/env python3
"""Consumer checks for scanlogd 2.2.8.

The upstream binary has no --help/--version contract and requires raw-socket
privileges.  The shell test verifies installation and the expected unprivileged
failure path without claiming a successful packet-capture run.
"""
import os

from conan import ConanFile


class ScanlogdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["scanlogd"].package_folder
        binary = os.path.join(package_folder, "bin", "scanlogd")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"

        self.run(
            f'SCANLOGD_BIN="{binary}" SCANLOGD_PREFIX="{package_folder}" '
            f'"{bash}" test.sh',
            env="conanrun",
        )
