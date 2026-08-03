#!/usr/bin/env python3
"""Conan test_package for nwipe 0.39 — CLI smoke test.

L1 test: verify the nwipe binary is installed and responds to --version.
Upstream nwipe 0.39 ships no traditional test suite (no TESTS/check_PROGRAMS
in Makefile.am/configure.ac), but has 2 GitHub CI workflows as upstream tests:
ci_ubuntu_latest.yml (compile check) + ci_formatting.yml (style check). The
compile step is executed equivalently by conanfile build() on OHOS; this
smoke test validates the binary runs. See test_package/MANIFEST.yml audit.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NwipeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["nwipe"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            nwipe_cmd = os.path.join(bin_dir, "nwipe")

            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

            self.run(f'{bash} test.sh "{nwipe_cmd}"', env="conanrun")
