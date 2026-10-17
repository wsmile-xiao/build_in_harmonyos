#!/usr/bin/env python3
"""Conan test_package for openrtsp — verify the openRTSP binary is packaged
and runs as a consumer-level smoke test.

live555 has no upstream automated test suite (0/0 official cases). The
consumer smoke test (test_package/test_openrtsp.sh) runs the packaged
openRTSP binary with no arguments — which prints a "Usage:" banner and
exits 1 — and asserts:
  - the process is not terminated by a signal (no crash),
  - the exit code is the expected usage exit (1, not a signal, not 0),
  - stdout contains the "Usage:" banner.
Missing output, a signal death, or an unexpected exit code must raise.

The test() method invokes test_openrtsp.sh with the conanrun environment
(VirtualRunEnv sets LD_LIBRARY_PATH for the openssl dependency) and
asserts the script exits 0 (PASS). Any non-zero script exit propagates
as a ConanException, so the test genuinely fails on a missing binary,
a signal death, a missing Usage banner, or an unexpected exit code.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class OpenrtspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["openrtsp"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        bin_path = os.path.join(bin_dir, "openRTSP")
        if not os.path.exists(bin_path):
            raise Exception(f"openRTSP binary not found at {bin_path}")
        self.output.info(f"openRTSP binary found at {bin_path}")

        # Invoke the consumer smoke-test script with conanrun env so
        # LD_LIBRARY_PATH (openssl) is set. The script runs openRTSP with
        # no args, checks for signal death, expected usage exit (1), and
        # the "Usage:" banner, exiting 0 on PASS / non-zero on FAIL.
        # We do NOT use ignore_errors here: a FAIL (non-zero exit from the
        # script) must surface as a real test failure (ConanException).
        script = os.path.join(os.path.dirname(__file__), "test_openrtsp.sh")
        if not os.path.exists(script):
            raise Exception(f"smoke-test script not found at {script}")
        self.run(f"sh {script} {bin_path}", env="conanrun")
