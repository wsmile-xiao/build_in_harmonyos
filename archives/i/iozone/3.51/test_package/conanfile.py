#!/usr/bin/env python3
"""Conan test_package for iozone 3.51 — Filesystem Benchmark Tool.

Runs test_iozone.py as the test source file (L0c compliance).
test_iozone.py directly executes the installed iozone binary and exits
non-zero on failure. self.run() will raise on non-zero exit.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy


class IozoneTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["iozone"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        iozone_cmd = os.path.join(bin_dir, "iozone")

        if not os.path.isfile(iozone_cmd):
            raise ConanException(f"iozone binary not found at: {iozone_cmd}")

        # Copy test_iozone.py to a writable working directory
        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.environ.get("HOME", "/storage"), "tmp")
        workdir = tempfile.mkdtemp(prefix="iozone-test-", dir=tmpdir)

        try:
            copy(self, "test_iozone.py", src=self.source_folder, dst=workdir)
            test_script = os.path.join(workdir, "test_iozone.py")
            if not os.path.isfile(test_script):
                raise ConanException(f"test_iozone.py not found at: {test_script}")

            # Run the test script — self.run() raises on non-zero exit
            self.output.info("Running test_iozone.py ...")
            self.run(
                f'python3 "{test_script}" "{iozone_cmd}"',
                env="conanrun"
            )
            self.output.info("iozone test_iozone.py: ALL PASS")
        finally:
            if os.path.isdir(workdir):
                shutil.rmtree(workdir, ignore_errors=True)
