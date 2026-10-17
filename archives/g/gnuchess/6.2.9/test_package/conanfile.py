#!/usr/bin/env python3
"""Consumer test for GNU Chess 6.2.9 (tool package).

The consumer test executes the packaged engine and asserts observable
behaviour (R34/R51) through test_gnuchess.sh — the three shipped
executables are present, and the engine answers a fixed `go depth 3`
command with a move ("My move is", src/frontend/engine.cc:316).
"""
import os

from conan import ConanFile


class GnuchessTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_gnuchess.sh")
        self.run(f'sh "{script}" "{bindir}"')
