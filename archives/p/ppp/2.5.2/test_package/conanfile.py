#!/usr/bin/env python3
"""Runtime smoke test for the installed ppp command suite."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class PppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        bindir = os.path.join(package, "bin")

        for command in ("pppd", "chat", "pppstats", "pppdump", "pppoe-discovery"):
            path = os.path.join(bindir, command)
            if not os.path.isfile(path):
                raise AssertionError(f"missing installed command: {path}")

        plugin = os.path.join(package, "lib", "pppd", "2.5.2", "pppoe.so")
        if not os.path.isfile(plugin):
            raise AssertionError(f"missing installed PPPoE plugin: {plugin}")
        if can_run(self):
            pppd = os.path.join(bindir, "pppd")
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{script}" "{pppd}"', env="conanrun")
