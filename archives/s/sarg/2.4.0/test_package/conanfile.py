#!/usr/bin/env python3
"""Conan test_package for sarg 2.4.0.

sarg is a command line tool, so the consumer test drives the installed binary
end to end: it feeds it a squid access log and asserts on the content of the
HTML report that comes out (per user / per site / per date, user dimension
isolated).  See test_sarg.sh for the assertion list.
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class SargTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["sarg"].package_folder
        sarg_bin = os.path.join(pkg, "bin", "sarg")
        script = os.path.join(self.source_folder, "test_sarg.sh")
        workdir = os.path.join(tempfile.gettempdir(), "sarg-2.4.0-test_package")
        self.run(f'sh "{script}" "{sarg_bin}" "{pkg}" "{workdir}"', env="conanrun")
