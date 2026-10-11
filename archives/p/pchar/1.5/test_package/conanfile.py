#!/usr/bin/env python3
"""Conan consumer tests for pchar 1.5, including offline trace replay."""

import os
import re

from conan import ConanFile
from conan.tools.layout import basic_layout


class PcharTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        fixture = os.path.join(self.source_folder, "fixtures", "replay_ipv4.txt")
        output = os.path.join(self.build_folder, "replay-output.txt")
        self.run(
            f'pchar -r "{fixture}" -n > "{output}"',
            cwd=self.source_folder,
            env="conanrun",
        )
        with open(output, encoding="utf-8") as result:
            output_text = result.read()
        if not re.search(r"Path length:\s+1 hops", output_text):
            raise RuntimeError("pchar did not report the expected one-hop path")

        # Keep basic CLI smoke checks in addition to the path-analysis assertion.
        self.run("pchar --version", env="conanrun")
        self.run("pchar --help", env="conanrun")
