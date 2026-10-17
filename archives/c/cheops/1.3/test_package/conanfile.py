#!/usr/bin/env python3
"""Conan test_package — cheops 1.3 consumer smoke test.

Runs the packaged `cheops` binary from a consumer point of view:
- `--version` exits 0 and prints the CHEOPS version banner
- `--help` exits 0 and prints usage
- a scripted human/human game (`h h e2e4 e7e5 quit`) drives the real game
  loop over stdin and exits 0
"""
import os
import shutil

from conan import ConanFile


class CheopsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_cheops.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
