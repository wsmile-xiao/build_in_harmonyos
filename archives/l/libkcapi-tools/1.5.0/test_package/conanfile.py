#!/usr/bin/env python3
"""Conan test_package for libkcapi-tools 1.5.0.

The tested package ships four command line binaries, so the test runs
them for real (R34): the --version/-v exit-status contract of every tool
(only kcapi_versionstring(), a pure user space API, is involved), the
upstream --help exit(1) contract, a self-containment check (no
DT_NEEDED on libkcapi - the tools must link the in-tree static library)
and a negative control for unknown options.

Real crypto operations are deliberately not asserted: they go through
the kernel AF_ALG socket, which the OHOS SELinux policy denies for
unprivileged processes (bind EPERM, see libkcapi 1.5.0 notes) - the
behavior is a platform capability, not a package property, and asserting
it would make the test result device-policy dependent.
"""
import os

from conan import ConanFile


class LibkcapiToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
