#!/usr/bin/env python3
"""test_package for nagios 4.5.14 — consumer smoke tests.

nagios is an application package; the tests (test_nagios.sh) exercise the
real daemon binary end-to-end:

  1. `nagios --version`  — binary loads, reports the right version
  2. `nagios -v cfg`     — the daemon's configuration validator actually
                           parses a minimal nagios.cfg (exercises config
                           loading, object parsing, pre-flight check —
                           the core startup path of the monitoring engine)
  3. `nagiostats --version` — the statistics utility binary works

These are real behaviour assertions against the installed package, not
print-only stubs (R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class NagiosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return

        nagios_dep = self.dependencies["nagios"]
        pkg = nagios_dep.package_folder
        script = os.path.join(self.source_folder, "test_nagios.sh")

        # run environment (LD_LIBRARY_PATH for the shared gd chain) is
        # provided by VirtualRunEnv through env="conanrun"
        self.run(f'sh "{script}" "{pkg}" "{self.build_folder}"',
                 env="conanrun")
