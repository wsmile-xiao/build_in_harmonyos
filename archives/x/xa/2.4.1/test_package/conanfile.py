#!/usr/bin/env python3
"""test_package for xa — exercises the packaged toolchain binaries (R34).

test_xa.sh really runs the installed binaries: it assembles raw and o65
objects with `xa`, links with `ldo65`, relocates with `reloc65`, inspects the
results with `file65`, round-trips a cpk archive with `uncpk` and dumps a
BASIC program with `printcbm`.  It fails if any binary is missing or broken
(CI L1e sabotages bin/ to prove the test really needs the package).
"""
import os

from conan import ConanFile


class XaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_xa.sh".format(shell), env="conanrun")
