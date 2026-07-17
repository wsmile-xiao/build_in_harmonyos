#!/usr/bin/env python3
"""Conan test_package for convmv 2.06 — Perl script test.

Verifies that the convmv command is functional after installation.
Runs convmv --list to verify encoding support, then tests actual
encoding conversion with --unescape.
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class ConvmvTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["convmv"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            convmv_cmd = os.path.join(bin_dir, "convmv")

            # Test 1: convmv --help should output version info
            # Note: convmv may exit with code 1 due to Perl "fleas" warnings,
            # so we check output content rather than exit code
            result = subprocess.run(
                [convmv_cmd, "--help"],
                capture_output=True, text=True, timeout=30
            )
            if "convmv 2.06" not in (result.stdout + result.stderr):
                raise Exception(
                    f"convmv --help did not output expected version string. "
                    f"stdout={result.stdout[:200]}, stderr={result.stderr[:200]}"
                )
            self.output.info("convmv --help: PASS (version string found)")

            # Test 2: convmv --list should list available encodings
            # Note: convmv may exit with code 1 due to Perl "fleas" warnings,
            # so we check output content rather than exit code
            list_result = subprocess.run(
                [convmv_cmd, "--list"],
                capture_output=True, text=True, timeout=30
            )
            encoding_count = len(list_result.stdout.strip().splitlines())
            if encoding_count == 0:
                raise Exception("convmv --list returned no encodings")
            self.output.info(f"convmv --list: PASS ({encoding_count} encodings)")

            # Test 3: Actual encoding conversion test (--unescape)
            tmpdir = tempfile.mkdtemp(prefix="convmv-test-")
            try:
                # Create a file with percent-encoded name
                test_file = os.path.join(tmpdir, "test%20file.txt")
                with open(test_file, "w") as f:
                    f.write("test content")

                # Run convmv --unescape to decode the filename
                self.run(
                    f'cd "{tmpdir}" && '
                    f'"{convmv_cmd}" --unescape --notest -r .',
                    env="conanrun"
                )

                # Verify the converted file name exists
                expected_file = os.path.join(tmpdir, "test file.txt")
                if not os.path.isfile(expected_file):
                    raise Exception(
                        f"Expected converted file not found: {expected_file}"
                    )
                self.output.info("convmv --unescape: PASS (test%20file.txt → test file.txt)")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
