#!/usr/bin/env python3
"""Conan test_package for indent/2.2.13 — consumer test (L1).

Runs the packaged indent CLI against an unformatted C sample and asserts
the formatted output file is produced with the expected content.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class IndentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        indent_bin = os.path.join(bindir, "indent")
        input_file = os.path.join(self.source_folder, "sample.c")
        out_file = os.path.join(self.build_folder, "sample_formatted.c")
        self.run(f'"{indent_bin}" -o "{out_file}" "{input_file}"', env="conanrun")
        with open(out_file, "r", encoding="utf-8") as f:
            formatted = f.read()
        assert "main" in formatted, "formatted output missing main()"
        assert "printf" in formatted, "formatted output missing printf()"
        print("indent consumer test OK: CLI formatted sample.c as asserted")
