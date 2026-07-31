#!/usr/bin/env python3
"""Conan test_package — vitetris 0.59.1 smoke test.

Verifies the installed `tetris` binary via its non-interactive entry points:
- `tetris -help` prints the version banner and usage.
- `tetris -hiscores` prints the highscore list and exits cleanly.

vitetris uses `-help` (single dash) instead of `--help` / `--version`.
The game itself is interactive and cannot be driven by CI, so test.sh
only exercises the non-interactive entry points and asserts on stdout.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class VitetrisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        # L2 smoke: verify binary is callable and prints version banner.
        # vitetris uses -help (single dash), not --help / --version.
        self.run("tetris -help", env="conanrun")

        # Full smoke test with stdout assertions (version banner,
        # -hiscores option listed, -hiscores output contains 'scores').
        script = os.path.join(self.source_folder, "test.sh")
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f'"{bash}" "{script}"', env="conanrun")
