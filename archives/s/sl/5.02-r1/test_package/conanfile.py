#!/usr/bin/env python3
"""Conan test_package for sl (Steam Locomotive).

This test verifies the sl binary is built and can execute.
Since sl requires a terminal (ncurses), we run it with TERM=dumb
which causes a graceful error exit — proving the binary runs and
ncurses is properly linked.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must actually execute the tested package's binary
        # VirtualRunEnv sets up PATH with sl's bin directory
        # test_sl.py finds and runs the sl binary, verifying ncurses linkage
        self.run("python3 test_sl.py", env="conanrun", cwd=self.source_folder)
