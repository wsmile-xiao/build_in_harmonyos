#!/usr/bin/env python3
"""Conan test_package — acf-apk-tools 0.11.0 (Alpine Configuration Framework apk module).

L1 official test: verifies the pure-Lua ACF apk module is packaged correctly.

The module ships:
  - apk-controller.lua  (dispatcher controller)
  - apk-model.lua       (apk configuration model)
  - apk.menu / apk.roles (ACF menu & role declarations)
  - HTML view templates (.lsp)

This test verifies the packaged files exist, the view templates are complete
(non-empty, real ACF HTML), and the Lua sources contain real controller/model
logic. It does NOT require apk-tools to be running — that would be an L2
integration test.
"""
from pathlib import Path

from conan import ConanFile


class AcfApkToolsTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-apk-tools package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-apk-tools")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-apk-tools package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_apk_tools.sh"
        if pkg_root:
            # Pass the package root inline in the command (Conan's env= param
            # expects env-file names, not VAR=value strings).
            self.run(f'ACF_APK_TOOLS_PKG_ROOT={pkg_root} sh {test_script}')
        else:
            self.run(f'sh {test_script}')
