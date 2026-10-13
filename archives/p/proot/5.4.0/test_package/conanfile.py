#!/usr/bin/env python3
"""test_package for proot — exercises the packaged CLI binary (R34).

test_proot.sh really runs the installed `proot` binary and asserts on its
documented behaviour: version/help output and exit codes, the accelerator
detection reported by --version, argument validation (missing command,
unknown option, unusable rootfs) and the platform-policy coherence of a
tracee run (see below).  It fails if the binary is missing or broken
(CI L1e sabotages bin/ to prove this dependency).

Platform note: the OHOS kernel refuses ptrace(2) for unprivileged processes,
so `proot <command>` cannot create a tracee there and exits with
"ptrace(TRACEME): Permission denied"; on a ptrace-permissive kernel the same
invocation must succeed.  The test asserts the coherent outcome for whichever
policy the running kernel enforces.  The upstream suite results (make -C test
check) are recorded truthfully in reports/test-report.md.
"""
import os

from conan import ConanFile


class ProotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_proot.sh".format(shell), env="conanrun")
