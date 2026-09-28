#!/usr/bin/env python3
"""test_package for the rephrase 0.2 executable.

Consumer verification: the installed `rephrase` binary is invoked from PATH the
way a real user invokes it, and five assertions on exit code plus stderr decide
the result.  Upstream ships no test harness, so all five are self-authored.
"""
import os

from conan import ConanFile


class RephraseTestConan(ConanFile):
    """Runs test.sh, which executes the packaged rephrase binary."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so bash wraps
        # the invocation.  CONFIG_SHELL is honoured when the pipeline exports it.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Lower bound on assertions, must equal test_package/MANIFEST.yml ->
        # assertion_count (5).  test.sh prints 5 assertion lines plus one summary
        # line that also starts with "[PASS] " (test.sh:80), so a `grep -c` over
        # the log yields 6.  This bound counts assertions, not [PASS] lines.
        self.run(f"{bash} test.sh 5", env="conanrun")
