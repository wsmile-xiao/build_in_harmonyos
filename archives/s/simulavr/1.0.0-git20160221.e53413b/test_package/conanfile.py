#!/usr/bin/env python3
"""Conan test_package — simulavr 1.0.0-git20160221.e53413b.

L1 official test: exercise the installed ``simulavr`` CLI (run it, assert it
reports its version).  simulavr is delivered as a command-line simulator
(libsim is linked in statically), so the meaningful consumer test is running
the binary — see test_simulavr.py.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SimulavrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["simulavr"].package_folder
        exe = os.path.join(pkg, "bin", "simulavr")
        if not os.path.isfile(exe):
            raise Exception(f"simulavr binary not found: {exe}")
        script = os.path.join(os.path.dirname(__file__), "test_simulavr.py")
        self.run(f"python3 '{script}' '{exe}' 'SimulAVR'", env="conanrun")
