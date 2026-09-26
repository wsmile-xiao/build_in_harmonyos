#!/usr/bin/env python3
"""test_package for wev — executes the shipped wev executable.

wev is an application (nothing for a consumer to link), so the L1 test runs
the real binary instead of compiling a consumer program:

  * `wev -h`            -> prints the usage line and exits 0
  * `wev` (no display)  -> exercises the wl_display_connect failure path,
                           proving the binary actually loads
                           wayland-client / libxkbcommon at runtime

R34: the test executes the tested package's binary, it is not a print-only
stub.  The shell wrapper mirrors the scdoc test_package, because OHOS
/system/bin/sh (mksh) cannot execute ELF binaries directly.
"""
import os

from conan import ConanFile


class WevTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
