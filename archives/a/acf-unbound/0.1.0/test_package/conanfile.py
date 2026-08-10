#!/usr/bin/env python3
"""Conan test_package for acf-unbound 0.1.0.

Runs test_acf_unbound.sh against the installed package: verifies artifact
presence and substantive ACF app content markers (real Lua controller/model,
menu + roles) — not a stub. Pure Lua/data package, no binary to execute.
"""

import os

from conan import ConanFile


class AcfUnboundTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_acf_unbound.sh")
        self.run(f'"{bash}" "{script}" "{pkg}"', env="conanrun")
