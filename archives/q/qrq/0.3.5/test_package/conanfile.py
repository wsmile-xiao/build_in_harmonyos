#!/usr/bin/env python3
"""Conan test_package for qrq 0.3.5.

R34: the test exercises the shipped binary (`qrq -h`), and additionally
verifies the HarmonyOS-specific OHAudio port:

  * the `qrq` binary is linked against the native `libohaudio` backend, and
  * the native OHAudio renderer that the backend relies on works at runtime
    (a raw renderer probe is compiled and executed).

qrq has no upstream test suite, so this is the package's only real test.
"""

import os

from conan import ConanFile


class QrqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # HarmonyOS-specific probe: compile against the OHOS system OHAudio API.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        src = os.path.join(self.source_folder, "src", "test_ohos_audio.c")
        out = os.path.join(self.build_folder, "test_ohos_audio")
        self.run(f"{cc} -O2 -o {out} {src} -lohaudio")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # R34: run the shipped binary + check the HarmonyOS OHAudio linkage.
        self.run(f"{bash} test.sh", env="conanrun")
        # HarmonyOS-specific runtime test of the native OHAudio renderer.
        self.run(os.path.join(self.build_folder, "test_ohos_audio"), env="conanrun")
