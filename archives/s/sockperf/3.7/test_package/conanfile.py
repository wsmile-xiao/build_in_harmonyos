#!/usr/bin/env python3
"""Conan test_package for sockperf 3.7 — consumer-style loopback test (R34).

Starts the packaged `sockperf server` on TCP loopback and drives a real
`sockperf ping-pong` latency run against 127.0.0.1, asserting a clean
summary report.  (TCP loopback is available on OHOS; only AF_UNIX bind is
restricted platform-wide.)
"""
import os

from conan import ConanFile


class SockperfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        # Seed PWD so bash trusts the environment instead of a failing
        # getcwd() inside HMDFS dirs (E386 family, §12.73③).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        scratch = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
        os.makedirs(scratch, exist_ok=True)
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'cd "{scratch}" && PWD="{scratch}" "{bash}" "{script}"',
                 env="conanrun")
