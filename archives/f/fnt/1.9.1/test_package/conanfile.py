#!/usr/bin/env python3
"""Conan test_package for fnt — a shell script font manager.
Verify the binary exists and has correct shebang (HMDFS can't chmod +x)."""
import os
from conan import ConanFile
from conan.tools.build import cross_building


class FntTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        # Delegate to test.sh which owns the 5 functional assertions.
        # Expose fnt on PATH so test.sh's `which fnt` resolves to our pkg.
        pkg = self.dependencies["fnt"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        test_sh = os.path.join(self.source_folder, "test.sh")
        # test.sh uses /data/service/hnp/bin/bash shebang (HMDFS noexec-safe
        # via explicit interpreter invocation). Pass PATH so `which fnt` works.
        self.run(f'PATH="{bin_dir}:$PATH" /data/service/hnp/bin/bash "{test_sh}"',
                 env="conanrun")