#!/usr/bin/env python3
"""test_package for ktls-utils - consumer test of the packaged tlshd binary.

Runs test_package/test.sh, which exercises the installed `tlshd` command
through its real command-line interface (version / help) and asserts that
invalid invocation is rejected (negative controls). These paths run entirely
in user space and do not require the kernel kTLS / net-handshake subsystem, so
they verify the OHOS build and its dynamic linking against the packaged gnutls,
libkeyutils, libnl and glib runtime libraries.
"""
import os
import shutil

from conan import ConanFile


class KtlsUtilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) is unreliable for these tests; use bash
        # when available (same pattern as the other CLI archives in this repo).
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"
        self.run(f"{shell} test.sh", env="conanrun")
