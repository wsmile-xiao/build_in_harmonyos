#!/usr/bin/env python3
"""Conan test_package — cldump 0.11-dfsg (CLI smoke test).

cldump is a command-line tool (no linkable library): the consumer test really
executes the packaged `cldump` binary. --version/--help exit(0) before any
file access, so headless environments can validate executability and output;
the two failure-path cases pin distinct exit codes (3/1) and stderr markers.
"""

import os

from conan import ConanFile


class CldumpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot reliably execute ELF binaries.
        # Use bash to wrap binary execution (xsel precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} test_cldump.sh".format(bash), env="conanrun")
