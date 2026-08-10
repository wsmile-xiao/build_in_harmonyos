#!/usr/bin/env python3
"""Conan test_package — acf-samba 0.10.1 (Alpine Configuration Framework Samba module).

L1 official test: verifies the pure-Lua ACF Samba module is packaged correctly.

The module ships:
  - samba-controller.lua  (dispatcher controller)
  - samba-model.lua       (samba configuration model)
  - samba.menu, samba.roles
  - HTML view templates (.lsp)

This test verifies the packaged files exist and the Lua sources are
syntactically valid (luac -p). It does NOT require samba to be running —
that would be an L2 integration test.
"""
from pathlib import Path

from conan import ConanFile


class AcfSambaTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-samba package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-samba")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-samba package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_samba.sh"
        if pkg_root:
            self.run(f'sh {test_script}', env=["ACF_SAMBA_PKG_ROOT=" + str(pkg_root)])
        else:
            self.run(f'sh {test_script}')
