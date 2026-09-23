#!/usr/bin/env python3
"""Conan test_package for pcal 4.11.0."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class PcalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pcal_bin = os.path.join(self.dependencies["pcal"].package_folder, "bin", "pcal")
        test_script = os.path.join(self.source_folder, "test.sh")
        shell = shutil.which("zsh") or os.environ.get("CONFIG_SHELL", "/bin/zsh")
        self.run('PCAL_BIN={} {} {}'.format(
            shlex.quote(pcal_bin),
            shlex.quote(shell),
            shlex.quote(test_script),
        ), env="conanrun")
