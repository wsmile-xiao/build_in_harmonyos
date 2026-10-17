#!/usr/bin/env python3
"""Run netdiscover's non-privileged help path."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NetdiscoverTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["netdiscover"].package_folder, "bin", "netdiscover"
        )
        output = os.path.join(self.build_folder, "netdiscover-help.txt")
        self.run(
            f'"{binary}" -h > "{output}"',
            env="conanrun",
            ignore_errors=True,
        )
        with open(output, encoding="utf-8", errors="replace") as stream:
            help_text = stream.read()
        if "Netdiscover 0.21" not in help_text or "Usage:" not in help_text:
            raise RuntimeError(f"netdiscover help check failed:\n{help_text}")
