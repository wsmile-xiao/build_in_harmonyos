#!/usr/bin/env python3
"""Consumer test for the jdupes command-line package."""
import os
import shutil

from conan import ConanFile


class JdupesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL")
        if not shell or (os.path.isabs(shell) and not os.path.exists(shell)):
            shell = shutil.which("bash") or "sh"
        self.run(f'"{shell}" test.sh', env="conanrun")
