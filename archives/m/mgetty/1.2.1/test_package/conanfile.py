#!/usr/bin/env python3
"""Conan test_package for mgetty 1.2.1 — consumer-side checks.

mgetty ships command-line tools only (getty/fax suite + G3 image tools), so
the consumer test runs the installed binaries from the package and exercises
real functionality (G3 encode/decode with the byte-exact expectations from the
upstream g3/ test suite), plus a HarmonyOS-specific test that checks the
installed executables against the OHOS toolchain (ELF64/AArch64 identity, no
Linux-only dynamic dependencies, on-device determinism).
"""
import os

from conan import ConanFile


class MgettyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg, "bin")
        self.run('bash "%s" "%s"' % (os.path.join(self.recipe_folder,
                                                  "test_mgetty.sh"), bin_dir),
                 env="conanrun")
        self.run('bash "%s" "%s"' % (os.path.join(self.recipe_folder,
                                                  "test_ohos.sh"), bin_dir),
                 env="conanrun")
