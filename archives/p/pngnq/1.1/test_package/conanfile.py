#!/usr/bin/env python3
"""Conan test_package — pngnq 1.1 (PNG NeuQuant quantizer CLI).

test.sh embeds a small valid 8x8 RGBA PNG (octal-escaped bytes, no
external tools needed), then runs the real pngnq binary to quantize it
and verifies the output is a valid palette PNG; it also cross-checks
the pngcomp comparison tool between the two images.

HMBS_TEST_PACKAGE_RESULT is emitted by test.sh as machine evidence.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PngnqTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["pngnq"].package_folder
        bin_path = os.path.join(package_folder, "bin", "pngnq")
        assert os.path.isfile(bin_path), f"pngnq binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # test.sh uses bash (set -euo pipefail); CONFIG_SHELL points at
            # the OHOS bash when set, otherwise fall back to bash on PATH.
            shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "bash"
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            # R34: actually execute the packaged pngnq/pngcomp binaries
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT emitted by test.sh.
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"pngnq is not an ELF binary: {magic!r}"
            self.output.info(f"pngnq binary exists and has ELF magic: {bin_path}")
