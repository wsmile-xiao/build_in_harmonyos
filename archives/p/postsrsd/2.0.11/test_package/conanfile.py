#!/usr/bin/env python3
"""Conan test_package — postsrsd 2.0.11 (application).

Runs the packaged postsrsd binary with -v / -h and checks the output, which
exercises the actual installed executable (not a print-only stub).
"""
import os
import shutil

from conan import ConanFile


class PostsrsdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries. Use bash to
        # wrap binary execution; prefer $CONFIG_SHELL, then PATH lookup, then
        # the well-known HNP bash location as a last resort.
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} test.sh", env="conanrun")