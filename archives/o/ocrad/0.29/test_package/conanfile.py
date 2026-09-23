#!/usr/bin/env python3
"""Conan test_package for ocrad — runs the OCR binary to verify packaging.

R34: This test executes the actual ocrad binary (not a print-only stub).
"""
import os

from conan import ConanFile


class OcradTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the ocrad binary directly from the dependency package folder
        ocrad_dep = self.dependencies["ocrad"]
        ocrad_bin = os.path.join(ocrad_dep.package_folder, "bin", "ocrad")
        if not os.path.exists(ocrad_bin):
            # Fallback: search in PATH (set by VirtualRunEnv)
            self.run("ocrad --version", env="conanrun")
        else:
            # Ensure it's executable (HMDFS may not support chmod, E046)
            try:
                os.chmod(ocrad_bin, 0o755)
            except (PermissionError, OSError):
                pass
            self.run(f'"{ocrad_bin}" --version', env="conanrun")
