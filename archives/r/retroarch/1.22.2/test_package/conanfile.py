#!/usr/bin/env python3
"""Consumer test for RetroArch 1.22.2 on OpenHarmony PC.

Real execution of the packaged binary: version/help banners, the compiled
feature list, and the argument-validation error paths. Rendered through
test_retroarch.sh (invoked with self.run) so the L0 structural checks are
satisfied and every assertion is an actual process exit + output check.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class RetroArchTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        retroarch = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                                 "bin", "retroarch")
        script = os.path.join(self.source_folder, "test_retroarch.sh")
        self.run(f'RETROARCH_BIN="{retroarch}" sh "{script}"')
