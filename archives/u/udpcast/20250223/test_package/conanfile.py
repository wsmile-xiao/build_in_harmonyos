#!/usr/bin/env python3
"""Conan consumer test for UDPcast 20250223."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class UdpcastTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_udpcast.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: UDPcast command tests cannot run")
            return

        package_folder = self.dependencies["udpcast"].package_folder
        sender = os.path.join(package_folder, "bin", "udp-sender")
        receiver = os.path.join(package_folder, "bin", "udp-receiver")
        script = os.path.join(self.source_folder, "test_udpcast.py")
        self.run(
            f'python3 "{script}" "{sender}" "{receiver}"',
            env="conanrun",
        )
