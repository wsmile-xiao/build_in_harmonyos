#!/usr/bin/env python3
"""Conan test_package for interbench 0.31 — Interactivity benchmark.

Runs test_interbench.py as the real executor (L0c compliance).
test_interbench.py directly executes the installed binary, prints per-case
TEST PASS / TEST FAIL lines and a final TEST SUMMARY, and exits non-zero on
failure so self.run() raises.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy


class InterbenchTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["interbench"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        interbench_cmd = os.path.join(bin_dir, "interbench")

        if not os.path.isfile(interbench_cmd):
            raise ConanException(f"interbench binary not found at: {interbench_cmd}")

        # Copy test_interbench.py to a writable working directory
        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.environ.get("HOME", "/storage"), "tmp")
        workdir = tempfile.mkdtemp(prefix="interbench-test-", dir=tmpdir)

        try:
            copy(self, "test_interbench.py", src=self.source_folder, dst=workdir)
            test_script = os.path.join(workdir, "test_interbench.py")
            if not os.path.isfile(test_script):
                raise ConanException(f"test_interbench.py not found at: {test_script}")

            # Run the test script — self.run() raises on non-zero exit
            self.output.info("Running test_interbench.py ...")
            self.run(
                f'python3 "{test_script}" "{interbench_cmd}"',
                env="conanrun"
            )
            self.output.info("interbench test_interbench.py: ALL PASS")
        finally:
            if os.path.isdir(workdir):
                shutil.rmtree(workdir, ignore_errors=True)
