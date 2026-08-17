#!/usr/bin/env python3
"""Conan test_package — pdf2json 0.71

Tests the pdf2json binary by running 'pdf2json -v' to verify version output.
pdf2json is a command-line tool, not a library, so we test the binary directly.
Note: pdf2json -v exits with code 1 even on success, so we pipe through grep
to verify the output contains the expected version string.
"""
import os

from conan import ConanFile


class Pdf2JsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = self.dependencies["pdf2json"].cpp_info.bindirs[0]
        pdf2json_bin = os.path.join(bin_dir, "pdf2json")
        # pdf2json -v exits with code 1 but prints version info to stdout.
        # Use grep to verify the binary outputs expected version string.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f'{bash} -c \'"{pdf2json_bin}" -v 2>&1 | grep -q "pdf2json"\'',
            env="conanrun",
        )
