#!/usr/bin/env python3
"""Conan test_package — polyglot 2.0.4.

Runs the packaged polyglot binary through its three opening-book tool
subcommands (no chess engine needed):
1. make-book   — builds a Polyglot book from an embedded minimal PGN
2. dump-book   — dumps book lines for white/black with move notation
3. no-args run — prints the usage banner
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PolyglotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["polyglot"]
        binary = os.path.join(dep.package_folder, "bin", "polyglot")
        script = os.path.join(self.source_folder, "test_polyglot.py")
        self.run(f'python3 "{script}" "{binary}"', env="conanrun")
