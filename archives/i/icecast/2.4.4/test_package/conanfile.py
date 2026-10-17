#!/usr/bin/env python3
"""Conan test_package for icecast 2.4.4 (streaming media server).

icecast is a command-line streaming server, so the L1 test runs a real
end-to-end job (R34): 1) `icecast --version` smoke check, 2) start the
server with a minimal config on an ephemeral port, 3) request
/status.xsl and assert the XSLT-rendered status page is served,
4) shut the server down cleanly and verify the port is released.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IcecastTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
