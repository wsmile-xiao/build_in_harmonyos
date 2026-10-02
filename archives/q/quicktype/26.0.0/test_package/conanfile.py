#!/usr/bin/env python3
"""Test package — quicktype 26.0.0 consumer test."""

import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class QuicktypeTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["quicktype"].package_folder
            executable = os.path.join(
                package_folder,
                "bin",
                "quicktype",
            ).replace("\\", "/")
            test_script = os.path.join(
                self.source_folder,
                "test.sh",
            ).replace("\\", "/")
            # Keep test scratch files out of the recipe tree.
            workdir = tempfile.mkdtemp(prefix="quicktype-consumer-")
            logfile = os.path.join(workdir, "consumer-tests.log").replace("\\", "/")
            # The OpenHarmony Node runtime aborts when it inherits socket
            # descriptors; give the test process a regular-file stdout/stderr
            # and /dev/null stdin.
            try:
                self.run(
                    f'sh "{test_script}" "{executable}" "{workdir}" '
                    f'> "{logfile}" 2>&1 < /dev/null',
                    cwd=self.source_folder,
                )
            except Exception:
                if os.path.exists(logfile):
                    self.output.error(
                        open(logfile, encoding="utf-8", errors="replace").read()
                    )
                raise
            if os.path.exists(logfile):
                self.output.info(
                    open(logfile, encoding="utf-8", errors="replace").read()
                )
