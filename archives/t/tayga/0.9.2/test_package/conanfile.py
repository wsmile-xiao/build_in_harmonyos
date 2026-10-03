#!/usr/bin/env python3
"""Conan test_package for tayga 0.9.2 — smoke-test the installed daemon binary.

The full NAT64 data plane requires /dev/net/tun and root privileges, which is
out of scope here; test_tayga.sh verifies that the installed binary is found
through the conanrun environment, prints its usage text for --help (exit 0)
and rejects invalid options with a non-zero exit code.
"""

from conan import ConanFile


class TaygaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: exercise the actual installed binary via the smoke-test script
        self.run("sh test_tayga.sh", env="conanrun", cwd=self.source_folder)
