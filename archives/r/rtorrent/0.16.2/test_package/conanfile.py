#!/usr/bin/env python3
"""Consumer test for rtorrent — executes the installed binary."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RtorrentTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: rtorrent binary not run")
            return
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution (test.sh invokes rtorrent -h/-n).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
