#!/usr/bin/env python3
"""Conan test_package — tectonic 0.16.9

L1 test: verifies the tectonic binary is functional by running `tectonic --version`.
This satisfies R34 (test must exercise the tested package's binary).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.layout import basic_layout


class TectonicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host: skip test")
            return
        # R34: Execute the tectonic binary directly
        tectonic_bin = os.path.join(
            self.dependencies["tectonic"].package_folder, "bin", "tectonic"
        )
        # Try to make binary executable (may fail due to filesystem restrictions)
        try:
            os.chmod(tectonic_bin, 0o755)
        except (PermissionError, OSError):
            pass  # OHOS may restrict chmod on cache files

        # Run with conanrun env (sets LD_LIBRARY_PATH for shared libs)
        self.run(f'"{tectonic_bin}" --version', env=["conanrun"])
