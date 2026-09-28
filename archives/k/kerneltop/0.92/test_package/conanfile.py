"""test_package for kerneltop 0.92 - consumer-level checks on the packaged CLI.

The upstream release has no test suite (the tarball is kerneltop.c, makefile
and vidsupport.h and nothing else), so this is the whole evidence chain that
the packaged binary works on HarmonyOS PC.

Deliberately no `can_run()` guard: the OHOS build profile is also passed as
the build profile, so the runner is the target and every case below really
executes the ELF.  A skip here would turn a live signal into a vacuous one -
and each case exits through the binary's own status code, which is what makes
a broken .codesign segment visible (rc=126) instead of hidden.
"""
import os

from conan import ConanFile


class KerneltopTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS ships no usable /bin/sh for running ELF-wrapping scripts; the
        # profile puts hnp bash in CONFIG_SHELL, with a hard fallback.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f'"{bash}" test_kerneltop.sh', env="conanrun")
