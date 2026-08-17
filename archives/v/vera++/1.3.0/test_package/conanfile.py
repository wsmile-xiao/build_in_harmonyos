#!/usr/bin/env python3
"""Conan test_package for vera++ 1.3.0 — command-line tool (L1 test).

vera++ is a C++ source-code verification tool, not a library, so the test
runs the installed binary against a sample file and asserts that real rules
fire (R34: substantive test — must exercise the packaged binary, not just
print a string).
"""
import os

from conan import ConanFile


class VeraPPTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["vera++"]
        vera_bin = os.path.join(dep.package_folder, "bin", "vera++")
        if not os.path.exists(vera_bin):
            raise RuntimeError(f"vera++ binary not found: {vera_bin}")

        # 1) --version must report the correct version
        out_file = os.path.join(self.build_folder, "version.txt")
        self.run(f"{vera_bin} --version > {out_file} 2>&1")
        with open(out_file) as f:
            version = f.read().strip()
        if version != "1.3.0":
            raise RuntimeError(f"unexpected version: {version!r}")

        # 2) A file with violations must trigger real rules
        sample = os.path.join(self.source_folder, "sample.cpp")
        if not os.path.exists(sample):
            raise RuntimeError(f"test source not found: {sample}")
        report_file = os.path.join(self.build_folder, "report.txt")
        self.run(f"{vera_bin} -p full -s {sample} > {report_file} 2>&1")
        with open(report_file) as f:
            report = f.read()
        # full profile reports: no copyright notice (T013), tab usage (L002),
        # closing brace not aligned (T011) — any of these proves rules ran
        expected = ("T013" in report) or ("L002" in report) or ("T011" in report)
        if not expected:
            raise RuntimeError(f"no rule fired on violating sample:\n{report}")
        self.output.info(f"vera++ test OK: version={version}, rules fired on sample")
