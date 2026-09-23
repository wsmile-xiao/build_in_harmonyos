#!/usr/bin/env python3
"""Conan test_package — centerim 4.22.10 (terminal app).

R34: substantially exercise the packaged binary. centerim is a ncurses TUI
client with no non-interactive test hooks, so the smoke test runs the
binary directly:
  1. centerim --version — binary installed + runnable, prints 4.22.10
  2. centerim --help    — usage listing path works
Interactive protocol flows need a live network + terminal and are out of
scope for CI (documented in test_package/MANIFEST.yml).
"""
import os

from conan import ConanFile


class CenterimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # --version must print the version and exit 0 without a TTY
        self.run("centerim --version", env="conanrun")
        # --help must print usage and exit 0
        self.run("centerim --help", env="conanrun")
