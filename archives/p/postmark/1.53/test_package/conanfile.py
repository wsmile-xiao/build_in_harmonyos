#!/usr/bin/env python3
"""test_package for postmark executable — runs the installed `postmark` binary.

Consumer verification: invoke the installed benchmark binary with a minimal
config file (set location/number/size/transactions + run + quit), and verify
it executes a full benchmark run and produces the expected report output.
"""
import os

from conan import ConanFile


class PostmarkTestConan(ConanFile):
    """test_package for postmark executable — runs test.sh which invokes the postmark binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. Prefer CONFIG_SHELL, fall back to
        # the OHOS device-verified path /data/service/hnp/bin/bash, then PATH.
        import shutil
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.exists(bash):
            bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f'"{bash}" test.sh', env="conanrun")
