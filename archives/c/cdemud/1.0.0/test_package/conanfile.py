#!/usr/bin/env python3
"""Conan test_package for cdemud (L1 consumer test).

cdemud 1.0.0 is an executable-only package (no library, no headers), so
the consumer test executes the packaged daemon binary end-to-end:

  1. `cdemud --help` (GOption built-in) — real process execution of the
     signed OHOS ELF; option parsing happens before any daemon
     initialization, so no D-Bus bus / vhba device is required;
  2. content assertion on the usage output (R34: no print-only stubs).

The test also satisfies the CI L1e negative check: it invokes the
packaged binary by absolute path, so removing bin/ makes it fail.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class CdemudTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        binary = os.path.join(
            self.dependencies["cdemud"].package_folder, "bin", "cdemud")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script}" "{binary}"', env="conanrun")
        self.output.info("cdemud test_package: packaged daemon smoke verified")
