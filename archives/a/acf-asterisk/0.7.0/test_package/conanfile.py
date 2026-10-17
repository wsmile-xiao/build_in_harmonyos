#!/usr/bin/env python3
"""Conan test_package — acf-asterisk 0.7.0 (Alpine Configuration Framework asterisk module).

L1 official test: verifies the pure-Lua ACF asterisk module is packaged correctly.
The module ships asterisk-controller.lua / asterisk-model.lua / asterisk.menu /
HTML view templates (.lsp). The test runs test_acf_asterisk.sh which verifies
files exist, are non-empty, and contain real ACF content.
"""
from pathlib import Path

from conan import ConanFile


class AcfAsteriskTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-asterisk package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-asterisk")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(
                f"Could not get acf-asterisk package_folder via dependencies API: {e}"
            )

        test_script = Path(__file__).parent / "test_acf_asterisk.sh"
        if pkg_root:
            # Pass the package root inline in the command (Conan's env= param
            # expects env-file names, not VAR=value strings).
            self.run(f"ACF_ASTERISK_PKG_ROOT={pkg_root} sh {test_script}")
        else:
            self.run(f"sh {test_script}")
