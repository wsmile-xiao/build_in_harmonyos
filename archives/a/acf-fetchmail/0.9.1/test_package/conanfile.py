#!/usr/bin/env python3
"""Conan test_package — acf-fetchmail 0.9.1 (Alpine Configuration Framework fetchmail module).

L1 official test: verifies the pure-Lua ACF fetchmail module is packaged correctly.
The module ships fetchmail-controller.lua / fetchmail-model.lua / fetchmail.menu /
HTML view templates (.lsp). The test runs test_acf-fetchmail.sh which verifies
files exist, are non-empty, and contain real ACF content.
"""
from pathlib import Path

from conan import ConanFile


class AcfFetchmailTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-fetchmail package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-fetchmail")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(
                f"Could not get acf-fetchmail package_folder via dependencies API: {e}"
            )

        test_script = Path(__file__).parent / "test_acf-fetchmail.sh"
        if pkg_root:
            self.run(f"ACF_FETCHMAIL_PKG_ROOT={pkg_root} sh {test_script}")
        else:
            self.run(f"sh {test_script}")
