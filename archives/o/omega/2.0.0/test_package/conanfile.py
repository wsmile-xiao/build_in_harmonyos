#!/usr/bin/env python3
"""Conan test_package for omega/2.0.0 (application package).

L1 test: run the packaged CLI tools end to end — version checks plus a
real scriptindex -> omega CGI query round trip (R34: the test actually
executes the packaged binaries and asserts on their output).
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class OmegaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Work dir goes to the system temp area: the test_package
            # build_folder is the source dir here (no layout), writing
            # into it would leak artifacts into archives/ (JC).
            work = tempfile.mkdtemp(prefix="omega-smoke.")
            smoke = os.path.join(self.source_folder, "smoke.sh")
            shell = shutil.which("bash") or "sh"
            self.run(f'"{shell}" "{smoke}"', cwd=work, env="conanrun")
