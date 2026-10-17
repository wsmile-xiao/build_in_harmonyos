#!/usr/bin/env python3
"""test_package for runlim — exercises the packaged CLI binary (R34).

test_runlim.sh really runs the installed `runlim` binary and asserts on its
documented behaviour: version/usage/error paths, pass-through execution, log
file contents, runlim's own status semantics (0 ok / 2 out of time / 3 out of
memory / 4 child SIGSEGV / 11 child other signal — child exit codes are
ignored by design), real-time (-r), CPU-time (-t/--time-limit) and space
(-s/--space-limit) limit enforcement, and -k signal propagation.  It fails if
the binary is missing or broken (CI L1e sabotages bin/ to prove this
dependency).

Upstream ships no test suite (see MANIFEST.yml for the inventory evidence), so
this is the consumer-side regression suite required by R51 for the
no-upstream-tests case.  The -t case is also the regression test for the
RLIMIT_AS unit fix: on an unpatched build the child cannot be exec'd and
runlim returns 1 ("execvp failed") instead of 2.
"""
import os

from conan import ConanFile


class RunlimTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_runlim.sh".format(shell), env="conanrun")
