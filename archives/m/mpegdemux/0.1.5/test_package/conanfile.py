#!/usr/bin/env python3
"""Conan test_package for mpegdemux 0.1.5 — real demux verification.

Upstream has no formal test suite (no tests/, no `make check` target),
so this test_package is the sole functional verification. It:

  1. Programmatically generates a minimal valid MPEG-2 Program Stream
     (no committed binary blob — the fixture is an auditable Python
     generator).
  2. Runs the installed mpegdemux binary in all four modes
     (scan / list / demux / remux) against that fixture.
  3. Checks output file size, structure, and determinism.
  4. Runs a negative test (empty input must not be accepted as valid).
  5. Verifies the produced binary is an OHOS aarch64 ELF with the musl
     interpreter.

Per R34, the test actually executes the packaged binary with real I/O
rather than only printing `--help`.
"""
import os

from conan import ConanFile


class MpegdemuxTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["mpegdemux"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        bin_path = os.path.join(bin_dir, "mpegdemux")

        this_dir = os.path.dirname(os.path.abspath(__file__))
        gen_py = os.path.join(this_dir, "gen_fixture.py")
        run_sh = os.path.join(this_dir, "run_tests.sh")
        work_dir = os.path.join(self.build_folder, "work")

        # R34: exercise the packaged binary with real demux I/O.
        self.run(f'sh {run_sh} "{bin_path}" "{gen_py}" "{work_dir}"',
                 env="conanrun")
        self.output.info("mpegdemux: OK")
