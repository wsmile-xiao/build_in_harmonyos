#!/usr/bin/env python3
"""Conan test_package — acf-provisioning 0.10.1 (Alpine Configuration Framework provisioning module).

L1 official test: verifies the pure-Lua ACF provisioning module is packaged correctly.

The module ships:
  - provisioning-controller.lua / provisioning-model.lua (dispatcher controller + model)
  - provisioning-scripts.lua (table_creation_scripts helper)
  - provisioning.menu / provisioning.roles (ACF menu and role definitions)
  - provisioning-*.lsp HTML view templates
  - upgradeprovisioning (db upgrade helper, mode 700)
  - cgi-bin/ scripts + config/ templates

This test verifies the packaged files exist and the Lua sources are
syntactically valid (luac -p). It does NOT require a running provisioning
backend — that would be an L2 integration test.
"""
import os
from pathlib import Path

from conan import ConanFile


class AcfProvisioningTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-provisioning package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-provisioning")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-provisioning package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_provisioning.sh"
        if pkg_root:
            # Conan 2 run() env= 参数只接受 env 文件名列表，不能传 KEY=VALUE；
            # 用 os.environ 注入，确保测试精确指向被测试包（而非缓存中其他实例）。
            os.environ["ACF_PROVISIONING_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
