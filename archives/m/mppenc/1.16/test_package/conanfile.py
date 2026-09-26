#!/usr/bin/env python3
"""Consumer smoke test for mppenc."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout

from test_mppenc import ASSERTION_COUNT, verify_mpc, write_wav


class MppencTestConan(ConanFile):
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
        output_mpc = os.path.join(self.build_folder, "output.mpc")
        self._run("mppenc --help", "1/4 mppenc --help exits 0")
        self._run(
            "mppenc --quality 5 {} {}".format(self._q(input_wav), self._q(output_mpc)),
            "2/4 mppenc encodes WAV to MPC (exit 0)",
        )
        verify_mpc(output_mpc)
        print("SMOKE PASS=%d/%d assertion_count=%d" % (ASSERTION_COUNT, ASSERTION_COUNT, ASSERTION_COUNT))

    def _run(self, command, ok_msg):
        self.run(command, env="conanrun")
        print("[PASS] " + ok_msg)

    def _q(self, value):
        value = str(value)
        if os.name == "nt":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)
