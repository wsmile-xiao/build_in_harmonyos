#!/usr/bin/env python3
"""Conan test_package — debian-security-support (shell tool + data).

Harmony-specific package validation (NOT the upstream Perl test suite / autopkgtest):
  1. CLI smoke: `--version` / `--help`
  2. portable-core decision with a real supplied manifest (DSS_MANIFEST) on
     controlled data -> ended / limited / earlyend output (upstream t/ semantics)
  3. shipped data-file lint (status enum, date column)
  4. honest no-backend boundary: with DSS_DISABLE_DPKG=1 and no manifest/status,
     the tool must exit 3 (NOT exit 0 with an empty "all clean" report)
The script needs sh + awk + GNU date(-d) + grep(+E/-P) + getopt + gettext; the
runner checks these and runs the full validation when present, else only the
file-layout assertions (still an honest pass for layout).
"""
import os

from conan import ConanFile


class DssTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debian-security-support"].package_folder
        script = os.path.join(self.source_folder, "test_security_support.py")
        self.run(f"python3 {script} {pkg}", env="conanrun")
