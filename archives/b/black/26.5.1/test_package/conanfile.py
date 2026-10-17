#!/usr/bin/env python3
"""Conan test_package for black 26.5.1.

R34: test must substantively depend on the package under test.
black is a console application (entry point: black = black:patched_main).
1. Run the installed `black --version` (wrapper + package layout smoke).
2. Format an intentionally unformatted example.py and assert the
   canonical output, exercising the real formatter code path.
"""
import os
import shutil
import tempfile

from conan import ConanFile


class BlackTestConan(ConanFile):
    # Pure Python application test, no CMake needed
    test_type = "explicit"
    settings = "os", "compiler", "build_type", "arch"  # L0p: all four required

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: substantively depend on the package under test — call bin/black
        black_dep = self.dependencies["black"]
        black_bin = os.path.join(black_dep.package_folder, "bin", "black")

        # 1. version smoke test
        self.run(f'"{black_bin}" --version', env="conanrun")

        # 2. real formatting check (tempdir so nothing pollutes the source tree)
        example = os.path.join(os.path.dirname(__file__), "example.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            formatted = os.path.join(tmpdir, "example_formatted.py")
            shutil.copyfile(example, formatted)
            self.run(f'"{black_bin}" "{formatted}"', env="conanrun")
            with open(formatted, encoding="utf-8") as f:
                content = f.read()
        assert 'x = {"a": 1, "b": 2}' in content, (
            f"black did not reformat sample to canonical style, got:\n{content}"
        )
        self.output.info("format check passed: sample reformatted to canonical style")
