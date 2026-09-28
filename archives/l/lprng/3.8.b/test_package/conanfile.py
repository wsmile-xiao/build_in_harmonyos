#!/usr/bin/env python3
"""Conan test_package for LPRng 3.8.b - HarmonyOS consumer smoke test.

LPRng is an application package.  With the conan 2 default prefix=/ +
DESTDIR install, all 8 programs land in bin/ and the sample spooler
configs land in etc/ (lpd.perms.sample, printcap.sample).  The consumer
assertions live in test.sh.
"""

import os

from conan import ConanFile


class LprngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv injects the packaged bin/ into PATH.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        # NOTE: no can_run guard - CI executes the consumer test on the
        # OHOS device itself, and the R34 destructive negative test (L1e)
        # relies on this test failing when the packaged artifacts are
        # removed; a silent skip would be judged a fake test.
        dep = self.dependencies.get("lprng")
        pkg = dep.package_folder if dep is not None else ""
        bindir = os.path.join(pkg, "bin")
        etcdir = os.path.join(pkg, "etc", "lpd")
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        self.run(
            "\"%s\" \"%s\" \"%s\" \"%s\""
            % (shell, script, bindir, etcdir),
            env="conanrun",
        )
