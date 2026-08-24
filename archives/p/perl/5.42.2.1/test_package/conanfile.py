#!/usr/bin/env python3
"""Conan consumer test for the Perl runtime and native XS modules."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PerlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: perl runtime smoke skipped")
            return

        script = os.path.join(self.source_folder, "test_perl.sh")
        runner = shutil.which("zsh") or "/system/bin/zsh"
        self.run(f"{shlex.quote(runner)} {shlex.quote(script)}", env="conanbuild")
