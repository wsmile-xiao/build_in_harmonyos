#!/usr/bin/env python3
"""Runtime contract and OHOS AArch64 ABI checks for jool-tools."""

import os

from conan import ConanFile
from conan.errors import ConanException


class JoolToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.info(f"skip runtime test on {self.settings.os} (cross-compiled)")
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        if not pkg:
            raise ConanException("jool-tools package folder unavailable")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_cli.sh")
        target = " ohos" if self.settings.os == "OHOS" else ""
        self.run(f'bash "{script}" "{pkg}"{target}', env=["conanrun", "conanbuild"])
