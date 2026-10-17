#!/usr/bin/env python3
"""Conan test_package for jgraph 83.

test_jgraph.sh drives the installed `jgraph` binary (R34 — no print-only
stub): PostScript rendering and determinism, -p show mode, the landscape
page translation, EPS mark bounding-box parsing (including the truncated
box error path), multi-page and -comments output, and the malformed-input
diagnostics.  See the script for the full assertion list.
"""

import os

from conan import ConanFile


class JgraphTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run("{0} test_jgraph.sh".format(bash), env="conanrun")
