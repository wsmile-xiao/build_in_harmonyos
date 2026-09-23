#!/usr/bin/env python3
"""Conan test package for oystr 0.2.0 (shell consumer)."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class OystrTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate(scope="run")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash:
            raise RuntimeError("CONFIG_SHELL or bash is required for the PTY test")
        self.run(f"{shlex.quote(bash)} test.sh", env="conanrun")
