#!/usr/bin/env python3
"""Conan test_package — acf-db 0.2.1 (Alpine Configuration Framework db module).

L1 official test: verifies the pure-Lua ACF db module is packaged correctly.

The module ships:
  - db-controller.lua  (dispatcher controller)
  - db-model.lua       (database configuration model)
  - db.menu / db.roles (ACF menu and role definitions)
  - lib/ Lua helpers + 4 HTML view templates (.lsp)

This test verifies the packaged files exist and the Lua sources are
syntactically valid (luac -p). It does NOT require a running database —
that would be an L2 integration test.
"""
import os
from pathlib import Path

from conan import ConanFile


class AcfDbTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-db package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-db")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-db package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_db.sh"
        if pkg_root:
            # Conan 2 run() env= 参数只接受 env 文件名列表，不能传 KEY=VALUE；
            # 用 os.environ 注入，确保测试精确指向被测试包（而非缓存中其他实例）。
            os.environ["ACF_DB_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
