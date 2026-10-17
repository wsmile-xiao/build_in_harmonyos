#!/usr/bin/env python3
"""Conan test_package — consumer feasibility test for lgrind/3.67 (OHOS).

Runs the packaged lgrind TOOL against a sample C file using the packaged
lgrindef definitions database (res dir), then verifies the LaTeX output.
This mirrors the T4 OHOS consumer case from upstream test reporting (notes.md).
"""
import os
import sys
import tempfile

from conan import ConanFile


class LgrindTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # packaged tool + res layout
        bindir = self.dependencies["lgrind"].cpp_info.bindirs[0]
        resdir = self.dependencies["lgrind"].cpp_info.resdirs[0]
        lgrind_bin = os.path.join(self.dependencies["lgrind"].package_folder, bindir, "lgrind")
        lgrindef = os.path.join(self.dependencies["lgrind"].package_folder, resdir, "lgrindef")
        sample = os.path.join(self.recipe_folder, "sample_consumer.c")

        # 1) real execution of the packaged binary (R34/PF3)
        out_tex = os.path.join(tempfile.mkdtemp(prefix="lgrind-test-"), "sample_consumer.tex")
        self.run(f'"{lgrind_bin}" -d "{lgrindef}" "{sample}" > "{out_tex}"', env="conanrun")

        # 2) assert the LaTeX listing envelope and semantic markers
        with open(out_tex, "r", errors="replace") as f:
            content = f.read()
        # \File{} echoes the input path with LaTeX-escaped underscores (sample\_consumer.c)
        normalized = content.replace("\\_", "_")
        checks = {
            "\\begin{lgrind}": "document envelope opened",
            "\\File{": "input file recorded",
            "sample_consumer.c": "correct input file named",
            "\\Proc{main}": "procedure recognized",
            "\\end{lgrind}": "document envelope closed",
        }
        missing = [k for k, v in checks.items() if k not in normalized]
        if missing:
            self.output.error(f"lgrind output missing markers: {missing}")
            sys.exit(1)
        self.output.success(
            f"lgrind consumer test passed: envelope+\\File+\\Proc present "
            f"({len(content.splitlines())} lines of LaTeX)")
