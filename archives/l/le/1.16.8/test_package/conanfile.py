#!/usr/bin/env python3
"""Conan test_package for le 1.16.8 — consumer verification.

Drives the installed ``le`` binary through ``test_le.sh``, which asserts the
editor's non-interactive entry points (version banner, keymap export, colour
table export) plus the usage path.  ``le`` is an interactive TUI editor, so an
unattended test cannot run a full editing session — the rationale and the list
of covered entry points live in the package's ``notes.md``.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bindir = self.dependencies["le"].cpp_info.bindirs[0]
        le = os.path.join(bindir, "le")
        script = os.path.join(self.source_folder, "test_le.sh")
        self.run(f'sh "{script}" "{le}"', env="conanrun")
