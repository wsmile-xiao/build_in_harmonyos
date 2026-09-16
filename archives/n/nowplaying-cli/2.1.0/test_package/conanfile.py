#!/usr/bin/env python3
"""test_package for nowplaying-cli 2.1.0 (OpenHarmony portable build).

R34: this test substantially exercises the packaged artifact. The package is a
command-line tool, so test.sh runs the installed `nowplaying-cli` binary and
asserts on its real stdout/stderr/exit codes (help, version, get, get-raw,
control verbs, argument validation). Nothing is mocked and no fabricated
now-playing data is expected.

Platform note: on OHOS the system /system/bin/sh (mksh) cannot execute ELF
binaries, so the checks are driven from bash (CONFIG_SHELL), exactly as the
CI environment expects.
"""
import os

from conan import ConanFile


class NowplayingCliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
