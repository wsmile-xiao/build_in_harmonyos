#!/usr/bin/env python3
"""Consumer smoke test for alacenc."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout

from test_alacenc import verify_m4a, write_wav


class AlacencTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        write_wav(os.path.join(self.build_folder, "input.wav"))

    def test(self):
        input_wav = os.path.join(self.build_folder, "input.wav")
        output_m4a = os.path.join(self.build_folder, "output.m4a")
        self._run("alacenc --version")
        self._run("alacenc --help")
        self._run("alacenc -q {} {}".format(self._q(input_wav), self._q(output_m4a)))
        verify_m4a(output_m4a)

    def _run(self, command):
        self.run(command, env="conanrun")

    def _q(self, value):
        value = str(value)
        if os.name == "nt":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)
