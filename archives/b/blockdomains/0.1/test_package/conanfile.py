#!/usr/bin/env python3
"""Conan test_package for blockdomains 0.1.

blockdomains is a standalone daemon (iptables NFQUEUE filter). The upstream
main() has no --help/--version: it loads the ACL files given as arguments and
then calls nfq_open(). The smoke test therefore:
  1. checks both packaged tools (blockdomains, blockdomainsctl) are present
  2. checks blockdomainsctl prints its usage hint without privileges
  3. runs the daemon on a real ACL file and asserts it reaches the NFQUEUE
     stage; it must then either keep running (kernel NFQUEUE available) or
     exit 1 at nfq_open() (kernel NFQUEUE unavailable) — anything else fails.
"""
import os

from conan import ConanFile


class BlockdomainsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate binaries via dependency package folder
        dep = self.dependencies["blockdomains"]
        bin_dir = os.path.join(str(dep.package_folder), "bin")
        test_script = os.path.join(self.source_folder, "test_blockdomains.sh")
        self.run(f'sh "{test_script}" "{bin_dir}"')
