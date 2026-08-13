#!/usr/bin/env python3
"""Conan test_package — acf-lvm2 0.7.0 (Alpine Configuration Framework lvm2 module).

L1 official test: verifies the pure-Lua ACF lvm2 module is packaged correctly.

The module ships:
  - lvm2-controller.lua  (dispatcher controller)
  - lvm2-model.lua       (LVM configuration model)
  - lvm2.menu / lvm2.roles (ACF menu and role definitions)
  - HTML view templates (.lsp)

This test verifies the packaged files exist and the layout matches the ACF
convention (share/acf/app/lvm2/). It does NOT require a running LVM stack —
that would be an L2 integration test.
"""
import os
from pathlib import Path

from conan import ConanFile


class AcfLvm2TestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-lvm2 package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-lvm2")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-lvm2 package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_lvm2.sh"
        if pkg_root:
            os.environ["ACF_LVM2_PKG_ROOT"] = str(pkg_root)
        self.run(f"sh {test_script}")
