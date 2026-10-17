#!/usr/bin/env python3
"""Conan test_package — acf-freeradius3 0.3.1 (Alpine Configuration Framework freeradius3 module).

L1 official test: verifies the pure-Lua ACF freeradius3 module is packaged correctly.
The module ships freeradius3-controller.lua / freeradius3-model.lua / freeradius3.menu /
HTML view templates (.lsp). The test runs test_acf-freeradius3.sh which verifies
files exist, are non-empty, and contain real ACF content.
"""
from pathlib import Path

from conan import ConanFile


class AcfFreeradius3TestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-freeradius3 package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-freeradius3")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(
                f"Could not get acf-freeradius3 package_folder via dependencies API: {e}"
            )

        test_script = Path(__file__).parent / "test_acf-freeradius3.sh"
        if pkg_root:
            self.run(f"ACF_FREERADIUS3_PKG_ROOT={pkg_root} sh {test_script}")
        else:
            self.run(f"sh {test_script}")
