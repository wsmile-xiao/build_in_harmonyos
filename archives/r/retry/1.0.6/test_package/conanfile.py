#!/usr/bin/env python3
"""test_package for retry — exercises the packaged CLI binary (R34).

test_retry.sh really runs the installed `retry` binary against freshly created
probe scripts and asserts on its documented behaviour: criteria handling
(success / fail / while / until), --times, stdin capture and replay, stdout
routing on retry (failed attempts go to stderr), custom notifications and
exit-code propagation.  It fails if the binary is missing or broken (CI L1e
sabotages bin/ to prove this dependency).

Upstream ships no test suite (see MANIFEST.yml for the inventory evidence), so
this is the consumer-side regression suite required by R51 for the
no-upstream-tests case.
"""
import os

from conan import ConanFile


class RetryTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_retry.sh".format(shell), env="conanrun")
