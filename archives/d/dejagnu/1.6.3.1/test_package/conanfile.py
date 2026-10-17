#!/usr/bin/env python3
"""test_package -- dejagnu 1.6.3 (autotools application)

Verifies that the packaged runtest script can execute and print
its version string.  The test runs in the conanrun environment so
that expect (transitive via dejagnu -> expect) is on PATH.

OHOS specifics:
  - expect binary needs TCL_LIBRARY pointing to tcl init.tcl.
    We resolve tcl package folder from the dependency graph.
  - /system/bin/sh (mksh) cannot execute ELF reliably; use bash.
"""
import os

from conan import ConanFile


class DejagnuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Make tcl a direct test_package requirement so that its
        # package_folder is resolved in the consumer test() lifecycle.
        self.requires("tcl/8.6.14")

    def test(self):
        # Resolve tcl package folder to set TCL_LIBRARY for expect.
        tcl_pkg = self.dependencies["tcl"].package_folder
        tcl_library = os.path.join(tcl_pkg, "lib", "tcl8.6")

        # Use bash to ensure a POSIX-compatible shell environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = "TCL_LIBRARY=" + tcl_library + " " + bash + " test.sh"
        self.run(cmd, env="conanrun")
