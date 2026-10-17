#!/usr/bin/env python3
"""Conan test_package: upx-ucl/4.2.4 consumer verification.

Runs the installed `upx` CLI:
  1) --version smoke (prints "upx 4.2.4")
  2) real pack/unpack round-trip on a copy of the upx binary itself
     (upstream self-pack precedent): pack -> integrity test -> unpack ->
     byte-identical compare. The packed binary is deliberately NOT
     executed here (exec of a packed image from a possibly-noexec temp
     dir is the run-packed upstream test's job; see notes.md).
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class UpxUclTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        # OHOS 真机 bash 路径与 test_package-executable 模板一致
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_sh}"', env="conanrun")
