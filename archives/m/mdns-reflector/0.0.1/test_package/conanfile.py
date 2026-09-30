#!/usr/bin/env python3
"""Consumer test for the mdns-reflector command-line application."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class MdnsReflectorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Skipping mdns-reflector runtime test in a non-runnable "
                "configuration"
            )
            return

        executable = os.path.join(
            self.dependencies["mdns-reflector"].package_folder,
            "bin",
            "mdns-reflector",
        )
        script = os.path.join(self.source_folder, "test_mdns_reflector.py")
        self.run(
            f'"{sys.executable}" "{script}" "{executable}"',
            env="conanrun",
        )
