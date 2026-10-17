#!/usr/bin/env python3
"""test_package for reptyr — exercises the packaged CLI binary (R34).

test_reptyr.sh really runs the installed `reptyr` binary and asserts on its
documented behaviour: version/help output, argument and pid validation, attach
error reporting for a non-existent pid, pty allocation (-l) and running a
command with its stdio on the newly allocated pty slave (-L, REPTYR_PTY).
It fails if the binary is missing or broken (CI L1e sabotages bin/ to prove
this dependency).

The upstream suite (test/basic.py, test/tty-steal.py) needs PTRACE_ATTACH,
which OHOS refuses with EPERM for unprivileged processes (seccomp-filtered;
PTRACE_TRACEME and process_vm_readv fail the same way).  The per-item upstream
results and the platform-boundary evidence are in reports/test-report.md;
this consumer suite covers everything that is available on such a platform.
"""
import os

from conan import ConanFile


class ReptyrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_reptyr.sh".format(shell), env="conanrun")
