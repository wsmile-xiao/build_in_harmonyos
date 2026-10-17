#!/usr/bin/env python3
"""test_package — usleep 20160311.094456 (command-line tool, no library API).

Runs test_usleep.py against the packaged bin/usleep: A1-A3 ELF artifact checks
on every host, F1-F6 functional checks (exit status, silence, measured sleep
time) mandatory on the aarch64 CI worker; see the script docstring for the
foreign-architecture rule. The binary path comes from the tested package only
(no PATH lookup), so the CI L1e destructive check fails once bin/ is removed.
"""
import os
import sys

from conan import ConanFile


class UsleepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        usleep = os.path.join(self.dependencies["usleep"].package_folder, "bin", "usleep")
        script = os.path.join(self.source_folder, "test_usleep.py")
        self.run(f'"{sys.executable}" "{script}" "{usleep}"', env="conanrun")
