#!/usr/bin/env python3
"""Conan test_package — ubench 0.32.

Runs test_ubench.py against the packaged bin/ubench: CLI error path,
single-mode CPU/MEM/AVG benchmarks, and three HarmonyOS checks (static-PIE
OHOS artefact, CLK_TCK -> sysconf(_SC_CLK_TCK) timing, musl strerror(EMFILE)
through the sys_errlist replacement).  See test_ubench.py for the case list.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class UbenchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        binary = os.path.join(self.dependencies["ubench"].package_folder, "bin", "ubench")
        if not os.path.isfile(binary):
            raise ConanException("bin/ubench not packaged")
        script = os.path.join(self.source_folder, "test_ubench.py")
        ohos = " --ohos" if str(self.settings.os) == "OHOS" else ""
        self.run(f'"{sys.executable}" "{script}" --binary "{binary}"{ohos}', env="conanrun")
