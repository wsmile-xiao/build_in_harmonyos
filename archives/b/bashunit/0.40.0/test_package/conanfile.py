#!/usr/bin/env python3
"""Consumer test for the packaged bashunit command."""

import os
import shutil

from conan import ConanFile


class BashunitTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["bashunit"]
        executable = os.path.join(package.package_folder, "bin", "bashunit")
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )

        # bashunit internally uses mktemp(1) with $TMPDIR (see lines 7747, 1050).
        # Ensure the directory exists; otherwise mktemp fails, e.g. in CI where
        # TMPDIR points to a non-existent path.
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        os.makedirs(tmpdir, exist_ok=True)

        self.run(f'"{bash}" "{executable}" --version', env="conanrun")
        self.run(
            f'"{bash}" "{executable}" "{os.path.join(self.source_folder, "test.sh")}" --no-color',
            env="conanrun",
        )
