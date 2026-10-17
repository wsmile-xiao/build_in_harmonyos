#!/usr/bin/env python3
"""Conan test_package for selint (SELinux policy linter CLI).

selint is a command-line tool, so the consumer test runs real end-to-end lint
jobs (R34): it verifies `--version` reports 1.5.1, then runs selint over a tiny
policy source with an unordered allow rule that triggers a known check (C-005)
and asserts the finding is reported (and that `-F` makes selint exit non-zero
on findings).  This exercises the actual parser/checker, not just the exit code.
"""
import os

from conan import ConanFile


class SelintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_selint.sh", env="conanrun")
