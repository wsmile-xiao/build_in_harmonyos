#!/usr/bin/env python3
"""Conan test_package — lzd 1.5 (Conan L1 official test).

Consumer test: decompress upstream fixtures (fox.lz known plaintext,
em.lz multi-member) + reject corrupted input (negative control), using
fixtures bundled in test_package/fixtures/ (R34: real binary usage).
"""
import base64
import os
import shutil
import tempfile

from conan import ConanFile


class LzdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = None
        for _, dep in self.dependencies.items():
            pkg_folder = dep.package_folder
            break
        bin_path = os.path.join(pkg_folder, "bin", "lzd")
        source_fixtures = os.path.join(os.path.dirname(__file__), "fixtures")
        fixtures = tempfile.mkdtemp(prefix="lzd-fixtures-")
        try:
            for name in ("fox", "em"):
                encoded = os.path.join(source_fixtures, name + ".lz.b64")
                decoded = os.path.join(fixtures, name + ".lz")
                with open(encoded, "rb") as src, open(decoded, "wb") as dst:
                    dst.write(base64.b64decode(src.read()))
            self.run(f'sh test.sh "{bin_path}" "{fixtures}"', env="conanrun")
        finally:
            shutil.rmtree(fixtures, ignore_errors=True)
