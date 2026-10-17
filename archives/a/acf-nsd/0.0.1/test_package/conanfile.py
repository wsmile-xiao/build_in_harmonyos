#!/usr/bin/env python3
"""Conan test_package — acf-nsd 0.0.1 (Alpine Configuration Framework NSD module).

L1 official test: verifies the pure-Lua ACF NSD module is packaged correctly.

The module ships:
  - nsd-controller.lua  (dispatcher controller)
  - nsd-model.lua       (nsd configuration model)
  - 4 HTML view templates (.lsp)

This test verifies the packaged files exist and the Lua sources are
syntactically valid (luac -p). It does NOT require nsd to be running —
that would be an L2 integration test.
"""
from pathlib import Path

from conan import ConanFile


class AcfNsdTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-nsd package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-nsd")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-nsd package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_nsd.sh"
        if pkg_root:
            self.run(f'sh {test_script}', env=["ACF_NSD_PKG_ROOT=" + str(pkg_root)])
        else:
            self.run(f'sh {test_script}')
