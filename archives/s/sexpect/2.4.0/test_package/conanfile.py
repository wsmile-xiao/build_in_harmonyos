#!/usr/bin/env python3
"""test_package conanfile — sexpect 2.4.0 (application package)."""
import os
import shutil

from conan import ConanFile


class SexpectTestConan(ConanFile):
    """Runs test.sh, which exercises the packaged sexpect binary end to end."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh cannot execute ELF binaries reliably; prefer
        # CONFIG_SHELL, then a bash found on PATH, then the worker's bash.
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
