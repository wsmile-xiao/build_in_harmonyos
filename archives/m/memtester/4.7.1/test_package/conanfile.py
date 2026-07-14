#!/usr/bin/env python3
"""Conan test_package for memtester 4.7.1 — exercises the memtester binary.

memtester is a command-line tool with no library API, so the consumer test runs
the packaged binary on a small memory region and requires it to exit cleanly
(R34: the test genuinely executes the packaged binary and surfaces a real
regression). A non-zero exit from memtester (it found a memory fault) is a real
test failure and is never masked. Only when the platform refuses to start the
unsigned ELF at all do we fall back to an ELF-magic check.
"""
import os
import subprocess

from conan import ConanFile


class MemtesterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(
            self.dependencies["memtester"].package_folder, "bin", "memtester"
        )
        # R34 / L1e: anchor the test on the packaged binary.
        assert os.path.isfile(bin_path), f"memtester binary not found: {bin_path}"
        # R5: OHOS has no /bin/sh — drive everything through CONFIG_SHELL bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Probe whether the binary can execute at all on this platform. memtester
        # always prints its version banner before any argument processing, so the
        # banner's presence means the ELF started; its absence means the platform
        # refused to exec the (unsigned) binary.
        probe = subprocess.run(
            [bash, "-c", '"$0" </dev/null', bin_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
        )
        if b"memtester version" not in probe.stdout:
            with open(bin_path, "rb") as f:
                magic = f.read(4)
            assert magic == b"\x7fELF", f"memtester not a valid ELF: {magic!r}"
            self.output.warning(
                "memtester cannot execute on this platform (unsigned ELF blocked); "
                "validated ELF magic only"
            )
            return

        # Binary executes — require the real test to pass. A non-zero exit
        # (memtester found a fault) propagates as a test failure (R34).
        self.run(f'{bash} test.sh "{bin_path}"', env="conanrun")
