#!/usr/bin/env python3
"""Conan test_package — acf-mariadb 0.2.0 (Alpine Configuration Framework mariadb module).

L1 official test: verifies the pure-Lua ACF mariadb module is packaged correctly.

The module ships:
  - mysql-controller.lua  (dispatcher controller)
  - mysql-model.lua       (MariaDB configuration model)
  - mysql.menu / mysql.roles (ACF menu and role definitions)
  - mysql-details-html.lsp (detail view template)
  - mysql-expert-html.lsp  (symlink to acf-core db-expert-html.lsp)
  - mysql-logfile-html.lsp (symlink to acf-core db-logfile-html.lsp)
  - mysql-status-html.lsp  (symlink to acf-core db-status-html.lsp)

This test verifies the packaged files exist and the Lua sources are
syntactically valid (luac -p). It does NOT require a running MariaDB —
that would be an L2 integration test.
"""
import os
from pathlib import Path

from conan import ConanFile


class AcfMariadbTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-mariadb package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-mariadb")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-mariadb package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_mariadb.sh"
        if pkg_root:
            os.environ["ACF_MARIADB_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
