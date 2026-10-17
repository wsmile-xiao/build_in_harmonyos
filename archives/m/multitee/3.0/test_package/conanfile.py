#!/usr/bin/env python3
"""test_package for multitee 3.0 (command-line tool, no library to link).

Runs test_multitee.py against the packaged bin/multitee:
  * A1-A4 artifact checks on every host: ELF64 little-endian EM_AARCH64,
    PIE, PT_INTERP = /lib/ld-musl-aarch64.so.1, executable bit;
  * F1-F11 functional checks (copy, fan-out, -b, merge, open-input wait,
    'e' EOF link, EPIPE warning, SIGPIPE death, -q, bad option, no args),
    mandatory on the aarch64 CI worker; see the script docstring for the
    foreign-architecture rule.
The binary is taken from the tested package only (no PATH fallback), so the
CI L1e destructive check fails as soon as bin/ is removed.
"""
import os
import sys

from conan import ConanFile


class MultiteeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        multitee = os.path.join(
            self.dependencies["multitee"].package_folder, "bin", "multitee")
        script = os.path.join(self.source_folder, "test_multitee.py")
        # scratch files go to the test build folder: /tmp is read-only on OHOS
        self.run(f'"{sys.executable}" "{script}" "{multitee}" "{self.build_folder}"',
                 env="conanrun")
