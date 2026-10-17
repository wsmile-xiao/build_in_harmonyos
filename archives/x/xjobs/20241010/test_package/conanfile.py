#!/usr/bin/env python3
"""Conan test recipe for xjobs 20241010 (Python functional tests)."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class XjobsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("xjobs behavioral tests skipped: target cannot run on this host")
            return
        package = self.dependencies["xjobs"].package_folder
        binary = os.path.join(package, "bin", "xjobs")
        script = os.path.join(self.source_folder, "functional.py")
        results = os.path.join(self.build_folder, "xjobs-test-results")
        command = [sys.executable, script, binary, results]
        self.run(" ".join(shlex.quote(part) for part in command), env="conanrun")