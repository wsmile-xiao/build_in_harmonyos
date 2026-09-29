#!/usr/bin/env python3
"""Conan test package for Passenger 6.1.8."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PassengerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["passenger"]
        script = os.path.join(self.recipe_folder, "check_passenger.py")
        args = [sys.executable, script, dependency.package_folder]
        if can_run(self):
            args.append("--run")
        self.run(" ".join(shlex.quote(arg) for arg in args), env="conanrun")
