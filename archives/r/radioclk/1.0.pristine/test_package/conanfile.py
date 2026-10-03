#!/usr/bin/env python3
"""Test package for radioclk 1.0.pristine (installed-package consumer test).

radioclk is an application package: the consumer is the radioclkd binary
itself. No consumer compilation is needed; the test runs the installed
binary through its built-in no-hardware code paths (--version, --help,
missing-argument error, unopenable-device error) which exit before any
serial port, SHM segment or daemonization happens.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class RadioclkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile check only")
            return
        binary = os.path.join(self.dependencies[self.tested_reference_str]
                              .cpp_info.bindirs[0], "radioclkd")
        script = os.path.join(self.recipe_folder, "test_radioclk.py")
        self.run(f'"{sys.executable}" "{script}" "{binary}"',
                 env="conanrun")
